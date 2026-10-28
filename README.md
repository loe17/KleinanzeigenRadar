# KleinanzeigenRadar

<p align="center">
  <img src="docs/images/logo.jpg" width="140" height="140" alt="KleinanzeigenRadar Logo" style="border-radius: 20px;">
</p>

<p align="center">
  <b>Dein persönlicher, unermüdlicher Wächter für Kleinanzeigen</b><br>
  Läuft rund um die Uhr leise auf deinem Linux-System oder im Docker-Container – sowohl auf Standard-PCs (x86) als auch auf sparsamen Geräten wie dem Raspberry Pi (ARM).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.1.2-86b817.svg" alt="Version 0.1.2">
  <img src="https://img.shields.io/badge/Plattform-Linux%20%7C%20Docker-blue.svg" alt="Linux & Docker">
  <img src="https://img.shields.io/badge/Architektur-x86__64%20%7C%20ARM64%20%7C%20ARMv7-orange.svg" alt="x86 & ARM">
  <img src="https://img.shields.io/badge/Sprachen-Deutsch%20%7C%20English-darkgreen.svg" alt="Languages">
  <img src="https://img.shields.io/badge/Telegram-Benachrichtigung-0088cc.svg" alt="Telegram Support">
</p>

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

* **Zweisprachig (DE / EN):** Vollständig auf Deutsch und Englisch nutzbar – Standard ist Deutsch, per Klick sofort umschaltbar.
* **Gezielte Suchaufträge:** Lege beliebig viele Suchen an. Du entscheidest, ob exakt auf Groß-/Kleinschreibung geachtet werden soll und ob die gesamte Artikelbeschreibung durchsucht wird.
* **Die Bild-Lupe (Foto-Texterkennung):** Viele Verkäufer schreiben kaum Text, stellen aber Fotos von Typenschildern, Seriennummern, Verpackungen oder Kassenbons ein. KleinanzeigenRadar liest Schriftzüge auf Fotos automatisch mit!
* **Versand & Entfernung:** Bestimme pro Suche, ob du nur Angebote mit Versand suchst, nur Selbstabholung in deiner Nähe (z. B. 20 km um deine PLZ) oder beides.
* **Preisspanne:** Setze flexibel Mindest- und Höchstpreise fest.
* **Sofort-Meldung via Telegram & E-Mail:** Kein ständiges manuelles Nachschauen mehr – dein Handy meldet sich sofort, wenn etwas Passendes eingestellt wird.
* **SVG-Grafiken statt Emojis:** Alle Oberflächenelemente basieren auf sauberen, hochauflösenden Vektorgrafiken.
* **Automatischer 1-Klick-Aktualisierer:** Prüft auf Knopfdruck über GitHub auf neue Versionen und aktualisiert sich auf Wunsch selbstständig.

---

## Schnellanleitung: Installation (In unter 2 Minuten)

Das mitgelieferte Installationsskript prüft dein System vollautomatisch und richtet alles schlüsselfertig ein.

### 1. Repository klonen & Ordner öffnen
Öffne das Terminal auf deinem Linux-Gerät oder Server:

```bash
git clone https://github.com/loe17/KleinanzeigenRadar.git
cd KleinanzeigenRadar
```

### 2. Installationsskript ausführen
Mache die Skripte ausführbar und starte die automatische Einrichtung:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

Das Skript fragt dich, welchen Modus du bevorzugst:
* **Option 1 (Docker):** Alles startet sauber und abgeschirmt in einem Docker-Container (empfohlen für Synology NAS, Heimserver etc.).
* **Option 2 (Nativ unter Linux):** Richtet Python, die Texterkennung und einen automatischen Hintergrunddienst (`systemd`) ein, der beim Serverstart selbstständig mitstartet.

### 3. Im Browser öffnen
Nach der Installation siehst du die fertige Adresse im Terminal (z. B. `http://deine-server-ip:8000`).
Öffne sie einfach in deinem Webbrowser am PC, Tablet oder Smartphone!

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
* Gibt es eine neue Version, klickst du auf **„Jetzt aktualisieren“** – die Anwendung holt sich die aktuellen Daten direkt von GitHub.

---

## Deinstallation

Möchtest du die Anwendung irgendwann entfernen, genügt ein einziger Befehl:

```bash
./uninstall.sh
```

Das Skript stoppt alle Dienste oder Container sauber und fragt dich, ob deine bisherigen Suchaufträge und Treffer (`data/`) aufbewahrt oder gelöscht werden sollen.

---

## Ordner-Struktur

```text
KleinanzeigenRadar/
├── app/
│   ├── config.py           # Konfiguration, Pfade & Version 0.1.2
│   ├── database.py         # Schnelle SQLite-Datenbank für Suchen & Treffer
│   ├── scraper.py          # Schonendes Kleinanzeigen-Scraping & Wortfilter
│   ├── ocr.py              # Foto-Texterkennung (Bild-Lupe)
│   ├── notifier.py         # Telegram- & E-Mail-Benachrichtigungen
│   ├── updater.py          # GitHub-Versionsprüfung & 1-Klick-Aktualisierer
│   ├── watcher.py          # Zuverlässiger Hintergrund-Wächter
│   ├── static/             # CSS, JavaScript, i18n & SVG-Icons
│   └── templates/          # Haupt-HTML-Oberfläche
├── data/                   # Gespeicherte Suchen & Treffer (bleibt bei Updates erhalten)
├── docs/images/            # Vorschaubilder für die Dokumentation
├── Dockerfile              # Multi-Architektur-Bauplan (x86 & ARM)
├── docker-compose.yml      # 1-Klick Startdatei für Docker
├── install.sh              # Automatisches Prüf- & Installationsskript
├── uninstall.sh            # Automatisches Deinstallationsskript
├── requirements.txt        # Python-Bibliotheken
├── run.py                  # Server-Startpunkt
└── README.md               # Diese Anleitung
```

---

<p align="center">
  Entwickelt für eine entspannte, automatische Schnäppchenjagd auf Kleinanzeigen.
</p>
