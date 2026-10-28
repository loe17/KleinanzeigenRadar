#!/usr/bin/env bash
# ==============================================================================
# KleinanzeigenRadar - Vollautomatisches Deinstallationsskript
# Stoppt Dienste, entfernt Autostarts und räumt auf Wunsch Daten auf.
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}"
echo "=========================================================="
echo "         KleinanzeigenRadar - Deinstallation             "
echo "=========================================================="
echo -e "${NC}"

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TYPE=""

if [ -f "$INSTALL_DIR/.install_type" ]; then
    INSTALL_TYPE=$(cat "$INSTALL_DIR/.install_type")
fi

echo -e "${BLUE}[1/3] Prüfe vorhandene Installation...${NC}"

# 1. Docker-Deinstallation
if [ "$INSTALL_TYPE" == "docker" ] || docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "kleinanzeigen-radar"; then
    echo -e "  -> Docker-Container erkannt. Stoppe und entferne Container..."
    cd "$INSTALL_DIR"
    if docker compose version &> /dev/null; then
        docker compose down
    elif command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker stop kleinanzeigen-radar 2>/dev/null || true
        docker rm kleinanzeigen-radar 2>/dev/null || true
    fi
    echo -e "${GREEN}  [OK] Docker-Container gestoppt und entfernt.${NC}"
fi

# 2. Native Systemd-Deinstallation
if [ "$INSTALL_TYPE" == "native" ] || [ -f "/etc/systemd/system/kleinanzeigen-radar.service" ]; then
    echo -e "  -> Nativer systemd-Dienst erkannt. Stoppe und deaktiviere Dienst..."
    if [ "$EUID" -ne 0 ]; then
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi

    $SUDO_CMD systemctl stop kleinanzeigen-radar 2>/dev/null || true
    $SUDO_CMD systemctl disable kleinanzeigen-radar 2>/dev/null || true
    $SUDO_CMD rm -f /etc/systemd/system/kleinanzeigen-radar.service
    $SUDO_CMD systemctl daemon-reload
    echo -e "${GREEN}  [OK] systemd-Dienst entfernt.${NC}"

    if [ -d "$INSTALL_DIR/venv" ]; then
        echo -e "  -> Entferne Python-Umgebung (venv)..."
        rm -rf "$INSTALL_DIR/venv"
    fi
fi

# 3. Daten behalten oder löschen?
echo ""
echo -e "${BLUE}[2/3] Behandlung der gespeicherten Daten:${NC}"
echo "In 'data/' liegen deine eingerichteten Suchen und gefundenen Inserate."
read -p "Möchtest du diese Daten behalten oder löschen? [B = Behalten / L = Löschen, Standard: B]: " DATA_CHOICE
DATA_CHOICE=${DATA_CHOICE:-B}

if [[ "$DATA_CHOICE" =~ ^[Ll]$ ]]; then
    echo -e "${YELLOW}Lösche Datenverzeichnis...${NC}"
    rm -rf "$INSTALL_DIR/data"
    echo -e "${GREEN}  [OK] Datenverzeichnis gelöscht.${NC}"
else
    echo -e "${GREEN}  [OK] Deine Suchen & Treffer in 'data/' wurden sicher aufbewahrt.${NC}"
fi

# Aufräumen
rm -f "$INSTALL_DIR/.install_type"

echo ""
echo -e "${GREEN}"
echo "=========================================================="
echo "    KleinanzeigenRadar wurde erfolgreich deinstalliert!   "
echo "=========================================================="
echo -e "${NC}"
