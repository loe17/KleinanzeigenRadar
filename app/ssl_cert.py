import os
import shutil
import socket
import logging
import subprocess
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

CERTS_DIR = Path(__file__).resolve().parent.parent / "data" / "certs"
CERT_FILE = CERTS_DIR / "cert.pem"
KEY_FILE = CERTS_DIR / "key.pem"

def get_lan_ip() -> str:
    """Ermittelt die primaere lokale IP-Adresse im Heimnetz."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Verbinungsversuch zu einem oeffentlichen DNS, ohne Daten zu senden
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def ensure_ssl_certificates(domain: str = "kleinanzeigenradar.local") -> Tuple[Optional[str], Optional[str]]:
    """
    Stellt sicher, dass ein gueltiges SSL-Zertifikat fuer kleinanzeigenradar.local,
    localhost und die lokale LAN-IP vorliegt. Falls nicht vorhanden, wird es automatisch generiert.
    """
    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    if CERT_FILE.exists() and KEY_FILE.exists():
        logger.info(f"SSL-Zertifikate gefunden in {CERTS_DIR}")
        return str(CERT_FILE), str(KEY_FILE)

    lan_ip = get_lan_ip()
    logger.info(f"Erzeuge automatisches SSL-Zertifikat fuer {domain}, localhost, 127.0.0.1 und {lan_ip}...")

    # Pruefe ob openssl verfuegbar ist
    openssl_bin = shutil.which("openssl")
    if not openssl_bin:
        logger.warning("openssl Befehl nicht gefunden. SSL kann nicht automatisch generiert werden.")
        return None, None

    san_config = f"subjectAltName=DNS:{domain},DNS:localhost,IP:127.0.0.1,IP:{lan_ip}"

    cmd = [
        openssl_bin, "req", "-x509",
        "-newkey", "rsa:2048",
        "-keyout", str(KEY_FILE),
        "-out", str(CERT_FILE),
        "-sha256",
        "-days", "3650",
        "-nodes",
        "-subj", f"/CN={domain}",
        "-addext", san_config
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0 and CERT_FILE.exists() and KEY_FILE.exists():
            logger.info("SSL-Zertifikat erfolgreich erzeugt!")
            return str(CERT_FILE), str(KEY_FILE)
        else:
            # Fallback fuer aeltere openssl Versionen ohne -addext
            logger.info("Versuche alternatives openssl Format ohne -addext...")
            cmd_alt = [
                openssl_bin, "req", "-x509",
                "-newkey", "rsa:2048",
                "-keyout", str(KEY_FILE),
                "-out", str(CERT_FILE),
                "-sha256",
                "-days", "3650",
                "-nodes",
                "-subj", f"/CN={domain}"
            ]
            proc_alt = subprocess.run(cmd_alt, capture_output=True, text=True, timeout=15)
            if proc_alt.returncode == 0:
                logger.info("SSL-Zertifikat erfolgreich erzeugt (Basis-Modus)!")
                return str(CERT_FILE), str(KEY_FILE)
            else:
                logger.error(f"openssl Fehler: {proc.stderr} {proc_alt.stderr}")
                return None, None
    except Exception as e:
        logger.error(f"Fehler bei Erzeugung des SSL-Zertifikats: {e}")
        return None, None
