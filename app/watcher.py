import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.database import (
    get_all_searches,
    get_search,
    update_search_last_run,
    save_result,
    get_settings
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

        for s in searches:
            if self._stop_event.is_set():
                break

            interval_min = s.get("interval_minutes") or 15
            last_run_str = s.get("last_run")

            is_due = False
            if not last_run_str:
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

        try:
            results = scrape_search(search)
            settings = get_settings()

            bot_token = settings.get("telegram_bot_token", "")
            chat_id = settings.get("telegram_chat_id", "")

            new_count = 0
            for item in results:
                # In Datenbank speichern
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

            update_search_last_run(search_id)
            logger.info(f"Suche '{search['name']}' beendet. {new_count} neue Treffer gefunden.")

        except Exception as e:
            logger.error(f"Fehler bei Ausführung von Suchauftrag {search_id}: {e}")
        finally:
            self.current_running_search_id = None

watcher_service = SearchWatcher()
