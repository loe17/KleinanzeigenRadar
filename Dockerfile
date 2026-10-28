# Multi-Architektur Basis-Image (unterstützt x86_64, ARM64 und ARMv7)
FROM python:3.11-slim

# Umgebungsvariablen setzen
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    HOST=0.0.0.0

# Arbeitsverzeichnis
WORKDIR /app

# System-Abhängigkeiten installieren: Tesseract-OCR mit Deutsch/Englisch-Sprachdaten, Git und Curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    libgl1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungs-Code kopieren
COPY . .

# Datenverzeichnis für persistente SQLite-Datenbank erstellen
RUN mkdir -p /app/data

# Port freigeben
EXPOSE 8000

# Startbefehl
CMD ["python", "run.py"]
