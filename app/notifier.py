import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- Telegram Notifier ---

def send_telegram_notification(bot_token: str, chat_id: str, item: Dict[str, Any]) -> bool:
    """Sendet eine formatierte Benachrichtigung an einen Telegram-Chat."""
    if not bot_token or not chat_id:
        return False

    title = item.get("title", "Neues Angebot")
    price = item.get("price", "K.A.")
    location = item.get("location", "Unbekannt")
    url = item.get("url", "")
    shipping = "📦 Versand möglich" if item.get("shipping_possible") else "📍 Nur Abholung"
    search_name = item.get("search_name", "Suchauftrag")
    match_reason = item.get("match_reason", "Suchbegriff passt")
    thumbnail = item.get("thumbnail_url")

    caption = (
        f"🎯 <b>Neuer KleinanzeigenRadar Treffer!</b>\n\n"
        f"<b>{title}</b>\n"
        f"💰 <b>Preis:</b> {price}\n"
        f"📍 <b>Ort / Versand:</b> {location} ({shipping})\n"
        f"🔍 <b>Suchauftrag:</b> {search_name}\n"
        f"💡 <b>Fundgrund:</b> {match_reason}\n\n"
        f"🔗 <a href='{url}'>Direkt zur Anzeige öffnen</a>"
    )

    try:
        if thumbnail and thumbnail.startswith("http"):
            # Versuche mit Foto zu senden
            photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            payload = {
                "chat_id": chat_id,
                "photo": thumbnail,
                "caption": caption,
                "parse_mode": "HTML"
            }
            res = requests.post(photo_url, data=payload, timeout=8)
            if res.status_code == 200:
                return True

        # Fallback auf normale Textnachricht
        msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        res = requests.post(msg_url, data=payload, timeout=8)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Fehler beim Senden der Telegram-Nachricht: {e}")
        return False

def test_telegram_connection(bot_token: str, chat_id: str) -> Dict[str, Any]:
    """Testet die Telegram-Verbindung mit einer Testnachricht."""
    if not bot_token or not chat_id:
        return {"success": False, "message": "Bot-Token oder Chat-ID fehlt."}

    text = (
        "🤖 <b>KleinanzeigenRadar Test</b>\n\n"
        "Die Verbindung zu Telegram funktioniert erfolgreich!\n"
        "Ab jetzt erhältst du hier Benachrichtigungen bei neuen Treffern."
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        res = requests.post(url, data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=8)
        data = res.json()
        if res.status_code == 200 and data.get("ok"):
            return {"success": True, "message": "Testnachricht erfolgreich an Telegram gesendet!"}
        else:
            return {"success": False, "message": f"Telegram-Fehler: {data.get('description', 'Unbekannt')}"}
    except Exception as e:
        return {"success": False, "message": f"Netzwerkfehler: {str(e)}"}


# --- E-Mail Notifier ---

def send_email_notification(smtp_settings: Dict[str, Any], item: Dict[str, Any]) -> bool:
    """Sendet eine formatierte HTML-E-Mail über SMTP."""
    host = smtp_settings.get("email_smtp_host")
    port = int(smtp_settings.get("email_smtp_port", 587))
    user = smtp_settings.get("email_smtp_user")
    password = smtp_settings.get("email_smtp_password")
    use_tls = smtp_settings.get("email_smtp_tls") in [1, "1", True, "true"]
    from_addr = smtp_settings.get("email_from") or user
    to_addr = smtp_settings.get("email_to")

    if not host or not to_addr:
        return False

    title = item.get("title", "Neues Angebot")
    price = item.get("price", "K.A.")
    location = item.get("location", "Unbekannt")
    url = item.get("url", "")
    shipping = "Versand möglich" if item.get("shipping_possible") else "Nur Abholung"
    search_name = item.get("search_name", "Suchauftrag")
    match_reason = item.get("match_reason", "")
    thumbnail = item.get("thumbnail_url", "")

    subject = f"[KleinanzeigenRadar] {title} ({price})"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7f7f5; margin: 0; padding: 20px; }}
        .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; }}
        .header {{ background: #86b817; color: #ffffff; padding: 18px 24px; font-size: 18px; font-weight: bold; }}
        .content {{ padding: 24px; color: #374151; }}
        .price {{ font-size: 22px; font-weight: bold; color: #111827; margin: 10px 0; }}
        .badge {{ display: inline-block; background: #f3f4f6; color: #4b5563; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; margin-bottom: 6px; }}
        .button {{ display: inline-block; background: #86b817; color: #ffffff !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 18px; }}
        .img {{ max-width: 100%; height: auto; border-radius: 8px; margin-top: 14px; border: 1px solid #e5e7eb; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">KleinanzeigenRadar Treffer</div>
        <div class="content">
          <span class="badge">🔍 {search_name}</span>
          <span class="badge">💡 {match_reason}</span>
          <h2 style="margin-top: 12px; margin-bottom: 6px; color: #111827;">{title}</h2>
          <div class="price">{price}</div>
          <p style="margin: 6px 0;">📍 <b>Standort:</b> {location} | <b>Versand:</b> {shipping}</p>
          {"<img class='img' src='" + thumbnail + "'>" if thumbnail else ""}
          <div style="text-align: center;">
            <a href="{url}" class="button">Auf Kleinanzeigen ansehen</a>
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Fehler beim Senden der E-Mail: {e}")
        return False

def test_email_connection(smtp_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Testet die E-Mail-Einstellungen mit einer Test-Mail."""
    host = smtp_settings.get("email_smtp_host")
    port = int(smtp_settings.get("email_smtp_port", 587))
    user = smtp_settings.get("email_smtp_user")
    password = smtp_settings.get("email_smtp_password")
    use_tls = smtp_settings.get("email_smtp_tls") in [1, "1", True, "true"]
    from_addr = smtp_settings.get("email_from") or user
    to_addr = smtp_settings.get("email_to")

    if not host or not to_addr:
        return {"success": False, "message": "SMTP-Server oder Empfänger-E-Mail fehlt."}

    test_item = {
        "title": "Verbindungstest erfolgreich",
        "price": "0,00 €",
        "location": "Lokal",
        "shipping_possible": True,
        "search_name": "Test-Suchauftrag",
        "match_reason": "Testübertragung",
        "url": "https://www.kleinanzeigen.de"
    }

    try:
        ok = send_email_notification(smtp_settings, test_item)
        if ok:
            return {"success": True, "message": f"Test-Mail erfolgreich an {to_addr} gesendet!"}
        else:
            return {"success": False, "message": "Senden fehlgeschlagen. Bitte Zugangsdaten und Port prüfen."}
    except Exception as e:
        return {"success": False, "message": f"SMTP-Fehler: {str(e)}"}
