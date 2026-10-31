import re
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("facebook_scraper")

DEFAULT_FB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

def parse_fb_price(price_str: str) -> Optional[float]:
    """Wandelt einen Facebook-Preis wie '120 €', 'Kostenlos' oder '€ 1.250' um."""
    if not price_str:
        return None
    cleaned = price_str.lower().strip()
    if "kostenlos" in cleaned or "gratis" in cleaned or "zu verschenken" in cleaned:
        return 0.0
    match = re.search(r"(\d+(?:[.]\d+)*(?:,\d+)?)", cleaned)
    if match:
        num_str = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return None
    return None

def build_fb_search_url(
    query: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    location_slug: str = ""
) -> str:
    """Baut eine Facebook Marketplace Such-URL."""
    loc = location_slug.strip() or "category"
    base = f"https://www.facebook.com/marketplace/{loc}/search"
    params = []
    if query:
        from urllib.parse import quote
        params.append(f"query={quote(query.strip())}")
    if min_price is not None:
        params.append(f"minPrice={int(min_price)}")
    if max_price is not None:
        params.append(f"maxPrice={int(max_price)}")

    if params:
        return f"{base}?{'&'.join(params)}"
    return base

def scrape_facebook_marketplace(
    query: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    postal_code: str = "",
    session_cookie: str = "",
    max_items: int = 30
) -> List[Dict[str, Any]]:
    """
    Sucht auf Facebook Marketplace nach Inseraten.
    Unterstützt optional hinterlegte Session-Cookies zur Authentifizierung.
    """
    if not query.strip():
        return []

    url = build_fb_search_url(query=query, min_price=min_price, max_price=max_price)
    headers = dict(DEFAULT_FB_HEADERS)
    if session_cookie and session_cookie.strip():
        headers["Cookie"] = session_cookie.strip()

    logger.info(f"Facebook Marketplace Anfrage: {url}")
    items: List[Dict[str, Any]] = []

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            logger.warning(f"Facebook antwortete mit Statuscode {resp.status_code}")
            return []

        html = resp.text
        seen_ids = set()

        matches = re.findall(r'/marketplace/item/(\d+)/', html)
        for item_id in matches:
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            if len(seen_ids) >= max_items:
                break

        soup = BeautifulSoup(html, "html.parser")
        
        scripts = soup.find_all("script", type="application/json")
        for s in scripts:
            if not s.string or "marketplace_listing" not in s.string.lower():
                continue
            try:
                data = json.loads(s.string)
                _extract_fb_listings_from_json(data, items, seen_ids, max_items)
            except Exception:
                continue

        if items:
            logger.info(f"Facebook Marketplace: {len(items)} Inserate aus JSON-Daten extrahiert.")
            return items

        feed_elements = soup.find_all("a", href=re.compile(r'/marketplace/item/\d+'))
        for a_elem in feed_elements:
            href = a_elem.get("href", "")
            m_id = re.search(r'/marketplace/item/(\d+)', href)
            if not m_id:
                continue
            fbid = m_id.group(1)
            if fbid in seen_ids:
                continue
            seen_ids.add(fbid)

            text_content = a_elem.get_text(separator=" ", strip=True)
            price_match = re.search(r'([\d.,]+\s*€|€\s*[\d.,]+|Kostenlos)', text_content, re.IGNORECASE)
            price_text = price_match.group(0).strip() if price_match else "VB"
            num_price = parse_fb_price(price_text)

            img_tag = a_elem.find("img")
            img_src = img_tag.get("src") if img_tag else ""

            clean_title = text_content
            if price_match:
                clean_title = clean_title.replace(price_match.group(0), "").strip()

            full_url = f"https://www.facebook.com/marketplace/item/{fbid}/"
            items.append({
                "adid": f"fb_{fbid}",
                "title": clean_title[:90] if clean_title else f"Facebook Angebot {fbid}",
                "price_text": price_text,
                "numeric_price": num_price,
                "shipping_possible": True,
                "location": postal_code or "Facebook Marketplace",
                "thumbnail": img_src,
                "url": full_url,
                "description": clean_title,
                "published_date": "Facebook Marketplace",
                "platform": "facebook"
            })
            if len(items) >= max_items:
                break

        logger.info(f"Facebook Marketplace: {len(items)} Inserate gefunden.")
        return items

    except Exception as e:
        logger.warning(f"Fehler beim Abruf von Facebook Marketplace: {e}")
        return []

def _extract_fb_listings_from_json(obj: Any, results: List[Dict[str, Any]], seen_ids: set, max_items: int):
    """Rekursive Hilfsfunktion zur Extraktion von Marketplace-Daten aus verschachtelten JSON-Objekten."""
    if len(results) >= max_items:
        return

    if isinstance(obj, dict):
        if "marketplace_listing_title" in obj or ("listing_price" in obj and "id" in obj):
            fbid = str(obj.get("id") or obj.get("listing_id") or "")
            if fbid and fbid not in seen_ids:
                seen_ids.add(fbid)
                title = obj.get("marketplace_listing_title") or obj.get("title") or "Angebot auf Facebook"
                price_obj = obj.get("listing_price") or {}
                price_formatted = price_obj.get("formatted_amount") or obj.get("formatted_price") or "VB"
                num_price = parse_fb_price(price_formatted)
                img_url = ""
                img_obj = obj.get("primary_listing_photo") or obj.get("image") or {}
                if isinstance(img_obj, dict):
                    img_url = img_obj.get("image", {}).get("uri") or img_obj.get("uri") or ""

                loc_name = ""
                loc_obj = obj.get("location") or {}
                if isinstance(loc_obj, dict):
                    loc_name = loc_obj.get("reverse_geocode", {}).get("city") or loc_obj.get("name") or ""

                results.append({
                    "adid": f"fb_{fbid}",
                    "title": title,
                    "price_text": price_formatted,
                    "numeric_price": num_price,
                    "shipping_possible": True,
                    "location": loc_name or "Facebook Marketplace",
                    "thumbnail": img_url,
                    "url": f"https://www.facebook.com/marketplace/item/{fbid}/",
                    "description": obj.get("redacted_description", {}).get("text") or title,
                    "published_date": "Facebook Marketplace",
                    "platform": "facebook"
                })
        for v in obj.values():
            _extract_fb_listings_from_json(v, results, seen_ids, max_items)
    elif isinstance(obj, list):
        for item in obj:
            _extract_fb_listings_from_json(item, results, seen_ids, max_items)
