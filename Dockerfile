# Dockerfile für den Einsatz auf einem Raspberry Pi (armhf/arm64)
FROM python:3.11-slim

# Arbeitsverzeichnis setzen
WORKDIR /app

# Abhängigkeiten installieren
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Projektdateien kopieren
COPY . .

# Standardkommando: Anwendung starten
ENTRYPOINT ["python", "web_app.py"]
