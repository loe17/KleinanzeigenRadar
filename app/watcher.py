import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.database import (
    get_all_searches,
    get_search,
    update_search_last_run,
    save_result,
    get_settings,
    get_stats
)
from app.scraper import scrape_search
from app.notifier import send_telegram_notification, send_email_notification

logger = logging.getLogger(__name__)

class SearchWatcher:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_running = False
        self.current_running_search_id: Optional[int] = None
        self.scan_progress: Dict[int, Dict[str, Any]] = {}

    def get_scan_progress(self, search_id: int) -> Dict[str, Any]:
        """Liefert den aktuellen Fortschritt eines Suchauftrags."""
        if search_id in self.scan_progress:
            return self.scan_progress[search_id]
        return {
            "search_id": search_id,
            "is_scanning": self.current_running_search_id == search_id,
            "progress": 100 if self.current_running_search_id != search_id else 10,
            "step_text": "Bereit" if self.current_running_search_id != search_id else "Wird ausgeführt...",
            "status": "Bereit" if self.current_running_search_id != search_id else "Wird ausgeführt...",
            "found_count": 0,
            "total_ads": 0
        }

    def set_scan_progress(
        self,
        search_id: int,
        progress: Any = 0,
        step_text: str = "",
        is_scanning: bool = True,
        found_count: int = 0,
        total_ads: int = 0,
        **kwargs
    ):
        if isinstance(progress, bool):
            actual_is_scanning = progress
            actual_progress = step_text if isinstance(step_text, (int, float)) else 0
            actual_step_text = is_scanning if isinstance(is_scanning, str) else kwargs.get("step_text", "")
        else:
            actual_is_scanning = is_scanning
            actual_progress = progress
            actual_step_text = step_text

        self.scan_progress[search_id] = {
            "search_id": search_id,
            "is_scanning": bool(actual_is_scanning),
            "progress": min(100, max(0, int(actual_progress))),
            "step_text": str(actual_step_text),
            "status": str(actual_step_text),
            "found_count": int(found_count),
            "total_ads": int(total_ads),
            "updated_at": time.time()
        }

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("KleinanzeigenRadar Hintergrund-Wächter gestartet.")

    def stop(self):
        self._stop_event.set()
        self.is_running = False

    def _run_loop(self):
        # Kurze Startverzögerung beim Booten
        time.sleep(3)
        while not self._stop_event.is_set():
            try:
                self._check_due_searches()
            except Exception as e:
                logger.error(f"Unerwarteter Fehler im Wächter-Zyklus: {e}")

            # Jede Minute prüfen, ob ein Suchauftrag fällig ist
            self._stop_event.wait(60)

    def _check_due_searches(self):
        searches = get_all_searches(active_only=True)
        now = datetime.now()
        stats = get_stats()
        has_zero_results = stats.get("total_results", 0) == 0

        for s in searches:
            if self._stop_event.is_set():
                break

            interval_min = s.get("interval_minutes") or 15
            last_run_str = s.get("last_run")

            is_due = False
            if not last_run_str or has_zero_results:
                is_due = True
            else:
                try:
                    last_run = datetime.fromisoformat(last_run_str)
                    if now - last_run >= timedelta(minutes=interval_min):
                        is_due = True
                except Exception:
                    is_due = True

            if is_due:
                self.execute_search_now(s["id"])

    def execute_search_now(self, search_id: int):
        """Führt einen bestimmten Suchauftrag sofort aus und benachrichtigt bei neuen Treffern."""
        search = get_search(search_id)
        if not search:
            return

        self.current_running_search_id = search_id
        logger.info(f"Führe Suche aus: '{search['name']}' (ID: {search_id})")

        settings = get_settings()
        bot_token = settings.get("telegram_bot_token", "")
        chat_id = settings.get("telegram_chat_id", "")
        new_count = 0
        found_total = 0

        self.set_scan_progress(
            search_id=search_id,
            is_scanning=True,
            progress=5,
            step_text="Initialisiere Suchlauf...",
            found_count=0,
            total_ads=0
        )

        def handle_progress(pct: int, msg: str, found: int, total: int):
            self.set_scan_progress(
                search_id=search_id,
                is_scanning=True,
                progress=pct,
                step_text=msg,
                found_count=found,
                total_ads=total
            )

        def handle_ad_found(item: Dict[str, Any]):
            nonlocal new_count, found_total
            found_total += 1
            # Sofort in Datenbank speichern
            res_id = save_result(item)
            if res_id:
                # Es handelt sich um ein NEUES Inserat!
                new_count += 1
                logger.info(f"Neuer Treffer #{res_id}: {item['title']} ({item.get('price')})")

                # Telegram Benachrichtigung
                if search.get("notify_telegram") and bot_token and chat_id:
                    send_telegram_notification(bot_token, chat_id, item)

                # E-Mail Benachrichtigung
                if search.get("notify_email") and settings.get("email_smtp_host"):
                    send_email_notification(settings, item)

        try:
            results = scrape_search(
                search=search,
                on_ad_found=handle_ad_found,
                on_progress=handle_progress
            )
            update_search_last_run(search_id)
            self.set_scan_progress(
                search_id=search_id,
                is_scanning=False,
                progress=100,
                step_text=f"Suchlauf abgeschlossen: {len(results)} Treffer gefunden.",
                found_count=len(results),
                total_ads=len(results)
            )
            logger.info(f"Suche '{search['name']}' beendet. {len(results)} Treffer, davon {new_count} neu.")

        except Exception as e:
            logger.error(f"Fehler bei Ausführung von Suchauftrag {search_id}: {e}")
            self.set_scan_progress(
                search_id=search_id,
                is_scanning=False,
                progress=100,
                step_text=f"Fehler beim Suchlauf: {e}",
                found_count=found_total,
                total_ads=0
            )
        finally:
            self.current_running_search_id = None

watcher_service = SearchWatcher()

def get_scan_progress(search_id: int) -> Dict[str, Any]:
    return watcher_service.get_scan_progress(search_id)

def set_scan_progress(
    search_id: int,
    progress: Any = 0,
    step_text: str = "",
    is_scanning: bool = True,
    found_count: int = 0,
    total_ads: int = 0,
    **kwargs
):
    watcher_service.set_scan_progress(
        search_id=search_id,
        progress=progress,
        step_text=step_text,
        is_scanning=is_scanning,
        found_count=found_count,
        total_ads=total_ads,
        **kwargs
    )
