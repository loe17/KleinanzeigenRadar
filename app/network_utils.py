import socket
import logging
from typing import List

logger = logging.getLogger(__name__)

def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Prueft, ob ein Port bereits belegt ist."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except OSError:
            return True

def find_available_port(preferred_port: int, max_attempts: int = 50, host: str = "0.0.0.0") -> int:
    """
    Sucht ab dem bevorzugten Port automatisch nach dem naechsten freien Port.
    """
    for candidate in range(preferred_port, preferred_port + max_attempts):
        if not is_port_in_use(candidate, host):
            if candidate != preferred_port:
                logger.warning(f"Port {preferred_port} ist belegt. Weiche automatisch auf freien Port {candidate} aus.")
            return candidate
    
    logger.error(f"Konnte im Bereich {preferred_port}-{preferred_port + max_attempts} keinen freien Port finden.")
    return preferred_port

def get_network_ips() -> List[str]:
    """Ermittelt alle verfuegbaren lokalen IP-Adressen."""
    ips = ["127.0.0.1"]
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and ip not in ips:  # Nur IPv4
                ips.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary not in ips:
            ips.insert(0, primary)
    except Exception:
        pass

    return ips
