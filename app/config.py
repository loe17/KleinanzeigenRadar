import os
from pathlib import Path

# Basis-Pfade
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = DATA_DIR / "radar.db"

# Versions-Information
VERSION = "0.1.2"
APP_NAME = "KleinanzeigenRadar"
GITHUB_REPO = "loe17/KleinanzeigenRadar"  # Standard-Repository auf GitHub

# Standard-Einstellungen
DEFAULT_PORT = int(os.environ.get("PORT", 8000))
DEFAULT_HOST = os.environ.get("HOST", "0.0.0.0")

# HTTP Header für unauffälliges & schonendes Scraping
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
