# MQ-UDP

MQ-UDP kombiniert eine einfache Brücke zwischen MQTT-Themen und einem
UDP-Endpunkt mit einer Weboberfläche für die Loxone-Daten. Nachrichten, die auf
dem konfigurierten MQTT-Topic eintreffen, werden einmalig über UDP weitergeleitet
und UDP-Pakete werden auf dem MQTT-Topic veröffentlicht. Zusätzlich können über
die Weboberfläche Steuerelemente für einen Automatikmodus ausgewählt werden, die
in regelmäßigen Abständen als MQTT-Nachrichten veröffentlicht werden.

## Nutzung

```bash
python app.py \
  --mqtt-broker <BROKER> \
  --mqtt-topic <TOPIC> \
  [--mqtt-port 1883] \
  [--mqtt-username <BENUTZER>] \
  [--mqtt-password <PASSWORT>] \
  [--udp-ip 127.0.0.1] \
  [--udp-port 5005] \
  [--automatic-interval 30]
```

## Docker

```bash
docker build -t mq-udp .
docker run --rm \
  -p 8000:8000 \
  -e MQTT_BROKER=<BROKER> \
  -e MQTT_TOPIC=<TOPIC> \
  [-e MQTT_PORT=1883] \
  [-e MQTT_USERNAME=<BENUTZER>] \
  [-e MQTT_PASSWORD=<PASSWORT>] \
  [-e UDP_IP=127.0.0.1] \
  [-e UDP_PORT=5005] \
  [-e AUTOMATIC_INTERVAL=30] \
  [-e LOXONE_URL=<https://host/data/LoxAPP3.json>] \
  [-e LOXONE_USERNAME=<BENUTZER>] \
  [-e LOXONE_PASSWORD=<PASSWORT>] \
  [-e LOXONE_JSON_PATH=/data/loxone.json] \
  [-e LOXONE_STATE_URL_TEMPLATE=<https://host/dev/sps/io/{uuid}>] \
  [-e AUTO_CONFIG_PATH=/data/auto_config.json] \
  [-v $(pwd)/data:/data] \
  mq-udp
```

* `AUTO_CONFIG_PATH` legt den Speicherort für die Automatikmodus-Konfiguration
  fest. Wird eine Datei außerhalb des Containers genutzt, sollte das
  entsprechende Verzeichnis als Volume eingebunden werden (siehe Beispiel mit
  `-v`).
* `LOXONE_JSON_PATH` kann auf eine bereits vorhandene JSON-Datei zeigen, die im
  Container verfügbar ist.
* `LOXONE_STATE_URL_TEMPLATE` überschreibt die automatisch abgeleitete URL für
  das Nachladen einzelner Statuswerte. Der Platzhalter `{uuid}` wird durch die
  jeweilige UUID des Status ersetzt.
* Über `AUTOMATIC_INTERVAL` wird das Veröffentlichungsintervall der automatisch
  ausgewählten Werte (in Sekunden) festgelegt.

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
- `LOXONE_STATE_URL_TEMPLATE`: URL-Schablone zum direkten Abfragen einzelner
  Statuswerte (optional, Standard: Ableitung aus `LOXONE_URL`)
- `AUTO_CONFIG_PATH`: Pfad zur JSON-Datei, in der die Automatik-Konfiguration
  gespeichert wird (Standard: `auto_config.json` im Arbeitsverzeichnis)
- `AUTOMATIC_INTERVAL`: Veröffentlichungsintervall der automatischen MQTT-Nachrichten

Der Host und Port können über Argumente oder Umgebungsvariablen angepasst werden:

```bash
python web_app.py --host 0.0.0.0 --port 9000
# oder per Umgebungsvariablen
WEBAPP_HOST=0.0.0.0 WEBAPP_PORT=9000 python web_app.py
```

Nach dem Start ist die Tabelle unter <http://HOST:PORT/> erreichbar (Standard:
<http://localhost:8000/>).
