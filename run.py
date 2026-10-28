import os
import time
import logging
import threading
import uvicorn
from app.config import DEFAULT_HOST, DEFAULT_PORT
from app.network_utils import find_available_port, get_network_ips
from app.ssl_cert import ensure_ssl_certificates

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run")

def main():
    host = os.environ.get("HOST", DEFAULT_HOST)
    preferred_http_port = int(os.environ.get("PORT", DEFAULT_PORT))
    preferred_ssl_port = int(os.environ.get("SSL_PORT", 8443))
    enable_https = os.environ.get("ENABLE_HTTPS", "true").lower() in ["1", "true", "yes"]

    # Automatische Suche nach freien Ports
    http_port = find_available_port(preferred_http_port, host=host)

    # SSL-Zertifikate vorbereiten
    cert_file, key_file = None, None
    ssl_port = None
    if enable_https:
        cert_file, key_file = ensure_ssl_certificates("kleinanzeigenradar.local")
        if cert_file and key_file:
            ssl_port = find_available_port(preferred_ssl_port, host=host)
            # Sicherstellen, dass ssl_port nicht identisch mit http_port ist
            if ssl_port == http_port:
                ssl_port = find_available_port(http_port + 1, host=host)

    # Netzwerk-IPs fuer freundliche Terminal-Ausgabe
    ips = get_network_ips()
    primary_ip = ips[0] if ips else "127.0.0.1"

    print("\n" + "=" * 60)
    print("           KleinanzeigenRadar Server gestartet            ")
    print("=" * 60)
    print(f"  HTTP:   http://kleinanzeigenradar.local:{http_port}")
    print(f"          http://{primary_ip}:{http_port}")
    if ssl_port and cert_file:
        print(f"  HTTPS:  https://kleinanzeigenradar.local:{ssl_port}")
        print(f"          https://{primary_ip}:{ssl_port}")
    print("=" * 60 + "\n")

    # Falls HTTPS aktiv ist, starten wir HTTPS im Hintergrund und HTTP im Haupt-Thread
    if ssl_port and cert_file and key_file:
        def start_https():
            time.sleep(0.5)
            try:
                uvicorn.run(
                    "app.main:app",
                    host=host,
                    port=ssl_port,
                    ssl_certfile=cert_file,
                    ssl_keyfile=key_file,
                    log_level="info",
                    lifespan="off"
                )
            except Exception as e:
                logger.error(f"Fehler im HTTPS Server: {e}")

        https_thread = threading.Thread(target=start_https, daemon=True)
        https_thread.start()

    # HTTP Server im Haupt-Thread
    uvicorn.run("app.main:app", host=host, port=http_port, log_level="info")

if __name__ == "__main__":
    main()
