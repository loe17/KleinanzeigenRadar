# KleinanzeigenRadar

<p align="center">
  <img src="docs/images/logo.jpg" width="140" height="140" alt="KleinanzeigenRadar Logo" style="border-radius: 20px;">
</p>

<p align="center">
  <b>Dein persönlicher, unermüdlicher Wächter für Kleinanzeigen und Facebook Marketplace</b><br>
  Läuft rund um die Uhr leise auf deinem Linux-System oder im Docker-Container – sowohl auf Standard-PCs (x86) als auch auf sparsamen Geräten wie dem Raspberry Pi (ARM).
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.3.0-86b817.svg" alt="Version 0.3.0">
  <img src="https://img.shields.io/badge/Plattformen-Kleinanzeigen%20%7C%20Facebook%20Marketplace-blue.svg" alt="Kleinanzeigen & Facebook">
  <img src="https://img.shields.io/badge/KI%20Assistent-Gemini%20%7C%20DeepSeek%20%7C%20Claude%20%7C%20OpenAI-purple.svg" alt="AI Negotiation">
  <img src="https://img.shields.io/badge/Domain-kleinanzeigenradar.local-purple.svg" alt="Local Domain">
  <img src="https://img.shields.io/badge/Sicherheit-HTTPS%20%7C%20SSL-green.svg" alt="HTTPS">
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
Schlicht, fokussiert und ohne Ablenkung mit gestochen scharfen SVG-Grafiken und zweisprachiger Benutzeroberfläche (Deutsch & Englisch). Alle Treffer laufen zentral ein und lassen sich blitzschnell nach Plattform (Kleinanzeigen oder Facebook Marketplace), Status, Versandart oder Preisspanne filtern:

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

Normale Suchen auf Verkaufsportalen sind oft ungenau oder verpassen Schnäppchen, weil Verkäufer wichtige Details im Text vergessen oder Tippfehler machen. **KleinanzeigenRadar** findet diese Angebote trotzdem:

* **Facebook Marketplace & Kleinanzeigen kombiniert:** Wähle bei jedem Suchauftrag frei, wo gesucht werden soll: Nur auf Kleinanzeigen, nur auf Facebook Marketplace oder auf beiden Plattformen gleichzeitig. Jedes Inserat ist mit einem gut erkennbaren Plattform-Badge gekennzeichnet. In der Filterleiste kannst du gezielt nach Plattformen filtern.
* **KI-Verhandlungsassistent:** Ein Klick auf "Verhandeln" bei einem Inserat öffnet deinen persönlichen Verhandlungsbegleiter. Lege deinen Wunschpreis (Zielpreis) und optionale Abbruchkriterien fest. Der Assistent analysiert den bisherigen Chatverlauf und formuliert für dich passende, überzeugende Antworten im hinterlegten Verhandlungsstil (Freundlich, Sachlich, Hartnäckig oder Schnäppchenjäger). Unterstützt Google Gemini, DeepSeek, Anthropic Claude, OpenAI, Kimi (Moonshot), lokales Ollama oder eine integrierte Heuristik ganz ohne API-Schlüssel.
* **KI-Deal-Score (Preiseinschätzung):** Berechnet automatisch für jedes Inserat einen transparenten Deal-Score von 0 bis 100 Punkten mit einer nachvollziehbaren Begründung sowie konkreten Vorteilen und Nachteilen des Angebots.
* **Betrugs- & Scam-Radar (Frühwarnung):** Erkennt verdächtige Formulierungen und bekannte Betrugsmaschen (z. B. Bezahlung nur per PayPal Freunde & Familie, angebliche Kurier-Übergaben, Gutschein-Zahlungen oder unrealistische Schleuderpreise) und warnt dich mit klaren Handlungsempfehlungen.
* **Persönliches Notizfeld pro Anzeige:** Halte wichtige Gedanken, Abholtermine, Mängel oder Preisverhandlungen direkt in einem eigenen Notizfeld bei der Anzeige fest. Die Notiz speichert sich automatisch beim Schreiben und wird durch ein dezentes Notiz-Abzeichen in der Übersicht hervorgehoben.
* **In-App Bild-Galerie (Lightbox):** Ein Klick auf ein Foto im Detailfenster öffnet eine bildschirmfüllende Großansicht. Blättere bequem mit den Pfeiltasten deiner Tastatur oder über Vor/Zurück-Schaltflächen durch alle Bilder, nutze die Miniaturansicht-Leiste oder schließe die Galerie mit der Esc-Taste.
* **Intelligente Umkreis-Steuerung:** Das Feld für den Suchradius ist im Suchauftrags-Fenster automatisch deaktiviert, solange keine Postleitzahl eingegeben wurde, um Fehlkonfigurationen zu vermeiden.
* **Treffer-Erhalt bei Suchanpassungen:** Wenn du die Kriterien eines bestehenden Suchauftrags bearbeitest, werden deine bisherigen Treffer nicht blind gelöscht. Anzeigen, die weiterhin zu deinen Kriterien passen, bleiben mit ihrem Status (gelesen, Favorit, persönliche Notizen, Preisverlauf) vollständig erhalten. Nur Angebote, die den neuen Vorgaben nicht mehr entsprechen, werden sauber entfernt.
* **ODER-Syntax (|) für flexible Alternativen:** Mit dem senkrechten Strich (`|`) kannst du beliebig viele Synonyme und Varianten in einem Begriff definieren (z. B. `Laptop | Notebook`, `Sofa | Couch`, `15*" | 17*"` oder `defekt | schaden`). Mindestens einer der Begriffe genügt für einen Treffer.
* **Interaktive Such-Infobox mit Beispielen (i):** Ein Klick auf das dezente (i)-Symbol im Suchauftrags-Fenster öffnet eine übersichtliche Anleitung mit praxisnahen Beispielen für ODER-Verknüpfungen, Joker-Sterne, Maßeinheiten und Ausschlussbegriffe.
* **Erweiterte Teilwort- & Einheitensuche (`*16*GB`):** Intelligente Wortteil-Suche mit automatischer Leerzeichen- und Einheitentoleranz. Suchbegriffe wie `*16*GB` finden `16GB`, `16 GB`, `16-GB`, `RAM: 16 GB` und `16 GB RAM` gleichermaßen.
* **Intelligente Displaygrößen-Erkennung (`15*"`, `15"`, `Zoll`, `Inch`):** Suchst du nach `15*"`, erkennt das System automatisch alle gängigen Schreibweisen wie `15,6 Zoll`, `15 Zoll`, `15-Zoll`, `15"`, `15.6"` oder `15 inch` – ohne dass du jede Variante einzeln anlegen musst.
* **Synonym-Erkennung (`Laptop` / `Notebook`):** Bei der Suche nach `Laptop` oder `Laptops` werden Inserate mit `Notebook` oder `Notebooks` automatisch als vollwertiger Treffer gewertet und umgekehrt.
* **Mehrseiten-Scraping für maximale Treffer:** Scannt bei Suchläufen mehrere Ergebnisseiten ab, sodass auch bei beliebten Kategorien mit hunderten Angeboten keine Schnäppchen übersehen werden.
* **Strikte Preisgrenzen-Sicherheit:** Garantiert, dass Treffer stets innerhalb der definierten Mindest- und Maximalpreisgrenzen deines Suchauftrags liegen, auch wenn die Filterleiste im Dashboard zurückgesetzt wird.
* **Präzise Treffer-Aufschlüsselung:** Zeigt dir genau an, was wo gefunden wurde (z. B. `Titel ('Lenovo', 'T480') • Beschreibung: '16' (...16 GB RAM...)`), inklusive relevantem Textausschnitt.
* **Online-Dauer & Preisverlauf:** Erkennt transparent, wie lange Inserate schon online sind (`vor 2 Std.`, `Heute, 14:23`) und dokumentiert Preissenkungen mit durchgestrichenem Altpreis und Ersparnis (`~~200 €~~ 160 € (-40 €)`). Im Detailfenster siehst du den gesamten Preisverlauf.
* **E-Mail-Vorlagen & SSL/TLS-Unterstützung:** Vorkonfigurierte Vorlagen für Netcup (Port 465 SSL & Port 587 STARTTLS), Gmail, Outlook, GMX, WEB.DE, 1&1/IONOS und Strato. Volle Unterstützung für direktes SSL/TLS (Port 465) und STARTTLS (Port 587) mit klarer Fehlerdiagnose.
* **Live-Treffer Vorschau beim Eintippen:** Während du Suchbegriffe, Preisbereiche oder Postleitzahlen eingibst, ermittelt das System in Sekundenschnelle die aktuelle Trefferanzahl direkt bei den Plattformen und zeigt sie live an.
* **Flexible Such- & Ausschlussbegriffe mit Sternchen-Joker (*):** Beliebig viele Begriffe hinterlegbar mit freier Auswahl zwischen aktivem Suchbegriff (grün) und Ausschlussbegriff (rot). Mit Sternchen wie `*15*` findest du Begriffe auch innerhalb von Wörtern (z. B. `15Zoll` oder `XPS15`), mit `15*` am Wortanfang oder mit `*defekt*`, um auch Teilwörter wie `Teildefekt` auszuschließen.
* **Präzise Trefferlogik (UND-Verknüpfung):** Sind mehrere Suchbegriffe definiert, müssen alle diese Begriffe irgendwo im Inserat (im Titel, der Beschreibung oder auf Fotos) vorkommen. Ausschlussbegriffe filtern unerwünschte Anzeigen zuverlässig heraus.
* **Sortier- & Filteroptionen:** Die Trefferliste lässt sich per Klick nach Neueste, Älteste, Niedrigster Preis oder Höchster Preis sortieren.
* **Lokale Domain & HTTPS:** Direkt im Heimnetzwerk unter `https://kleinanzeigenradar.local` mit automatisch generiertem SSL-Zertifikat erreichbar.
* **Automatische Port-Erkennung:** Sollte ein Standardport (z. B. 8000 oder 8443) bereits belegt sein, sucht das System selbstständig den nächsten freien Port.
* **Die Bild-Lupe (Foto-Texterkennung):** Viele Verkäufer schreiben kaum Text, stellen aber Fotos von Typenschildern, Seriennummern, Verpackungen oder Kassenbons ein. KleinanzeigenRadar liest Schriftzüge auf Fotos automatisch mit!
* **SVG-Grafiken statt Emojis:** Alle Oberflächenelemente basieren auf sauberen, hochauflösenden Vektorgrafiken.
* **Automatischer 1-Klick-Aktualisierer mit Ladebalken & Neustart:** Prüft auf Knopfdruck über GitHub auf neue Versionen, lädt Aktualisierungen mit animiertem Ladebalken herunter und startet den Hintergrunddienst bzw. Docker-Container vollautomatisch neu.

---

## Telegram, E-Mail & KI-Assistent einrichten

1. Klicke in der Web-Oberfläche unten links auf **„Einstellungen & Updates“**.
2. **KI-Verhandlungsassistent & Analyse:**
   * Wähle deinen bevorzugten Anbieter (z. B. *Google Gemini*, *DeepSeek*, *Anthropic Claude*, *OpenAI*, *Kimi (Moonshot)*, lokales *Ollama* oder *Integrierte Heuristik*).
   * Trage deinen API-Schlüssel ein (bei *Integrierte Heuristik* oder lokalem *Ollama* ist kein API-Schlüssel erforderlich).
   * Wähle deinen Standard-Verhandlungsstil (*Freundlich*, *Sachlich*, *Hartnäckig* oder *Schnäppchenjäger*).
3. **Facebook Marketplace:**
   * Optional: Hinterlege deinen Facebook-Session-Cookie (`c_user=...; xs=...`), um auch Angebote abrufen zu können, die eine Anmeldung erfordern.
4. **Telegram:**
   * Gib deinen **Bot-Token** (vom Telegram `@BotFather`) und deine **Chat-ID** ein.
   * Klicke auf **„Telegram-Testnachricht senden“**, um die Verbindung sofort zu testen.
5. **E-Mail:**
   * Wähle bei Bedarf eine **Vorlage** (z. B. *Netcup*, *Gmail*, *Outlook*, etc.) aus, um Serveradresse, Port und Verschlüsselung automatisch auszufüllen.
   * Trage deine E-Mail-Zugangsdaten sowie Absender- und Empfängeradresse ein.
   * Klicke auf **„Test-E-Mail senden“**. Bei Fehlern gibt dir das System präzise deutsche Diagnosehinweise.
6. Klicke auf **„Einstellungen speichern“**. Fertig!

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
│   ├── config.py           # Konfiguration, Pfade & Version 0.3.0
│   ├── database.py         # Schnelle SQLite-Datenbank, Preisverlauf, Notizen & Score-Cache
│   ├── network_utils.py    # Automatische Suche nach freien Ports & IPs
│   ├── ssl_cert.py         # Automatische SSL-Zertifikatsgenerierung (HTTPS)
│   ├── scraper.py          # Multiseiten-Scraping, Plattform-Dispatch & Wortfilter
│   ├── facebook_scraper.py # Facebook Marketplace Extraktion & Cookie-Unterstützung
│   ├── ai_engine.py        # KI-Verhandlungsassistent, Deal-Score & Scam-Radar
│   ├── ocr.py              # Foto-Texterkennung (Bild-Lupe)
│   ├── notifier.py         # Telegram- & E-Mail-Benachrichtigungen (SSL & STARTTLS)
│   ├── updater.py          # GitHub-Versionsprüfung, Ladebalken & Auto-Restart
│   ├── watcher.py          # Zuverlässiger Hintergrund-Wächter
│   ├── static/             # CSS, JavaScript, i18n & SVG-Icons
│   └── templates/          # Haupt-HTML-Oberfläche mit Lightbox & Verhandlungs-Modal
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
  Entwickelt für eine entspannte, automatische Schnäppchenjagd auf Kleinanzeigen und Facebook Marketplace.
</p>
