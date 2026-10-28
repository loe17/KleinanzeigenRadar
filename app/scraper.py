import re
import time
import random
import logging
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from app.config import DEFAULT_USER_AGENT
from app.ocr import analyze_listing_images

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleinanzeigen.de"

def build_search_url(search: Dict[str, Any]) -> str:
    """Baut eine saubere Kleinanzeigen Such-URL basierend auf den Kriterien."""
    query = search.get("query", "").strip()
    plz = search.get("postal_code", "").strip()
    radius = search.get("radius") or 0
    min_price = search.get("min_price")
    max_price = search.get("max_price")

    # URL-Parameter zusammenbauen
    params = {}
    if query:
        params["keywords"] = query
    if plz:
        params["locationStr"] = plz
        if radius and int(radius) > 0:
            params["radius"] = str(radius)
    if min_price is not None and min_price != "":
        params["minPrice"] = str(min_price)
    if max_price is not None and max_price != "":
        params["maxPrice"] = str(max_price)

    # Sortierung: Immer die neuesten zuerst ("Neueste Anzeigen")
    params["sortingField"] = "SORTING_DATE"

    query_string = urllib.parse.urlencode(params)
    return f"{BASE_URL}/s-suchanfrage.html?{query_string}"

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

def fetch_ad_details(ad_url: str, headers: Dict[str, str]) -> Tuple[str, List[str]]:
    """Ruft die Detailseite einer Anzeige ab für vollständige Beschreibung und hochauflösende Bilder."""
    try:
        time.sleep(random.uniform(0.6, 1.4))  # Schonende Pause
        resp = requests.get(ad_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return "", []

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

        return full_description, image_urls
    except Exception as e:
        logger.warning(f"Fehler beim Laden der Detailseite {ad_url}: {e}")
        return "", []

def matches_keywords(
    search_criteria: Dict[str, Any],
    title: str,
    description: str,
    ocr_text: str
) -> Tuple[bool, str]:
    """Prüft, ob Suchbegriffe und Ausschlusskriterien erfüllt sind."""
    raw_keywords = search_criteria.get("keywords", "") or ""
    case_sensitive = bool(search_criteria.get("case_sensitive", False))
    search_in_desc = bool(search_criteria.get("search_in_description", True))

    # Textblöcke zusammenstellen
    title_check = title if case_sensitive else title.lower()
    desc_check = (description if case_sensitive else description.lower()) if search_in_desc else ""
    ocr_check = ocr_text if case_sensitive else ocr_text.lower()

    # Zeilen- oder Komma-getrennte Suchbegriffe extrahieren
    lines = [kw.strip() for kw in re.split(r"[,\n]+", raw_keywords) if kw.strip()]

    # Wenn keine spezifischen Keywords definiert wurden, gilt das Inserat als Treffer (wurde ja schon via Hauptsuche gefunden)
    if not lines:
        return True, "Treffer durch Hauptsuchbegriff"

    match_locations = []

    for kw in lines:
        is_negative = kw.startswith("-") or kw.startswith("!")
        word = kw[1:].strip() if is_negative else kw
        if not word:
            continue

        target_word = word if case_sensitive else word.lower()

        in_title = target_word in title_check
        in_desc = target_word in desc_check if search_in_desc else False
        in_ocr = target_word in ocr_check

        found = in_title or in_desc or in_ocr

        # Ausschlusskriterium (z.B. -defekt): Wenn gefunden, sofort aussortieren!
        if is_negative and found:
            return False, f"Ausgeschlossen durch Kriterium: '{word}'"

        # Positives Kriterium: Muss vorkommen
        if not is_negative:
            if not found:
                return False, f"Fehlendes Kriterium: '{word}'"
            
            # Dokumentieren, wo das Wort gefunden wurde
            if in_title:
                match_locations.append(f"Titel ('{word}')")
            elif in_ocr:
                match_locations.append(f"Bild-Text ('{word}')")
            elif in_desc:
                match_locations.append(f"Beschreibung ('{word}')")

    location_str = ", ".join(dict.fromkeys(match_locations))
    return True, f"Treffer in: {location_str}" if location_str else "Treffer durch Kriterien"

def scrape_search(search: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Führt eine Suche auf Kleinanzeigen durch und gibt passende Inserate zurück."""
    url = build_search_url(search)
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": BASE_URL
    }

    logger.info(f"Starte Suche '{search.get('name')}' unter URL: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            logger.warning(f"Kleinanzeigen antwortete mit Status {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"Fehler bei Anfrage an Kleinanzeigen: {e}")
        return []

    # Artikel extrahieren (Kleinanzeigen Struktur: <article class="aditem" ...>)
    ad_items = soup.find_all("article", class_="aditem")
    if not ad_items:
        # Fallback falls andere Klassen verwendet werden
        ad_items = soup.find_all("li", class_="ad-listitem")

    matched_results = []

    for item in ad_items:
        try:
            adid = item.get("data-adid")
            if not adid:
                # Versuche ID aus Link zu lesen
                link_elem = item.find("a", href=re.compile(r"/s-anzeige/"))
                if link_elem:
                    match_id = re.search(r"/(\d+)-", link_elem.get("href", ""))
                    adid = match_id.group(1) if match_id else None

            if not adid:
                continue

            # Titel und Link
            title_elem = item.find("h2") or item.find("a", class_="ellipsis")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            
            link = title_elem.find("a") if title_elem.name != "a" else title_elem
            rel_url = link.get("href", "") if link else ""
            full_url = BASE_URL + rel_url if rel_url.startswith("/") else rel_url

            # Preis
            price_elem = item.select_one(".aditem-main--middle--price-shipping--price")
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            numeric_price = parse_price(price_text)

            # Preis-Filterprüfung
            min_p = search.get("min_price")
            max_p = search.get("max_price")
            if numeric_price is not None:
                if min_p is not None and numeric_price < float(min_p):
                    continue
                if max_p is not None and numeric_price > float(max_p):
                    continue

            # Versand-Prüfung
            shipping_elem = item.select_one(".aditem-main--middle--price-shipping--shipping")
            shipping_text = shipping_elem.get_text(strip=True) if shipping_elem else ""
            shipping_possible = "versand" in shipping_text.lower()

            shipping_pref = search.get("shipping_type", "all")
            if shipping_pref == "shipping_only" and not shipping_possible:
                continue
            if shipping_pref == "pickup_only" and shipping_possible:
                continue

            # Standort & Entfernung
            loc_elem = item.select_one(".aditem-main--top--left")
            location_str = loc_elem.get_text(separator=" ", strip=True) if loc_elem else ""

            # Vorschaubild
            img_elem = item.select_one(".imagebox img")
            thumbnail = ""
            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src") or ""

            # Vorschau-Beschreibung
            desc_elem = item.select_one(".aditem-main--middle--description")
            short_desc = desc_elem.get_text(strip=True) if desc_elem else ""

            # Detailseite laden (falls Beschreibung oder OCR aktiviert ist)
            full_description = short_desc
            all_images = [thumbnail] if thumbnail else []
            ocr_text = ""

            need_details = search.get("search_in_description") or search.get("ocr_images")
            if need_details and full_url:
                detailed_desc, detailed_images = fetch_ad_details(full_url, headers)
                if detailed_desc:
                    full_description = detailed_desc
                if detailed_images:
                    all_images = detailed_images

            # OCR / Bildanalyse durchführen falls gewünscht
            if search.get("ocr_images") and all_images:
                ocr_text = analyze_listing_images(all_images, max_images=3)

            # Suchkriterien prüfen
            is_match, reason = matches_keywords(
                search_criteria=search,
                title=title,
                description=full_description,
                ocr_text=ocr_text
            )

            if not is_match:
                continue

            matched_results.append({
                "search_id": search["id"],
                "kleinanzeigen_id": str(adid),
                "title": title,
                "price": price_text,
                "price_num": numeric_price,
                "location": location_str,
                "shipping_possible": shipping_possible,
                "url": full_url,
                "thumbnail_url": thumbnail or (all_images[0] if all_images else ""),
                "images": all_images,
                "description": full_description,
                "ocr_text": ocr_text,
                "match_reason": reason,
                "status": "new",
                "search_name": search.get("name")
            })

        except Exception as e:
            logger.warning(f"Fehler beim Verarbeiten eines Kleinanzeigen-Elements: {e}")
            continue

    return matched_results
