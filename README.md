# MQ-UDP

MQ-UDP stellt eine einfache Brücke zwischen MQTT-Themen und einem UDP-Endpunkt
bereit. Nachrichten, die auf dem konfigurierten MQTT-Topic eintreffen, werden
einmalig über UDP weitergeleitet. Gleichzeitig werden UDP-Pakete empfangen und
auf dem MQTT-Topic veröffentlicht.

## Nutzung

```bash
python app.py \
  --mqtt-broker <BROKER> \
  --mqtt-topic <TOPIC> \
  [--mqtt-port 1883] \
  [--mqtt-username <BENUTZER>] \
  [--mqtt-password <PASSWORT>] \
  [--udp-ip 127.0.0.1] \
  [--udp-port 5005]
```

## Docker

```bash
docker build -t mq-udp .
docker run --rm mq-udp \
  --mqtt-broker <BROKER> \
  --mqtt-topic <TOPIC> \
  --udp-ip <UDP_IP>
```

## Webansicht der Loxone Werte

Zusätzlich zur MQTT/UDP-Brücke steht eine kleine FastAPI-Anwendung bereit, die
alle Werte der `LoxAPP3.json` in einer tabellarischen Weboberfläche darstellt.

### Starten

```bash
pip install -r requirements.txt
python web_app.py --reload
```

Standardmäßig wird die Beispieldatei `json.txt` aus dem Repository verwendet.
Um die Daten direkt von deinem Miniserver abzurufen, können folgende
Umgebungsvariablen gesetzt werden:

- `LOXONE_URL`: Vollständige URL zur `LoxAPP3.json` deines Miniservers
- `LOXONE_USERNAME` / `LOXONE_PASSWORD`: Zugangsdaten für Basic Auth
- `LOXONE_JSON_PATH`: Pfad zu einer lokalen JSON-Datei (optional, Standard: `json.txt`)

Der Host und Port können über Argumente oder Umgebungsvariablen angepasst werden:

```bash
python web_app.py --host 0.0.0.0 --port 9000
# oder per Umgebungsvariablen
WEBAPP_HOST=0.0.0.0 WEBAPP_PORT=9000 python web_app.py
```

Nach dem Start ist die Tabelle unter <http://HOST:PORT/> erreichbar (Standard:
<http://localhost:8000/>).
