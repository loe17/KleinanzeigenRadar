import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Tabelle für Suchaufträge
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        query TEXT NOT NULL,
        keywords TEXT DEFAULT '',
        case_sensitive INTEGER DEFAULT 0,
        search_in_description INTEGER DEFAULT 1,
        ocr_images INTEGER DEFAULT 1,
        min_price REAL,
        max_price REAL,
        postal_code TEXT DEFAULT '',
        radius INTEGER DEFAULT 0,
        shipping_type TEXT DEFAULT 'all', -- 'all', 'shipping_only', 'pickup_only'
        notify_telegram INTEGER DEFAULT 1,
        notify_email INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        interval_minutes INTEGER DEFAULT 15,
        last_run TEXT,
        created_at TEXT NOT NULL,
        terms_json TEXT DEFAULT '[]'
    );
    """)

    # Prüfen, ob Spalte terms_json existiert (falls Tabelle schon angelegt war)
    cursor.execute("PRAGMA table_info(searches)")
    columns = [row[1] for row in cursor.fetchall()]
    if "terms_json" not in columns:
        cursor.execute("ALTER TABLE searches ADD COLUMN terms_json TEXT DEFAULT '[]'")

    # Tabelle für gefundene Inserate
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_id INTEGER NOT NULL,
        kleinanzeigen_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        price TEXT,
        price_num REAL,
        location TEXT,
        distance TEXT,
        shipping_possible INTEGER DEFAULT 0,
        url TEXT NOT NULL,
        thumbnail_url TEXT,
        images_json TEXT DEFAULT '[]',
        description TEXT,
        ocr_text TEXT DEFAULT '',
        match_reason TEXT,
        status TEXT DEFAULT 'new', -- 'new', 'starred', 'dismissed', 'read'
        notified_telegram INTEGER DEFAULT 0,
        notified_email INTEGER DEFAULT 0,
        found_at TEXT NOT NULL,
        FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
    );
    """)

    # Tabelle für globale Einstellungen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Standard-Einstellungen eintragen falls noch nicht vorhanden
    defaults = {
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "email_smtp_host": "",
        "email_smtp_port": "587",
        "email_smtp_user": "",
        "email_smtp_password": "",
        "email_smtp_tls": "1",
        "email_from": "",
        "email_to": "",
        "global_interval_minutes": "15",
        "github_repo": "loe17/KleinanzeigenRadar"
    }

    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

# --- Hilfsfunktionen für Einstellungen ---

def get_settings() -> Dict[str, str]:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] or "" for row in rows}

def save_settings(new_settings: Dict[str, str]):
    conn = get_db()
    for k, v in new_settings.items():
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, str(v)))
    conn.commit()
    conn.close()

# --- Hilfsfunktionen für Suchaufträge ---

def format_datetime_str(dt_str: Optional[str]) -> str:
    """Wandelt einen ISO-Zeitstempel in deutsches Datums- und Uhrzeitformat um."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y, %H:%M Uhr")
    except Exception:
        return dt_str

def _enrich_search_dict(search_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Erweitert den Suchauftrag um formatierte Zeitstempel und die Begriffsliste."""
    terms = []
    raw_terms_json = search_dict.get("terms_json")
    if raw_terms_json:
        try:
            terms = json.loads(raw_terms_json)
        except Exception:
            terms = []

    if not terms:
        # Falls terms_json noch leer ist, migrieren wir aus query und keywords
        query = (search_dict.get("query") or "").strip()
        if query:
            terms.append({"text": query, "type": "include"})
        keywords_str = (search_dict.get("keywords") or "").strip()
        if keywords_str:
            for kw in re.split(r"[,;\n]+", keywords_str):
                kw = kw.strip()
                if not kw:
                    continue
                if kw.startswith("-") or kw.startswith("!"):
                    terms.append({"text": kw[1:].strip(), "type": "exclude"})
                else:
                    terms.append({"text": kw, "type": "include"})

    search_dict["terms"] = terms
    search_dict["created_at_formatted"] = format_datetime_str(search_dict.get("created_at"))
    search_dict["last_run_formatted"] = format_datetime_str(search_dict.get("last_run")) or "Noch nie geprüft"
    return search_dict

def get_all_searches(active_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_db()
    query = "SELECT * FROM searches"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY id DESC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [_enrich_search_dict(dict(row)) for row in rows]

def get_search(search_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    conn.close()
    return _enrich_search_dict(dict(row)) if row else None

def create_search(data: Dict[str, Any]) -> int:
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    terms = data.get("terms") or []
    if terms:
        terms_json = json.dumps(terms, ensure_ascii=False)
        include_list = [t["text"].strip() for t in terms if t.get("type") == "include" and t.get("text", "").strip()]
        exclude_list = [f"-{t['text'].strip()}" for t in terms if t.get("type") == "exclude" and t.get("text", "").strip()]
        query_val = include_list[0] if include_list else (data.get("query") or "")
        keywords_val = ", ".join(include_list[1:] + exclude_list)
    else:
        query_val = data.get("query", "")
        keywords_val = data.get("keywords", "")
        terms_list = []
        if query_val:
            terms_list.append({"text": query_val.strip(), "type": "include"})
        terms_json = json.dumps(terms_list, ensure_ascii=False)

    cursor.execute("""
    INSERT INTO searches (
        name, query, keywords, terms_json, case_sensitive, search_in_description,
        ocr_images, min_price, max_price, postal_code, radius,
        shipping_type, notify_telegram, notify_email, is_active,
        interval_minutes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        query_val,
        keywords_val,
        terms_json,
        1 if data.get("case_sensitive") else 0,
        1 if data.get("search_in_description", True) else 0,
        1 if data.get("ocr_images", True) else 0,
        data.get("min_price"),
        data.get("max_price"),
        data.get("postal_code", ""),
        data.get("radius", 0),
        data.get("shipping_type", "all"),
        1 if data.get("notify_telegram", True) else 0,
        1 if data.get("notify_email", True) else 0,
        1 if data.get("is_active", True) else 0,
        data.get("interval_minutes", 15),
        now
    ))
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id

def update_search(search_id: int, data: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()

    terms = data.get("terms") or []
    if terms:
        terms_json = json.dumps(terms, ensure_ascii=False)
        include_list = [t["text"].strip() for t in terms if t.get("type") == "include" and t.get("text", "").strip()]
        exclude_list = [f"-{t['text'].strip()}" for t in terms if t.get("type") == "exclude" and t.get("text", "").strip()]
        query_val = include_list[0] if include_list else (data.get("query") or "")
        keywords_val = ", ".join(include_list[1:] + exclude_list)
    else:
        query_val = data.get("query", "")
        keywords_val = data.get("keywords", "")
        terms_list = []
        if query_val:
            terms_list.append({"text": query_val.strip(), "type": "include"})
        terms_json = json.dumps(terms_list, ensure_ascii=False)

    cursor.execute("""
    UPDATE searches SET
        name = ?,
        query = ?,
        keywords = ?,
        terms_json = ?,
        case_sensitive = ?,
        search_in_description = ?,
        ocr_images = ?,
        min_price = ?,
        max_price = ?,
        postal_code = ?,
        radius = ?,
        shipping_type = ?,
        notify_telegram = ?,
        notify_email = ?,
        is_active = ?,
        interval_minutes = ?
    WHERE id = ?
    """, (
        data.get("name"),
        query_val,
        keywords_val,
        terms_json,
        1 if data.get("case_sensitive") else 0,
        1 if data.get("search_in_description", True) else 0,
        1 if data.get("ocr_images", True) else 0,
        data.get("min_price"),
        data.get("max_price"),
        data.get("postal_code", ""),
        data.get("radius", 0),
        data.get("shipping_type", "all"),
        1 if data.get("notify_telegram", True) else 0,
        1 if data.get("notify_email", True) else 0,
        1 if data.get("is_active", True) else 0,
        data.get("interval_minutes", 15),
        search_id
    ))
    conn.commit()
    conn.close()

def delete_search(search_id: int):
    conn = get_db()
    conn.execute("DELETE FROM results WHERE search_id = ?", (search_id,))
    conn.execute("DELETE FROM searches WHERE id = ?", (search_id,))
    conn.commit()
    conn.close()

def update_search_last_run(search_id: int):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute("UPDATE searches SET last_run = ? WHERE id = ?", (now, search_id))
    conn.commit()
    conn.close()

# --- Hilfsfunktionen für Ergebnisse ---

def save_result(result_data: Dict[str, Any]) -> Optional[int]:
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute("""
        INSERT INTO results (
            search_id, kleinanzeigen_id, title, price, price_num,
            location, distance, shipping_possible, url, thumbnail_url,
            images_json, description, ocr_text, match_reason,
            status, notified_telegram, notified_email, found_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_data["search_id"],
            result_data["kleinanzeigen_id"],
            result_data["title"],
            result_data.get("price", ""),
            result_data.get("price_num"),
            result_data.get("location", ""),
            result_data.get("distance", ""),
            1 if result_data.get("shipping_possible") else 0,
            result_data["url"],
            result_data.get("thumbnail_url", ""),
            json.dumps(result_data.get("images", [])),
            result_data.get("description", ""),
            result_data.get("ocr_text", ""),
            result_data.get("match_reason", ""),
            result_data.get("status", "new"),
            1 if result_data.get("notified_telegram") else 0,
            1 if result_data.get("notified_email") else 0,
            now
        ))
        res_id = cursor.lastrowid
        conn.commit()
        return res_id
    except sqlite3.IntegrityError:
        # Bereits in der Datenbank vorhanden
        return None
    finally:
        conn.close()

def get_results(
    search_id: Optional[int] = None,
    status: Optional[str] = None,
    shipping_filter: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search_term: Optional[str] = None,
    limit: int = 150
) -> List[Dict[str, Any]]:
    conn = get_db()
    query = """
    SELECT r.*, s.name as search_name 
    FROM results r
    LEFT JOIN searches s ON r.search_id = s.id
    WHERE 1=1
    """
    params = []

    if search_id:
        query += " AND r.search_id = ?"
        params.append(search_id)

    if status and status != "all":
        query += " AND r.status = ?"
        params.append(status)

    if shipping_filter == "shipping_only":
        query += " AND r.shipping_possible = 1"
    elif shipping_filter == "pickup_only":
        query += " AND r.shipping_possible = 0"

    if min_price is not None:
        query += " AND r.price_num >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND r.price_num <= ?"
        params.append(max_price)

    if search_term:
        query += " AND (r.title LIKE ? OR r.description LIKE ? OR r.ocr_text LIKE ?)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term])

    query += " ORDER BY r.id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["images"] = json.loads(d.get("images_json") or "[]")
        except:
            d["images"] = []
        results.append(d)
    return results

def update_result_status(result_id: int, status: str):
    conn = get_db()
    conn.execute("UPDATE results SET status = ? WHERE id = ?", (status, result_id))
    conn.commit()
    conn.close()

def mark_all_results_as_read(search_id: Optional[int] = None):
    conn = get_db()
    if search_id:
        conn.execute("UPDATE results SET status = 'read' WHERE search_id = ? AND status = 'new'", (search_id,))
    else:
        conn.execute("UPDATE results SET status = 'read' WHERE status = 'new'")
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, int]:
    conn = get_db()
    total_searches = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
    active_searches = conn.execute("SELECT COUNT(*) FROM searches WHERE is_active = 1").fetchone()[0]
    total_results = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    new_results = conn.execute("SELECT COUNT(*) FROM results WHERE status = 'new'").fetchone()[0]
    starred_results = conn.execute("SELECT COUNT(*) FROM results WHERE status = 'starred'").fetchone()[0]
    conn.close()
    return {
        "total_searches": total_searches,
        "active_searches": active_searches,
        "total_results": total_results,
        "new_results": new_results,
        "starred_results": starred_results
    }
