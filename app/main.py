import os
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.config import VERSION, APP_NAME, BASE_DIR
from app.database import (
    init_db,
    get_all_searches,
    get_search,
    create_search,
    update_search,
    delete_search,
    get_results,
    update_result_status,
    mark_all_results_as_read,
    get_stats,
    get_settings,
    save_settings,
    clear_results,
    get_result_by_id,
    update_result_details,
    update_result_notes,
    update_result_deal_score,
    update_result_safety_score,
    update_result_negotiation,
    recheck_existing_results_for_search
)
from app.scraper import fetch_live_result_count, fetch_ad_details, DEFAULT_HEADERS
from app.watcher import watcher_service
from app.notifier import test_telegram_connection, test_email_connection
from app.updater import check_for_github_update, perform_update, schedule_restart
from app.ai_engine import evaluate_deal_score, evaluate_safety_risk, generate_negotiation_reply

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kleinanzeigen_radar")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Datenbank initialisieren und Hintergrund-Wächter starten
    init_db()
    watcher_service.start()
    logger.info(f"{APP_NAME} v{VERSION} erfolgreich gestartet.")
    yield
    # Shutdown: Hintergrund-Wächter beenden
    watcher_service.stop()
    logger.info(f"{APP_NAME} beendet.")

app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)

# Statische Dateien und Templates mounten
static_dir = BASE_DIR / "app" / "static"
templates_dir = BASE_DIR / "app" / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# --- Pydantic Datenmodelle ---

class SearchTerm(BaseModel):
    text: str
    type: str = "include"  # 'include' oder 'exclude'

class SearchCreateUpdate(BaseModel):
    name: str
    query: Optional[str] = ""
    keywords: Optional[str] = ""
    terms: Optional[List[SearchTerm]] = []
    case_sensitive: Optional[bool] = False
    search_in_description: Optional[bool] = True
    ocr_images: Optional[bool] = True
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    postal_code: Optional[str] = ""
    radius: Optional[int] = 0
    shipping_type: Optional[str] = "all"
    notify_telegram: Optional[bool] = True
    notify_email: Optional[bool] = True
    is_active: Optional[bool] = True
    interval_minutes: Optional[int] = 15
    platform: Optional[str] = "both"

class StatusUpdate(BaseModel):
    status: str  # 'new', 'starred', 'dismissed', 'read'

class NoteUpdate(BaseModel):
    notes: str

class NegotiationStepRequest(BaseModel):
    target_price: Optional[float] = None
    style: Optional[str] = "freundlich"
    stop_condition: Optional[str] = ""
    seller_message: Optional[str] = ""

# --- HTML Web-Oberfläche ---

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    try:
        init_searches = get_all_searches()
        init_results = get_results(limit=60)
        init_stats = get_stats()
    except Exception:
        init_searches, init_results, init_stats = [], [], {}

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": APP_NAME,
            "version": VERSION,
            "searches_json": json.dumps(init_searches, ensure_ascii=False),
            "results_json": json.dumps(init_results, ensure_ascii=False),
            "stats_json": json.dumps(init_stats, ensure_ascii=False)
        }
    )

# --- API: Statistiken & Dashboard ---

@app.get("/api/stats")
async def api_stats():
    return get_stats()

# --- API: Suchen ---

@app.get("/api/searches")
async def api_get_searches():
    return get_all_searches()

@app.get("/api/searches/preview-count")
async def api_preview_count(
    query: Optional[str] = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    postal_code: Optional[str] = "",
    radius: Optional[int] = 0
):
    count = fetch_live_result_count(
        query=query or "",
        min_price=min_price,
        max_price=max_price,
        postal_code=postal_code or "",
        radius=radius or 0
    )
    return {"count": count}

@app.post("/api/searches")
async def api_create_search(data: SearchCreateUpdate, bg: BackgroundTasks):
    search_dict = data.model_dump()
    new_id = create_search(search_dict)
    watcher_service.set_scan_progress(new_id, is_scanning=True, progress=5, step_text="Suchlauf wird vorbereitet...", found_count=0, total_ads=0)
    # Neue Suche direkt einmal im Hintergrund ausführen
    bg.add_task(watcher_service.execute_search_now, new_id)
    return {"id": new_id, "success": True}

@app.get("/api/searches/{search_id}")
async def api_get_search(search_id: int):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    return search

@app.get("/api/searches/{search_id}/progress")
async def api_get_search_progress(search_id: int):
    return watcher_service.get_scan_progress(search_id)

@app.put("/api/searches/{search_id}")
async def api_update_search(search_id: int, data: SearchCreateUpdate, bg: BackgroundTasks):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    update_search(search_id, data.model_dump())
    # Kriterien aktualisieren und bestehende Treffer erneut validieren (kein Datenverlust für passende Anzeigen!)
    removed_count = recheck_existing_results_for_search(search_id)
    logger.info(f"Suchauftrag {search_id} aktualisiert: {removed_count} unpassende Inserate bereinigt, passende Treffer erhalten.")
    watcher_service.set_scan_progress(search_id, is_scanning=True, progress=5, step_text="Kriterien aktualisiert, prüfe neue Treffer...", found_count=0, total_ads=0)
    bg.add_task(watcher_service.execute_search_now, search_id)
    return {"success": True, "removed_obsolete": removed_count}

@app.delete("/api/searches/{search_id}")
async def api_delete_search(search_id: int):
    delete_search(search_id)
    return {"success": True}

@app.post("/api/searches/{search_id}/run")
async def api_run_search(search_id: int, bg: BackgroundTasks, clear_existing: bool = False):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    if clear_existing:
        clear_results(search_id)
    watcher_service.set_scan_progress(search_id, is_scanning=True, progress=5, step_text="Suche manuell ausgelöst...", found_count=0, total_ads=0)
    bg.add_task(watcher_service.execute_search_now, search_id)
    return {"success": True, "message": "Suche im Hintergrund gestartet"}

# --- API: Ergebnisse ---

@app.get("/api/results")
async def api_get_results(
    search_id: Optional[int] = None,
    status: Optional[str] = None,
    platform_filter: Optional[str] = None,
    shipping_filter: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search_term: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    limit: int = 150
):
    effective_min = min_price
    effective_max = max_price
    if search_id:
        s = get_search(search_id)
        if s:
            if effective_min is None and s.get("min_price") is not None:
                effective_min = s["min_price"]
            if effective_max is None and s.get("max_price") is not None:
                effective_max = s["max_price"]

    return get_results(
        search_id=search_id,
        status=status,
        platform_filter=platform_filter,
        shipping_filter=shipping_filter,
        min_price=effective_min,
        max_price=effective_max,
        search_term=search_term,
        sort_by=sort_by or "newest",
        limit=limit
    )

@app.post("/api/results/{result_id}/status")
async def api_set_result_status(result_id: int, data: StatusUpdate):
    if data.status not in ["new", "starred", "dismissed", "read"]:
        raise HTTPException(status_code=400, detail="Ungültiger Status")
    update_result_status(result_id, data.status)
    return {"success": True}

@app.post("/api/results/mark-all-read")
async def api_mark_all_read(search_id: Optional[int] = None):
    mark_all_results_as_read(search_id)
    return {"success": True}

@app.post("/api/results/{result_id}/notes")
async def api_update_notes(result_id: int, data: NoteUpdate):
    res = get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden")
    update_result_notes(result_id, data.notes)
    return {"success": True, "notes": data.notes}

@app.get("/api/results/{result_id}/details")
async def api_get_result_details(result_id: int):
    res = get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden")

    desc = res.get("description") or ""
    images = res.get("images") or []
    # Falls die Beschreibung noch unvollständig ist (< 80 Zeichen) oder Bilder fehlen, von Kleinanzeigen nachladen
    if (len(desc) < 80 or len(images) <= 1) and res.get("url") and res.get("platform") != "facebook":
        try:
            full_desc, new_images, pub_date = fetch_ad_details(res["url"], DEFAULT_HEADERS)
            updated = False
            if full_desc and len(full_desc) > len(desc):
                desc = full_desc
                updated = True
            if new_images and len(new_images) > len(images):
                images = new_images
                updated = True
            if updated:
                update_result_details(result_id, desc, images)
                res["description"] = desc
                res["images"] = images
        except Exception as e:
            logger.warning(f"Konnte Details für Inserat {result_id} nicht nachladen: {e}")

    # Automatische KI-Deal- und Betrugs-Analyse, falls noch nicht erfolgt
    if not res.get("deal_score") or not res.get("safety_score"):
        try:
            search = get_search(res["search_id"]) if res.get("search_id") else None
            min_b = search.get("min_price") if search else None
            max_b = search.get("max_price") if search else None
            peers = [r["price_num"] for r in get_results(search_id=res.get("search_id"), limit=50) if r.get("price_num")]

            if not res.get("deal_score"):
                ds = evaluate_deal_score(
                    title=res["title"],
                    price=res.get("price_num"),
                    description=desc,
                    platform=res.get("platform", "kleinanzeigen"),
                    min_budget=min_b,
                    max_budget=max_b,
                    peer_prices=peers
                )
                update_result_deal_score(result_id, ds)
                res["deal_score"] = ds

            if not res.get("safety_score"):
                ss = evaluate_safety_risk(
                    title=res["title"],
                    price=res.get("price_num"),
                    description=desc,
                    platform=res.get("platform", "kleinanzeigen")
                )
                update_result_safety_score(result_id, ss)
                res["safety_score"] = ss
        except Exception as e_ai:
            logger.warning(f"Fehler bei automatischer Deal/Safety Analyse für Inserat {result_id}: {e_ai}")

    return res

@app.post("/api/results/{result_id}/evaluate-ai")
async def api_evaluate_ai(result_id: int):
    res = get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden")

    search = get_search(res["search_id"]) if res.get("search_id") else None
    min_b = search.get("min_price") if search else None
    max_b = search.get("max_price") if search else None
    peers = [r["price_num"] for r in get_results(search_id=res.get("search_id"), limit=50) if r.get("price_num")]

    deal_score = evaluate_deal_score(
        title=res["title"],
        price=res.get("price_num"),
        description=res.get("description", ""),
        platform=res.get("platform", "kleinanzeigen"),
        min_budget=min_b,
        max_budget=max_b,
        peer_prices=peers
    )

    safety_score = evaluate_safety_risk(
        title=res["title"],
        price=res.get("price_num"),
        description=res.get("description", ""),
        platform=res.get("platform", "kleinanzeigen")
    )

    update_result_deal_score(result_id, deal_score)
    update_result_safety_score(result_id, safety_score)

    return {
        "deal_score": deal_score,
        "safety_score": safety_score
    }

@app.get("/api/results/{result_id}/negotiation")
async def api_get_negotiation(result_id: int):
    res = get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden")
    return res.get("negotiation") or {}

@app.post("/api/results/{result_id}/negotiation/step")
async def api_step_negotiation(result_id: int, data: NegotiationStepRequest):
    res = get_result_by_id(result_id)
    if not res:
        raise HTTPException(status_code=404, detail="Inserat nicht gefunden")

    neg = res.get("negotiation") or {}
    history = list(neg.get("history") or [])
    settings = get_settings()

    if data.seller_message and data.seller_message.strip():
        history.append({
            "sender": "seller",
            "text": data.seller_message.strip(),
            "timestamp": datetime.now().strftime("%H:%M")
        })

    style = data.style or settings.get("ai_negotiation_style") or "freundlich"
    target_price = data.target_price if data.target_price is not None else neg.get("target_price")
    stop_condition = data.stop_condition if data.stop_condition is not None else neg.get("stop_condition", "")

    reply_data = generate_negotiation_reply(
        title=res["title"],
        current_price=res.get("price_num"),
        description=res.get("description", ""),
        target_price=target_price,
        style=style,
        stop_condition=stop_condition,
        chat_history=history,
        latest_seller_message=data.seller_message or "",
        ai_settings=settings
    )

    history.append({
        "sender": "assistant",
        "text": reply_data["reply_text"],
        "strategy": reply_data.get("strategy", ""),
        "timestamp": datetime.now().strftime("%H:%M")
    })

    neg_updated = {
        "target_price": target_price,
        "style": style,
        "stop_condition": stop_condition,
        "history": history,
        "should_stop": reply_data.get("should_stop", False),
        "stop_reason": reply_data.get("stop_reason", ""),
        "target_reached": reply_data.get("target_reached", False),
        "last_suggestion": reply_data["reply_text"]
    }

    update_result_negotiation(result_id, neg_updated)
    return neg_updated

# --- API: Einstellungen ---

@app.get("/api/settings")
async def api_get_settings():
    s = get_settings()
    # Maskiere Passwort aus Sicherheitsgründen in der Anzeige
    if s.get("email_smtp_password"):
        s["email_smtp_password_masked"] = True
    else:
        s["email_smtp_password_masked"] = False
    return s

@app.post("/api/settings")
async def api_save_settings(data: Dict[str, Any]):
    current = get_settings()
    # Wenn kein neues Passwort übergeben wurde, das alte behalten
    if not data.get("email_smtp_password") and current.get("email_smtp_password"):
        data["email_smtp_password"] = current["email_smtp_password"]
    save_settings(data)
    return {"success": True}

@app.post("/api/settings/test-telegram")
async def api_test_telegram(data: Dict[str, str]):
    token = data.get("telegram_bot_token") or get_settings().get("telegram_bot_token")
    chat_id = data.get("telegram_chat_id") or get_settings().get("telegram_chat_id")
    return test_telegram_connection(token, chat_id)

@app.post("/api/settings/test-email")
async def api_test_email(data: Dict[str, Any]):
    current = get_settings()
    merged = {**current, **data}
    return test_email_connection(merged)

# --- API: System & GitHub Updater ---

@app.get("/api/system/version")
async def api_get_version():
    return {
        "app_name": APP_NAME,
        "version": VERSION
    }

@app.get("/api/system/update/check")
async def api_update_check():
    return check_for_github_update()

@app.post("/api/system/update/perform")
async def api_update_perform():
    return perform_update()

@app.post("/api/system/restart")
async def api_system_restart():
    schedule_restart(1.0)
    return {"success": True, "message": "Neustart eingeleitet..."}

