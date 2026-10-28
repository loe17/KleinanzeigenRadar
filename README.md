# KleinanzeigenRadar

<p align="center">
  <img src="docs/images/logo.jpg" width="140" height="140" alt="KleinanzeigenRadar Logo" style="border-radius: 20px;">
</p>

<p align="center">
  <b>Dein persönlicher, unermüdlicher Wächter für Kleinanzeigen</b><br>
  Läuft rund um die Uhr leise auf deinem Linux-System oder im Docker-Container – sowohl auf Standard-PCs (x86) als auch auf sparsamen Geräten wie dem Raspberry Pi (ARM).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.1.5-86b817.svg" alt="Version 0.1.5">
  <img src="https://img.shields.io/badge/Domain-kleinanzeigenradar.local-purple.svg" alt="Local Domain">
  <img src="https://img.shields.io/badge/Sicherheit-HTTPS%20%7C%20SSL-green.svg" alt="HTTPS">
  <img src="https://img.shields.io/badge/Plattform-Linux%20%7C%20Docker-blue.svg" alt="Linux & Docker">
  <img src="https://img.shields.io/badge/Sprachen-Deutsch%20%7C%20English-darkgreen.svg" alt="Languages">
</p>

---

## 1-Befehl-Installation (Empfohlen)

Kopiere diesen **einzigen Befehl** in das Terminal deines Linux-Servers oder Raspberry Pis. Das Skript prüft alle Voraussetzungen, installiert fehlende Werkzeuge (inklusive Docker & Compose, falls noch nicht vorhanden) vollautomatisch, sucht selbstständig freie Ports und richtet die lokale Domain sowie HTTPS ein:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/loe17/KleinanzeigenRadar/main/install.sh || wget -qO- https://raw.githubusercontent.com/loe17/KleinanzeigenRadar/main/install.sh)"
```

*Alternativ über Git-Klon:*
```bash
git clone https://github.com/loe17/KleinanzeigenRadar.git && cd KleinanzeigenRadar && ./install.sh
```

Nach der Installation ist KleinanzeigenRadar sofort über dein lokales Netzwerk erreichbar:
* **HTTPS:** `https://kleinanzeigenradar.local:8443` (oder `https://deine-server-ip:8443`)
* **HTTP:** `http://kleinanzeigenradar.local:8000` (oder `http://deine-server-ip:8000`)

---

## Einblicke in die Anwendung

### Das Dashboard
Schlicht, fokussiert und ohne Ablenkung mit gestochen scharfen SVG-Grafiken und zweisprachiger Benutzeroberfläche (Deutsch & Englisch). Alle Treffer laufen zentral ein und lassen sich blitzschnell nach Status, Versandart oder Preisspanne filtern:

<p align="center">
  <img src="docs/images/dashboard_preview.jpg" width="100%" alt="KleinanzeigenRadar Dashboard Vorschau" style="border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);">
</p>

---

### Blitzschnelle Benachrichtigungen auf dein Smartphone
Sobald ein passendes Angebot online geht, erhältst du sofort eine Benachrichtigung auf dein Smartphone via **Telegram** (mit Bild, Preis und Klick-Link) oder per **E-Mail**:

<p align="center">
  <img src="docs/images/telegram_preview.jpg" width="340" alt="Telegram Benachrichtigung Vorschau" style="border-radius: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.15);">
</p>

---

## Was kann KleinanzeigenRadar für dich tun?

Normale Suchen auf Kleinanzeigen sind oft ungenau oder verpassen Schnäppchen, weil Verkäufer wichtige Details im Text vergessen oder Tippfehler machen. **KleinanzeigenRadar** findet diese Angebote trotzdem:

* **Lokale Domain & HTTPS:** Direkt im Heimnetzwerk unter `https://kleinanzeigenradar.local` mit automatisch generiertem SSL-Zertifikat erreichbar.
* **Automatische Port-Erkennung:** Sollte ein Standardport (z. B. 8000 oder 8443) bereits durch andere Dienste belegt sein, sucht das System vollautomatisch den nächsten freien Port.
* **Live-Treffer Vorschau beim Eintippen:** Während du Suchbegriffe, Preisbereiche oder Postleitzahlen eingibst, ermittelt das System in Sekundenschnelle die aktuelle Trefferanzahl direkt bei Kleinanzeigen und zeigt sie live an.
* **Flexible Such- & Ausschlussbegriffe:** Kein starrer Hauptbegriff mehr. Du kannst beliebig viele Begriffe (z. B. `Dell Latitude`, `Lenovo T480`) hinterlegen und jeweils frei bestimmen, ob sie als aktiver Suchbegriff (grün) oder als Ausschlussbegriff (rot, z. B. `defekt`, `Bastler`) dienen.
* **Datums- & Zeitangaben:** Jeder Suchauftrag zeigt transparent und minutengenau an, wann er angelegt wurde (*Erstellt am*) und wann der Wächter zuletzt nach neuen Inseraten geschaut hat (*Zuletzt geprüft*).
* **Zweisprachig (DE / EN):** Vollständig auf Deutsch und Englisch nutzbar – die Sprache lässt sich sauber im Menü „Einstellungen & Updates“ auswählen.
* **Die Bild-Lupe (Foto-Texterkennung):** Viele Verkäufer schreiben kaum Text, stellen aber Fotos von Typenschildern, Seriennummern, Verpackungen oder Kassenbons ein. KleinanzeigenRadar liest Schriftzüge auf Fotos automatisch mit!
* **Versand & Entfernung:** Bestimme pro Suche, ob du nur Angebote mit Versand suchst, nur Selbstabholung in deiner Nähe (z. B. 20 km um deine PLZ) oder beides.
* **Preisspanne:** Setze flexibel Mindest- und Höchstpreise fest.
* **Sofort-Meldung via Telegram & E-Mail:** Kein ständiges manuelles Nachschauen mehr – dein Handy meldet sich sofort, wenn etwas Passendes eingestellt wird.
* **SVG-Grafiken statt Emojis:** Alle Oberflächenelemente basieren auf sauberen, hochauflösenden Vektorgrafiken.
* **Automatischer 1-Klick-Aktualisierer mit Ladebalken & Neustart:** Prüft auf Knopfdruck über GitHub auf neue Versionen, lädt Aktualisierungen mit animiertem Ladebalken herunter und startet den Hintergrunddienst bzw. Docker-Container vollautomatisch neu.

---

## Telegram & E-Mail einrichten

1. Klicke in der Web-Oberfläche unten links auf **„Einstellungen & Updates“**.
2. **Telegram:**
   * Gib deinen **Bot-Token** (vom Telegram `@BotFather`) und deine **Chat-ID** ein.
   * Klicke auf **„Telegram-Testnachricht senden“**, um die Verbindung sofort zu testen.
3. **E-Mail:**
   * Trage deine E-Mail-Zugangsdaten (SMTP-Server, Port, Benutzername, Passwort) ein.
   * Klicke auf **„Test-E-Mail senden“**.
4. Klicke auf **„Einstellungen speichern“**. Fertig!

---

## Updates über GitHub

* In der Web-Oberfläche unter **„Einstellungen & Updates“** kannst du jederzeit auf **„Auf Updates prüfen“** klicken.
* Mit Klick auf **„Jetzt aktualisieren“** zeigt KleinanzeigenRadar einen animierten Fortschrittsbalken, lädt die neuesten Daten von GitHub, führt den automatischen Dienst-Neustart durch und lädt das Dashboard im Browser neu, sobald der Server wieder erreichbar ist.

---

## Deinstallation

Möchtest du die Anwendung irgendwann entfernen, genügt ein einziger Befehl im Projektordner:

```bash
./uninstall.sh
```

Das Skript stoppt alle Dienste oder Container sauber und fragt dich, ob deine bisherigen Suchaufträge und Treffer (`data/`) aufbewahrt oder gelöscht werden sollen.

---

## Ordner-Struktur

```text
KleinanzeigenRadar/
├── app/
│   ├── config.py           # Konfiguration, Pfade & Version 0.1.5
│   ├── database.py         # Schnelle SQLite-Datenbank für Suchen & Treffer
│   ├── network_utils.py    # Automatische Suche nach freien Ports & IPs
│   ├── ssl_cert.py         # Automatische SSL-Zertifikatsgenerierung (HTTPS)
│   ├── scraper.py          # Schonendes Kleinanzeigen-Scraping & Wortfilter
│   ├── ocr.py              # Foto-Texterkennung (Bild-Lupe)
│   ├── notifier.py         # Telegram- & E-Mail-Benachrichtigungen
│   ├── updater.py          # GitHub-Versionsprüfung, Ladebalken & Auto-Restart
│   ├── watcher.py          # Zuverlässiger Hintergrund-Wächter
│   ├── static/             # CSS, JavaScript, i18n & SVG-Icons
│   └── templates/          # Haupt-HTML-Oberfläche
├── data/                   # Gespeicherte Suchen, Treffer & SSL-Zertifikate
├── docs/images/            # Vorschaubilder für die Dokumentation
├── Dockerfile              # Multi-Architektur-Bauplan (x86 & ARM) mit OpenSSL
├── docker-compose.yml      # 1-Klick Startdatei mit HTTP & HTTPS Ports
├── install.sh              # Automatisches Prüf-, Installations- & Port-Skript
├── uninstall.sh            # Automatisches Deinstallationsskript
├── requirements.txt        # Python-Bibliotheken
├── run.py                  # Dual-Server Einstiegspunkt (HTTP & HTTPS)
└── README.md               # Diese Anleitung
```

---

<p align="center">
  Entwickelt für eine entspannte, automatische Schnäppchenjagd auf Kleinanzeigen.
</p>
