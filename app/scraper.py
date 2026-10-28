import re
import time
import random
import logging
import json
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple, Callable
import requests
from bs4 import BeautifulSoup

from app.config import DEFAULT_USER_AGENT
from app.ocr import analyze_listing_images

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleinanzeigen.de"

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": BASE_URL,
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

def clean_slug(text: str) -> str:
    """Wandelt einen Suchbegriff in einen suchmaschinenfreundlichen Kleinanzeigen-Slug um."""
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")

def build_search_url_for_query(
    query: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    postal_code: str = "",
    radius: int = 0
) -> str:
    """Baut eine moderne SEO-URL für Kleinanzeigen basierend auf Parametern."""
    parts = []

    # Preis-Pfad
    has_min = min_price is not None and str(min_price).strip() != ""
    has_max = max_price is not None and str(max_price).strip() != ""
    if has_min or has_max:
        min_s = str(int(float(min_price))) if has_min else ""
        max_s = str(int(float(max_price))) if has_max else ""
        parts.append(f"preis:{min_s}:{max_s}")

    # PLZ & Umkreis
    plz_clean = str(postal_code).strip() if postal_code else ""
    if plz_clean:
        if radius and int(radius) > 0:
            parts.append(f"{plz_clean}/umkreis:{int(radius)}")
        else:
            parts.append(f"{plz_clean}")

    # Suchbegriff
    slug = clean_slug(query)
    if slug:
        parts.append(slug)

    path = "/".join(parts)
    if path:
        return f"{BASE_URL}/s-{path}/k0?sortingField=SORTING_DATE"
    return f"{BASE_URL}/s-k0?sortingField=SORTING_DATE"

def build_search_url(search: Dict[str, Any]) -> str:
    """Kompatibilitäts-Funktion: Baut die Such-URL für einen Suchauftrag."""
    query = search.get("query", "")
    terms = search.get("terms") or []
    if terms:
        includes = [t["text"] for t in terms if t.get("type") == "include" and t.get("text")]
        if includes:
            query = includes[0]

    return build_search_url_for_query(
        query=query,
        min_price=search.get("min_price"),
        max_price=search.get("max_price"),
        postal_code=search.get("postal_code", ""),
        radius=search.get("radius", 0)
    )

def fetch_live_result_count(
    query: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    postal_code: str = "",
    radius: int = 0
) -> int:
    """Fragt bei Kleinanzeigen die aktuelle Anzahl an Treffern für eine Suche ab."""
    url = build_search_url_for_query(
        query=query,
        min_price=min_price,
        max_price=max_price,
        postal_code=postal_code,
        radius=radius
    )
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=8)
        if resp.status_code != 200:
            logger.warning(f"Live-Count Abfrage gab Status {resp.status_code} zurück für {url}")
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")
        summary = soup.find(id="srp-breadcrumb-summary") or soup.find(class_="breadcrumb-summary")
        summary_text = summary.get_text(strip=True) if summary else resp.text

        match = re.search(r"([\d.,]+)\s*Ergebnisse", summary_text)
        if match:
            clean_num = match.group(1).replace(".", "").replace(",", "")
            return int(clean_num)
        return 0
    except Exception as e:
        logger.warning(f"Fehler bei Live-Count Abfrage für '{query}': {e}")
        return 0

def parse_price(price_str: str) -> Optional[float]:
    """Wandelt einen Preis-String wie '120 € VB' oder '1.250 €' in eine Zahl um."""
    if not price_str:
        return None
    cleaned = price_str.lower().strip()
    if "zu verschenken" in cleaned:
        return 0.0
    # Zahlen mit Punkten/Kommas herausfiltern
    match = re.search(r"(\d+(?:[.]\d+)*(?:,\d+)?)", cleaned)
    if match:
        num_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return None
    return None

def fetch_ad_details(ad_url: str, headers: Dict[str, str]) -> Tuple[str, List[str], str]:
    """Ruft die Detailseite einer Anzeige ab für vollständige Beschreibung, Galerie-Bilder und Datum."""
    try:
        time.sleep(random.uniform(0.1, 0.25))  # Kurze Pause
        resp = requests.get(ad_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return "", [], ""

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Vollständige Beschreibung extrahieren
        desc_elem = soup.find(id="viewad-description-text")
        full_description = desc_elem.get_text(separator="\n", strip=True) if desc_elem else ""

        # Große Galerie-Bilder extrahieren
        image_urls = []
        gallery = soup.find_all("img", id=re.compile(r"viewad-image"))
        for img in gallery:
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and src not in image_urls:
                image_urls.append(src)

        # Falls keine Hauptbilder gefunden, Thumbnails aus Galerie prüfen
        if not image_urls:
            thumbnails = soup.select(".galleryimage-element img")
            for img in thumbnails:
                src = img.get("data-src") or img.get("src")
                if src and src.startswith("http") and src not in image_urls:
                    image_urls.append(src)

        # Veröffentlichungsdatum aus Detailansicht
        published_date = ""
        extra_info = soup.find(id="viewad-extra-info")
        if extra_info:
            date_span = extra_info.find("span")
            if date_span:
                published_date = date_span.get_text(strip=True)

        return full_description, image_urls, published_date
    except Exception as e:
        logger.warning(f"Fehler beim Laden der Detailseite {ad_url}: {e}")
        return "", [], ""

def compile_keyword_pattern(term: str, case_sensitive: bool = False) -> re.Pattern:
    """Wandelt einen Such- oder Ausschlussbegriff mit optionalen Wildcards (*, ?) in ein Regex um.
    
    Unterstützt flexible Wortbestandteil- und Wortgrenzen-Suche:
      *15*        -> Sucht '15' irgendwo im Wort/Text (z. B. '15Zoll', 'XPS15', '15 Zoll')
      15*         -> Sucht '15' am Wortanfang (z. B. '15Zoll', '15cm')
      *15         -> Sucht '15' am Wortende (z. B. 'XPS15')
      15          -> Sucht das eigenständige Wort '15' (Wortgrenzen auf beiden Seiten)
      *16*GB      -> Findet '16GB', '16 GB', '16-GB', 'RAM: 16 GB', '16 GB RAM'
      16GB / 16 GB-> Automatische Toleranz für optionale Leerzeichen zwischen Zahl & Einheit
      *defekt*    -> Findet 'Teildefekt', 'defekt', 'Defektgerät'
      defekt      -> Findet nur 'defekt', aber nicht 'Teildefekt'
      Dell Lat*   -> Findet 'Dell Latitude'
    """
    term = term.strip()
    if not term:
        return re.compile(r"$^")
    
    starts_wild = term.startswith("*")
    ends_wild = term.endswith("*")
    
    core = term.strip("*")
    if not core:
        return re.compile(r".*")
        
    prefix = "" if starts_wild else (r"\b" if core[0].isalnum() else "")
    suffix = "" if ends_wild else (r"\b" if core[-1].isalnum() else "")
    
    parts = term.split("*")
    escaped_parts = []
    for p in parts:
        if not p:
            continue
        p_esc = re.escape(p).replace(r"\?", r".")
        # Automatische Toleranz für optionale Leerzeichen zwischen Zahlen und Einheiten (z. B. 16GB -> 16\s*GB)
        p_esc = re.sub(r"(\d+)\\?([a-zA-Z]+)", r"\1\\s*\2", p_esc)
        p_esc = re.sub(r"(\d+)\\\s+([a-zA-Z]+)", r"\1\\s*\2", p_esc)
        p_esc = re.sub(r"\\\s+", r"\\s+", p_esc)
        escaped_parts.append(p_esc)
        
    inner = r".{0,15}?".join(escaped_parts)
    pattern_str = f"{prefix}{inner}{suffix}"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern_str, flags)

def matches_keywords(
    search_criteria: Dict[str, Any],
    title: str,
    description: str,
    ocr_text: str,
    matched_term: Optional[str] = None
) -> Tuple[bool, str]:
    """Prüft, ob Suchbegriffe und Ausschlusskriterien erfüllt sind."""
    case_sensitive = bool(search_criteria.get("case_sensitive", False))
    search_in_desc = bool(search_criteria.get("search_in_description", True))

    title_str = title or ""
    desc_str = (description or "") if search_in_desc else ""
    ocr_str = ocr_text or ""

    terms = search_criteria.get("terms") or []
    include_words = []
    exclude_words = []

    if terms:
        for t in terms:
            txt = t.get("text", "").strip()
            if not txt:
                continue
            if t.get("type") == "exclude":
                exclude_words.append(txt)
            else:
                include_words.append(txt)
    else:
        raw_keywords = search_criteria.get("keywords", "") or ""
        lines = [kw.strip() for kw in re.split(r"[,\n]+", raw_keywords) if kw.strip()]
        for kw in lines:
            if kw.startswith("-") or kw.startswith("!"):
                exclude_words.append(kw[1:].strip())
            else:
                include_words.append(kw)

    # Ausschlussprüfung: Wenn irgendein Ausschlussbegriff vorkommt -> sofort verwerfen
    for word in exclude_words:
        rx = compile_keyword_pattern(word, case_sensitive)
        if rx.search(title_str) or (search_in_desc and rx.search(desc_str)) or rx.search(ocr_str):
            return False, f"Ausgeschlossen durch Kriterium: '{word}'"

    # Alle definierten Suchbegriffe müssen irgendwo vorkommen (in Titel, Beschreibung oder Bild-Text)
    title_matches = []
    desc_matches = []
    ocr_matches = []

    for word in include_words:
        rx = compile_keyword_pattern(word, case_sensitive)
        in_title = bool(rx.search(title_str))
        in_desc = bool(rx.search(desc_str)) if search_in_desc else False
        in_ocr = bool(rx.search(ocr_str))

        if not (in_title or in_desc or in_ocr):
            # Sobald auch nur EIN definierter Suchbegriff fehlt -> KEIN Treffer!
            return False, f"Fehlender Suchbegriff: '{word}'"

        if in_title:
            title_matches.append(word)
        elif in_desc:
            m = rx.search(desc_str)
            if m:
                s_start = max(0, m.start() - 15)
                s_end = min(len(desc_str), m.end() + 20)
                snip = desc_str[s_start:s_end].replace("\n", " ").strip()
                prefix_dot = "..." if s_start > 0 else ""
                suffix_dot = "..." if s_end < len(desc_str) else ""
                desc_matches.append(f"'{word}' ({prefix_dot}{snip}{suffix_dot})")
            else:
                desc_matches.append(f"'{word}'")
        elif in_ocr:
            ocr_matches.append(f"'{word}'")

    sections = []
    if title_matches:
        terms_str = ", ".join(repr(w) for w in title_matches)
        sections.append(f"Titel ({terms_str})")
    if desc_matches:
        sections.append(f"Beschreibung: {', '.join(desc_matches)}")
    if ocr_matches:
        sections.append(f"Bild-Text: {', '.join(ocr_matches)}")

    location_str = " • ".join(sections)
    return True, f"Treffer in: {location_str}" if location_str else "Treffer durch Kriterien"

def parse_articles_from_soup(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extrahiert Inserate aus dem HTML von Kleinanzeigen (unterstützt modernes und älteres Layout)."""
    articles = soup.find_all("article", attrs={"data-adid": True})
    if not articles:
        articles = soup.find_all("article", class_="aditem")
    if not articles:
        articles = soup.find_all("li", class_="ad-listitem")

    results = []

    for item in articles:
        try:
            adid = item.get("data-adid")
            if not adid:
                link_elem = item.find("a", href=re.compile(r"/s-anzeige/"))
                if link_elem:
                    m = re.search(r"/(\d+)-", link_elem.get("href", ""))
                    adid = m.group(1) if m else None
            if not adid:
                continue

            rel_url = item.get("data-href") or ""
            if not rel_url:
                a_elem = item.find("a", href=re.compile(r"/s-anzeige/"))
                if a_elem:
                    rel_url = a_elem.get("href", "")
            full_url = BASE_URL + rel_url if rel_url.startswith("/") else rel_url

            ld_data = {}
            ld_script = item.find("script", type="application/ld+json")
            if ld_script and ld_script.string:
                try:
                    ld_data = json.loads(ld_script.string)
                except Exception:
                    pass

            title = ld_data.get("title") or ""
            if not title:
                t_elem = item.find("h3") or item.find("h2") or item.find("a", class_=re.compile("ellipsis"))
                title = t_elem.get_text(strip=True) if t_elem else ""
            if not title:
                continue

            thumbnail = ld_data.get("contentUrl") or ""
            if not thumbnail:
                img_elem = item.find("img")
                if img_elem:
                    thumbnail = img_elem.get("src") or img_elem.get("data-src") or ""

            short_desc = ld_data.get("description") or ""
            if not short_desc:
                desc_elem = item.select_one(".aditem-main--middle--description") or item.find("p")
                short_desc = desc_elem.get_text(strip=True) if desc_elem else ""

            price_text = ""
            p_elem = item.find("p", class_=re.compile(r"text-title3|price"))
            if p_elem:
                price_text = p_elem.get_text(strip=True)
            if not price_text:
                m_price = re.search(r"(\d+(?:[.]\d+)*(?:,\d+)?\s*€(?:\s*VB)?)", item.get_text())
                if m_price:
                    price_text = m_price.group(1)
                elif "zu verschenken" in item.get_text().lower():
                    price_text = "Zu verschenken"
                elif "vb" in item.get_text().lower():
                    price_text = "VB"
            numeric_price = parse_price(price_text)

            item_text = item.get_text().lower()
            shipping_possible = "versand" in item_text

            location_str = ""
            loc_match = re.search(r"\b(\d{5}\s+[A-Za-zÄÖÜäöüß\s\-\/]+)", item.get_text())
            if loc_match:
                location_str = loc_match.group(1).split("\n")[0].strip()
            if not location_str:
                loc_elem = item.select_one(".aditem-main--top--left")
                if loc_elem:
                    location_str = loc_elem.get_text(separator=" ", strip=True)

            # Datum der Anzeige ermitteln
            published_date = ""
            date_elem = item.select_one(".aditem-main--top--right")
            if date_elem:
                published_date = date_elem.get_text(strip=True)
            if not published_date:
                m_date = re.search(r"\b(Heute,\s*\d{1,2}:\d{2}|Gestern,\s*\d{1,2}:\d{2}|\d{1,2}\.\d{1,2}\.\d{2,4})\b", item.get_text())
                if m_date:
                    published_date = m_date.group(1).strip()

            results.append({
                "adid": str(adid),
                "title": title,
                "price_text": price_text,
                "numeric_price": numeric_price,
                "shipping_possible": shipping_possible,
                "location": location_str,
                "thumbnail": thumbnail,
                "url": full_url,
                "description": short_desc,
                "published_date": published_date
            })
        except Exception as e:
            logger.warning(f"Fehler beim Parsen eines Inserats: {e}")
            continue

    return results

def scrape_search(
    search: Dict[str, Any],
    on_ad_found: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_progress: Optional[Callable[[int, str, int, int], None]] = None
) -> List[Dict[str, Any]]:
    """Führt eine Suche auf Kleinanzeigen mit allen Such- & Ausschlussbegriffen durch."""
    terms = search.get("terms") or []
    include_terms = [t["text"].strip() for t in terms if t.get("type") == "include" and t.get("text", "").strip()]
    exclude_terms = [t["text"].strip() for t in terms if t.get("type") == "exclude" and t.get("text", "").strip()]

    if not include_terms and search.get("query"):
        include_terms = [search["query"].strip()]

    search_queries = []
    if include_terms:
        # Für die Kleinanzeigen-Such-URL bereinigen wir Wildcards (*, ?), damit Kleinanzeigen
        # sauber nach dem Kernbegriff sucht
        clean_terms = [re.sub(r"[*?]+", "", it).strip() for it in include_terms]
        clean_terms = [t for t in clean_terms if t]

        if clean_terms:
            # Hauptabfrage mit allen Kernbegriffen kombiniert (z. B. "Lenovo T480")
            combined = " ".join(clean_terms)
            search_queries.append(combined)
        else:
            search_queries = [""]
    else:
        search_queries = [""]

    all_matched = {}

    if on_progress:
        display_q = search_queries[0] if search_queries and search_queries[0] else search.get("name", "Suchauftrag")
        on_progress(10, f"Frage Kleinanzeigen nach '{display_q}' ab...", 0, 0)

    for query_term in search_queries:
        url = build_search_url_for_query(
            query=query_term,
            min_price=search.get("min_price"),
            max_price=search.get("max_price"),
            postal_code=search.get("postal_code", ""),
            radius=search.get("radius", 0)
        )
        logger.info(f"Suche '{search.get('name')}' - Abruf Begriff '{query_term}' unter: {url}")

        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Kleinanzeigen antwortete mit Status {resp.status_code} für '{query_term}'")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            parsed_items = parse_articles_from_soup(soup)
            logger.info(f"Gefundene Anzeigen auf Seite für '{query_term}': {len(parsed_items)}")
        except Exception as e:
            logger.error(f"Fehler bei Anfrage an Kleinanzeigen für '{query_term}': {e}")
            continue

        total_items = len(parsed_items)
        if on_progress:
            on_progress(25, f"{total_items} Inserate auf Kleinanzeigen geladen. Prüfe Kriterien...", len(all_matched), total_items)

        for idx, ad in enumerate(parsed_items, 1):
            adid = ad["adid"]
            if adid in all_matched:
                continue

            pct = 25 + int((idx / max(1, total_items)) * 70)
            if on_progress:
                on_progress(pct, f"Prüfe Inserat {idx} von {total_items}...", len(all_matched), total_items)

            # Preis-Filter
            min_p = search.get("min_price")
            max_p = search.get("max_price")
            num_p = ad["numeric_price"]
            if num_p is not None:
                if min_p is not None and str(min_p).strip() != "" and num_p < float(min_p):
                    continue
                if max_p is not None and str(max_p).strip() != "" and num_p > float(max_p):
                    continue

            # Versand-Filter
            shipping_pref = search.get("shipping_type", "all")
            if shipping_pref == "shipping_only" and not ad["shipping_possible"]:
                continue
            if shipping_pref == "pickup_only" and ad["shipping_possible"]:
                continue

            full_description = ad["description"]
            all_images = [ad["thumbnail"]] if ad["thumbnail"] else []
            ocr_text = ""

            # 1. Schnelle Vorprüfung mit den bereits vorhandenen Daten der Suchergebnisseite
            is_match, reason = matches_keywords(
                search_criteria=search,
                title=ad["title"],
                description=full_description,
                ocr_text="",
                matched_term=query_term
            )

            # 2. Falls durch Ausschlusskriterium im Titel/Text verworfen -> sofort überspringen
            if not is_match and "Ausgeschlossen" in reason:
                continue

            published_date = ad.get("published_date", "")

            # 3. Falls noch kein Treffer, aber Volltextsuche gewünscht ist -> Detailseite abrufen
            if not is_match and search.get("search_in_description") and ad["url"]:
                detailed_desc, detailed_images, detailed_date = fetch_ad_details(ad["url"], DEFAULT_HEADERS)
                if detailed_desc:
                    full_description = detailed_desc
                if detailed_images:
                    all_images = detailed_images
                if detailed_date:
                    published_date = detailed_date
                is_match, reason = matches_keywords(
                    search_criteria=search,
                    title=ad["title"],
                    description=full_description,
                    ocr_text="",
                    matched_term=query_term
                )

            # 4. Falls immer noch kein Treffer, aber Foto-Texterkennung aktiv ist -> OCR ausführen
            if not is_match and search.get("ocr_images") and all_images:
                ocr_text = analyze_listing_images(all_images, max_images=3)
                is_match, reason = matches_keywords(
                    search_criteria=search,
                    title=ad["title"],
                    description=full_description,
                    ocr_text=ocr_text,
                    matched_term=query_term
                )

            if not is_match:
                continue

            ad_item = {
                "search_id": search["id"],
                "kleinanzeigen_id": str(adid),
                "title": ad["title"],
                "price": ad["price_text"],
                "price_num": ad["numeric_price"],
                "location": ad["location"],
                "shipping_possible": ad["shipping_possible"],
                "url": ad["url"],
                "thumbnail_url": ad["thumbnail"] or (all_images[0] if all_images else ""),
                "images": all_images,
                "description": full_description,
                "ocr_text": ocr_text,
                "match_reason": reason,
                "status": "new",
                "search_name": search.get("name"),
                "published_date": published_date
            }
            all_matched[adid] = ad_item

            # Sofort an Callback übergeben (Streaming in die Datenbank)
            if on_ad_found:
                try:
                    on_ad_found(ad_item)
                except Exception as e_cb:
                    logger.warning(f"Fehler in on_ad_found Callback: {e_cb}")

        if len(search_queries) > 1:
            time.sleep(random.uniform(0.6, 1.2))

    if on_progress:
        on_progress(100, f"Suchlauf abgeschlossen: {len(all_matched)} Treffer gefunden.", len(all_matched), len(all_matched))

    return list(all_matched.values())

