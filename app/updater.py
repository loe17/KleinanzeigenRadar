import os
import subprocess
import logging
import threading
import time
import requests
from typing import Dict, Any
from app.config import VERSION, BASE_DIR
from app.database import get_settings

logger = logging.getLogger(__name__)

def schedule_restart(delay_seconds: float = 1.5):
    """Startet den Prozess nach kurzer Verzögerung neu (über Systemd oder Docker)."""
    def _restart():
        time.sleep(delay_seconds)
        logger.info("Führe automatischen Neustart nach Update durch...")
        os._exit(0)

    t = threading.Thread(target=_restart, daemon=True)
    t.start()

def check_for_github_update() -> Dict[str, Any]:
    """Prüft über die GitHub API, ob eine neuere Version verfügbar ist."""
    settings = get_settings()
    repo = settings.get("github_repo", "loe17/KleinanzeigenRadar").strip()
    
    result = {
        "current_version": VERSION,
        "latest_version": VERSION,
        "update_available": False,
        "release_notes": "",
        "repo": repo,
        "error": None
    }

    if not repo:
        result["error"] = "Kein GitHub-Repository konfiguriert."
        return result

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "KleinanzeigenRadar-Updater"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            tag_name = data.get("tag_name", "").lstrip("v")
            body = data.get("body", "Keine Versionshinweise vorhanden.")
            result["latest_version"] = tag_name
            result["release_notes"] = body

            # Versionsvergleich (einfacher String-/Tupelvergleich)
            def parse_ver(v_str):
                try:
                    return tuple(map(int, v_str.lstrip("v").split(".")))
                except:
                    return (0, 0, 0)

            if parse_ver(tag_name) > parse_ver(VERSION):
                result["update_available"] = True
        elif resp.status_code == 404:
            # Fallback: Falls keine Releases angelegt sind, prüfe letzten Commit auf GitHub
            commit_url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
            c_resp = requests.get(commit_url, headers=headers, timeout=8)
            if c_resp.status_code == 200:
                commits = c_resp.json()
                if commits and len(commits) > 0:
                    latest_commit = commits[0]
                    short_sha = latest_commit.get("sha", "")[:7]
                    commit_msg = latest_commit.get("commit", {}).get("message", "")
                    result["latest_version"] = f"commit-{short_sha}"
                    result["release_notes"] = commit_msg
            else:
                result["error"] = f"Repository '{repo}' wurde auf GitHub nicht gefunden."
        else:
            result["error"] = f"GitHub API antwortete mit Status {resp.status_code}"
    except Exception as e:
        result["error"] = f"Netzwerkfehler beim Update-Check: {str(e)}"

    return result

def perform_update() -> Dict[str, Any]:
    """Führt ein Update durch (per git pull) und startet den Dienst automatisch neu."""
    git_dir = BASE_DIR / ".git"
    
    if not git_dir.exists():
        return {
            "success": False,
            "message": "Dieses System wurde nicht direkt über 'git clone' installiert. Bitte install.sh erneut ausführen oder Docker-Container neu ziehen."
        }

    try:
        # Führe git pull im Projektverzeichnis aus
        proc = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.returncode != 0:
            # Fallback falls ff-only meckert
            proc = subprocess.run(
                ["git", "pull"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=30
            )

        if proc.returncode == 0:
            output = proc.stdout.strip()
            # Falls requirements vorhanden sind und venv existiert, Abhängigkeiten aktualisieren
            pip_path = BASE_DIR / "venv" / "bin" / "pip"
            if pip_path.exists():
                try:
                    subprocess.run(
                        [str(pip_path), "install", "-r", "requirements.txt"],
                        cwd=str(BASE_DIR),
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                except Exception as pip_err:
                    logger.warning("pip install nach Update fehlgeschlagen: %s", pip_err)

            # Automatischen Neustart nach 1.5 Sekunden auslösen
            schedule_restart(1.5)

            return {
                "success": True,
                "restarting": True,
                "message": f"Update erfolgreich: {output}. Dienst startet jetzt automatisch neu.",
                "output": output
            }
        else:
            return {
                "success": False,
                "message": f"Git Pull fehlgeschlagen: {proc.stderr.strip()}"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Fehler bei Aktualisierung: {str(e)}"
        }
