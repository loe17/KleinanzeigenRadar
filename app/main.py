import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

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
    save_settings
)
from app.watcher import watcher_service
from app.notifier import test_telegram_connection, test_email_connection
from app.updater import check_for_github_update, perform_update

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

class SearchCreateUpdate(BaseModel):
    name: str
    query: str
    keywords: Optional[str] = ""
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

class StatusUpdate(BaseModel):
    status: str  # 'new', 'starred', 'dismissed', 'read'

# --- HTML Web-Oberfläche ---

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": APP_NAME,
            "version": VERSION
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

@app.post("/api/searches")
async def api_create_search(data: SearchCreateUpdate, bg: BackgroundTasks):
    search_dict = data.model_dump()
    new_id = create_search(search_dict)
    # Neue Suche direkt einmal im Hintergrund ausführen
    bg.add_task(watcher_service.execute_search_now, new_id)
    return {"id": new_id, "success": True}

@app.get("/api/searches/{search_id}")
async def api_get_search(search_id: int):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    return search

@app.put("/api/searches/{search_id}")
async def api_update_search(search_id: int, data: SearchCreateUpdate):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    update_search(search_id, data.model_dump())
    return {"success": True}

@app.delete("/api/searches/{search_id}")
async def api_delete_search(search_id: int):
    delete_search(search_id)
    return {"success": True}

@app.post("/api/searches/{search_id}/run")
async def api_run_search(search_id: int, bg: BackgroundTasks):
    search = get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Suchauftrag nicht gefunden")
    bg.add_task(watcher_service.execute_search_now, search_id)
    return {"success": True, "message": "Suche im Hintergrund gestartet"}

# --- API: Ergebnisse ---

@app.get("/api/results")
async def api_get_results(
    search_id: Optional[int] = None,
    status: Optional[str] = None,
    shipping_filter: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search_term: Optional[str] = None,
    limit: int = 150
):
    return get_results(
        search_id=search_id,
        status=status,
        shipping_filter=shipping_filter,
        min_price=min_price,
        max_price=max_price,
        search_term=search_term,
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
