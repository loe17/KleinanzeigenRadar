import io
import logging
import requests
from typing import List, Optional
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

# Prüfen ob pytesseract verfügbar ist
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract ist nicht installiert. Bildanalyse wird übersprungen.")

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Extrahiert lesbaren Text aus einem Bild (z.B. Typenschild, Modell, Rechnung)."""
    if not PYTESSERACT_AVAILABLE:
        return ""

    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Vorverarbeitung für bessere Erkennung
        # 1. In Graustufen umwandeln
        image = image.convert("L")
        # 2. Kontrast leicht anheben
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Versuche zuerst mit Deutsch & Englisch, sonst Fallback
        try:
            text = pytesseract.image_to_string(image, lang="deu+eng", timeout=8)
        except Exception:
            try:
                text = pytesseract.image_to_string(image, timeout=8)
            except Exception:
                text = ""

        # Bereinigen von überflüssigen Leerzeichen und Sonderzeichen
        cleaned_text = " ".join(text.split())
        return cleaned_text
    except Exception as e:
        logger.debug(f"OCR Fehler bei Bild: {e}")
        return ""

def analyze_listing_images(image_urls: List[str], max_images: int = 4) -> str:
    """Lädt die Bilder einer Anzeige herunter und führt Texterkennung durch."""
    if not PYTESSERACT_AVAILABLE or not image_urls:
        return ""

    combined_text = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    for url in image_urls[:max_images]:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                text = extract_text_from_image_bytes(resp.content)
                if text and len(text.strip()) > 3:
                    combined_text.append(text)
        except Exception as e:
            logger.debug(f"Konnte Bild nicht für OCR laden ({url}): {e}")
            continue

    return " | ".join(combined_text)
