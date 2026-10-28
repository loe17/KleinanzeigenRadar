#!/usr/bin/env bash
# ==============================================================================
# KleinanzeigenRadar - Vollautomatisches Installationsskript
# Unterstützt: Linux (x86_64, ARM64, ARMv7, Raspberry Pi)
# Modi: Docker Container (Standard) oder Nativ (systemd)
# ==============================================================================

set -e

# Farben für Terminal-Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "=========================================================="
echo "          KleinanzeigenRadar - Setup & Installation       "
echo "=========================================================="
echo -e "${NC}"

# Root / Sudo Erkennung
if [ "$EUID" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        SUDO_CMD="sudo"
    else
        echo -e "${RED}Fehler: Bitte als Root oder mit installiertem 'sudo' ausführen.${NC}"
        exit 1
    fi
else
    SUDO_CMD=""
fi

# 1. System & Architektur prüfen
ARCH=$(uname -m)
echo -e "${BLUE}[1/5] Prüfe System-Architektur...${NC}"
case "$ARCH" in
  x86_64|amd64)
    ARCH_NAME="x86_64 (Standard PC / Server)"
    ;;
  aarch64|arm64)
    ARCH_NAME="ARM64 (Raspberry Pi 3/4/5 64-bit / ARM-Server)"
    ;;
  armv7l|armhf)
    ARCH_NAME="ARMv7 (Raspberry Pi 32-bit)"
    ;;
  *)
    ARCH_NAME="Unbekannt ($ARCH)"
    ;;
esac
echo -e "  -> Erkannte Architektur: ${GREEN}$ARCH_NAME${NC}"

# Betriebssystem prüfen
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_ID=$ID
else
    OS_NAME=$(uname -s)
    OS_ID="unknown"
fi
echo -e "  -> Betriebssystem: ${GREEN}$OS_NAME ($OS_ID)${NC}"

# Hilfsfunktion: Automatische Installation fehlender Basispakete
install_package() {
    PKG=$1
    if ! command -v "$PKG" &> /dev/null; then
        echo -e "${YELLOW}Installiere fehlendes Basispaket: $PKG...${NC}"
        if [ "$OS_ID" == "debian" ] || [ "$OS_ID" == "ubuntu" ] || [ "$OS_ID" == "raspbian" ]; then
            $SUDO_CMD apt-get update -qq && $SUDO_CMD apt-get install -y -qq "$PKG" ca-certificates
        elif [ "$OS_ID" == "fedora" ] || [ "$OS_ID" == "rhel" ] || [ "$OS_ID" == "centos" ]; then
            $SUDO_CMD dnf install -y -q "$PKG" ca-certificates
        elif [ "$OS_ID" == "arch" ] || [ "$OS_ID" == "manjaro" ]; then
            $SUDO_CMD pacman -Sy --noconfirm "$PKG" ca-certificates
        elif [ "$OS_ID" == "alpine" ]; then
            $SUDO_CMD apk add --no-cache "$PKG" ca-certificates
        fi
    fi
}

# Sicherstellen, dass curl, ca-certificates und git bereitstehen
install_package curl
install_package ca-certificates

# Arbeitsverzeichnis ermitteln
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"

# Falls das Skript über 'curl ... | bash' aufgerufen wurde und keine Projektdateien vorliegen:
if [ ! -f "$INSTALL_DIR/Dockerfile" ] && [ ! -f "$INSTALL_DIR/run.py" ]; then
    echo -e "${YELLOW}Projektdateien nicht gefunden. Klone KleinanzeigenRadar von GitHub...${NC}"
    install_package git
    TARGET_DIR="KleinanzeigenRadar"
    git clone https://github.com/loe17/KleinanzeigenRadar.git "$TARGET_DIR"
    cd "$TARGET_DIR"
    INSTALL_DIR="$(pwd)"
fi

cd "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"

# 2. Installationsmodus bestimmen (Docker oder Nativ)
echo ""
echo -e "${BLUE}[2/5] Wähle den gewünschten Installationsmodus:${NC}"

MODE=""
if [ "$1" == "--docker" ]; then
    MODE="1"
elif [ "$1" == "--native" ]; then
    MODE="2"
fi

if [ -z "$MODE" ]; then
    echo "  1) Docker Container (Empfohlen - Alles isoliert im Container)"
    echo "  2) Nativ unter Linux (Als systemd Hintergrunddienst mit Python)"
    
    # Sicherstellen, dass interaktive Eingabe auch via 'curl | bash' Pipe funktioniert
    if [ -t 0 ]; then
        read -p "Auswahl eingeben [1 oder 2, Standard: 1]: " USER_CHOICE
    elif [ -c /dev/tty ]; then
        read -p "Auswahl eingeben [1 oder 2, Standard: 1]: " USER_CHOICE < /dev/tty
    else
        USER_CHOICE="1"
    fi
    MODE=${USER_CHOICE:-1}
fi

# ==============================================================================
# MODUS 1: DOCKER INSTALLATION
# ==============================================================================
if [ "$MODE" == "1" ]; then
    echo ""
    echo -e "${BLUE}[3/5] Prüfe Docker-Voraussetzungen...${NC}"
    
    # 1. Prüfen ob Docker installiert ist
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker ist noch nicht installiert. Starte automatische Docker-Installation...${NC}"
        
        # Sicherstellen, dass curl da ist
        install_package curl
        
        # Offizielles Docker-Installationsskript herunterladen & ausführen
        DOCKER_INSTALLED=false
        if command -v curl &> /dev/null; then
            curl -fsSL https://get.docker.com -o get-docker.sh && $SUDO_CMD sh get-docker.sh && DOCKER_INSTALLED=true
            rm -f get-docker.sh
        elif command -v wget &> /dev/null; then
            wget -qO get-docker.sh https://get.docker.com && $SUDO_CMD sh get-docker.sh && DOCKER_INSTALLED=true
            rm -f get-docker.sh
        fi

        # Fallback falls get.docker.com fehlschlägt
        if [ "$DOCKER_INSTALLED" = false ]; then
            echo -e "${YELLOW}Versuche Docker-Installation über System-Paketmanager...${NC}"
            if [ "$OS_ID" == "debian" ] || [ "$OS_ID" == "ubuntu" ] || [ "$OS_ID" == "raspbian" ]; then
                $SUDO_CMD apt-get update -qq
                $SUDO_CMD apt-get install -y docker.io docker-compose-plugin || $SUDO_CMD apt-get install -y docker.io docker-compose
            fi
        fi
    fi

    # 2. Docker-Dienst starten & aktivieren
    echo -e "  -> Stelle sicher, dass der Docker-Dienst läuft..."
    $SUDO_CMD systemctl start docker 2>/dev/null || $SUDO_CMD service docker start 2>/dev/null || true
    $SUDO_CMD systemctl enable docker 2>/dev/null || true

    # 3. Docker Compose prüfen / nachinstallieren
    DOCKER_COMPOSE_CMD=""
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif $SUDO_CMD docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="$SUDO_CMD docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif $SUDO_CMD command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="$SUDO_CMD docker-compose"
    else
        echo -e "${YELLOW}Docker Compose fehlt. Installiere Compose-Plugin...${NC}"
        if [ "$OS_ID" == "debian" ] || [ "$OS_ID" == "ubuntu" ] || [ "$OS_ID" == "raspbian" ]; then
            $SUDO_CMD apt-get update -qq
            $SUDO_CMD apt-get install -y -qq docker-compose-plugin || $SUDO_CMD apt-get install -y -qq docker-compose
            DOCKER_COMPOSE_CMD="docker compose"
        else
            echo -e "${RED}Fehler: Bitte installiere Docker Compose für deine Distribution.${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}  [OK] Docker und Compose sind bereit.${NC}"

    echo -e "${BLUE}[4/5] Baue und starte KleinanzeigenRadar Docker Container...${NC}"
    cd "$INSTALL_DIR"
    
    # Container starten
    if ! $DOCKER_COMPOSE_CMD up -d --build; then
        echo -e "${RED}Fehler beim Starten der Docker-Container. Versuche mit sudo...${NC}"
        $SUDO_CMD $DOCKER_COMPOSE_CMD up -d --build
    fi

    # Markiere Installationstyp für Uninstaller
    echo "docker" > "$INSTALL_DIR/.install_type"

# ==============================================================================
# MODUS 2: NATIVE LINUX INSTALLATION (SYSTEMD)
# ==============================================================================
elif [ "$MODE" == "2" ]; then
    echo ""
    echo -e "${BLUE}[3/5] Prüfe und installiere native System-Pakete...${NC}"

    if [ "$OS_ID" == "debian" ] || [ "$OS_ID" == "ubuntu" ] || [ "$OS_ID" == "raspbian" ]; then
        $SUDO_CMD apt-get update -qq
        $SUDO_CMD apt-get install -y \
            python3 \
            python3-venv \
            python3-pip \
            tesseract-ocr \
            tesseract-ocr-deu \
            tesseract-ocr-eng \
            git \
            curl
    elif [ "$OS_ID" == "fedora" ] || [ "$OS_ID" == "rhel" ] || [ "$OS_ID" == "centos" ]; then
        $SUDO_CMD dnf install -y python3 python3-pip tesseract tesseract-langpack-deu git curl
    elif [ "$OS_ID" == "arch" ] || [ "$OS_ID" == "manjaro" ]; then
        $SUDO_CMD pacman -Sy --noconfirm python python-pip tesseract tesseract-data-deu git curl
    else
        echo -e "${YELLOW}Achtung: Unbekannte Linux-Distribution. Bitte stelle sicher, dass Python3, Venv und Tesseract-OCR installiert sind.${NC}"
    fi

    echo -e "${BLUE}[4/5] Richte Python-Umgebung ein...${NC}"
    cd "$INSTALL_DIR"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt

    # Systemd-Dienst einrichten
    echo -e "${BLUE}Erstelle systemd Hintergrunddienst 'kleinanzeigen-radar'...${NC}"
    CURRENT_USER=${SUDO_USER:-$USER}
    SERVICE_FILE="/etc/systemd/system/kleinanzeigen-radar.service"

    $SUDO_CMD bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=KleinanzeigenRadar Wächter Dienst
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py
Restart=always
RestartSec=5
Environment=PORT=8000
Environment=HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
EOF"

    $SUDO_CMD systemctl daemon-reload
    $SUDO_CMD systemctl enable kleinanzeigen-radar
    $SUDO_CMD systemctl restart kleinanzeigen-radar

    # Markiere Installationstyp für Uninstaller
    echo "native" > "$INSTALL_DIR/.install_type"

else
    echo -e "${RED}Ungültige Auswahl. Installation abgebrochen.${NC}"
    exit 1
fi

# ==============================================================================
# ABSCHLUSS & PRÜFUNG
# ==============================================================================
echo ""
echo -e "${BLUE}[5/5] Überprüfe Ausführung...${NC}"
sleep 2

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo -e "${GREEN}"
echo "=========================================================="
echo "   Installation von KleinanzeigenRadar war erfolgreich!   "
echo "=========================================================="
echo -e "${NC}"
echo -e "Die Anwendung laeuft im Hintergrund und ist ab sofort erreichbar unter:"
echo -e "  -> ${GREEN}http://${LOCAL_IP}:8000${NC} oder ${GREEN}http://localhost:8000${NC}"
echo ""
echo "Tipp: Richte in der Oberfläche (Zahnrad-Symbol) direkt deinen Telegram-Bot"
echo "ein, um sofort über passende Angebote informiert zu werden!"
echo ""
