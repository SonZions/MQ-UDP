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
  [-e LOXONE_HOSTNAME=miniserver.local] \
  [-e LOXONE_URL=<https://host/data/LoxAPP3.json>] \
  [-e LOXONE_USERNAME=<BENUTZER>] \
  [-e LOXONE_PASSWORD=<PASSWORT>] \
  [-e LOXONE_JSON_PATH=/data/loxone.json] \
  [-e LOXONE_STATE_URL_TEMPLATE=<https://host/jdev/sps/io/{uuid}/state>] \
  [-e AUTO_CONFIG_PATH=/data/auto_config.json] \
  [-v $(pwd)/data:/data] \
  mq-udp
```

* `AUTO_CONFIG_PATH` legt den Speicherort für die Automatikmodus-Konfiguration
  fest. Wird eine Datei außerhalb des Containers genutzt, sollte das
  entsprechende Verzeichnis als Volume eingebunden werden (siehe Beispiel mit
  `-v`).
* `LOXONE_HOSTNAME` setzt den Hostnamen deines Miniservers. Daraus werden
  standardmäßig `LOXONE_URL` (`http://<hostname>/data/LoxAPP3.json`) und die
  Statusabfrage (`http://<hostname>/jdev/sps/io/{uuid}/state`) abgeleitet.
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

- `LOXONE_HOSTNAME`: Hostname oder IP-Adresse deines Miniservers. Ohne weitere
  Angaben werden daraus `LOXONE_URL` und `LOXONE_STATE_URL_TEMPLATE`
  abgeleitet.
- `LOXONE_URL`: Vollständige URL zur `LoxAPP3.json` deines Miniservers
- `LOXONE_USERNAME` / `LOXONE_PASSWORD`: Zugangsdaten für Basic Auth
- `LOXONE_JSON_PATH`: Pfad zu einer lokalen JSON-Datei (optional, Standard: `json.txt`)
- `LOXONE_STATE_URL_TEMPLATE`: URL-Schablone zum direkten Abfragen einzelner
  Statuswerte (optional, Standard: `http://<hostname>/jdev/sps/io/{uuid}/state`
  bei gesetztem Hostname bzw. Ableitung aus `LOXONE_URL`)
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

## Icons auf der AWTRIX

Die Weboberfläche ermöglicht es, jedem Steuerelement ein Icon aus der
[LaMetric Icon Gallery](https://developer.lametric.com/icons) zuzuweisen. Im
JSON-Payload wird dann die numerische Icon-ID mitgeschickt (z. B.
`{"text": "22.5 °C", "icon": 2056}`).

**Wichtig:** Das Icon muss zusätzlich auf der AWTRIX selbst heruntergeladen
werden. Die AWTRIX kennt nur Icons, die lokal auf ihrem Dateisystem im Ordner
`ICONS` liegen. Wird eine Icon-ID gesendet, die auf dem Gerät nicht vorhanden
ist, wird kein Icon angezeigt.

### Icons manuell herunterladen

1. Öffne die **AWTRIX-Weboberfläche** (z. B. `http://<AWTRIX_IP>/`).
2. Wechsle zum **Icons**-Tab.
3. Gib die gewünschte **LaMetric Icon-ID** ein (die gleiche ID, die du in
   MQ-UDP ausgewählt hast) und klicke auf **Download**.
4. Das Icon wird direkt von LaMetric heruntergeladen und steht sofort zur
   Verfügung.

Alternativ kannst du Icons im **Dateimanager** der AWTRIX-Weboberfläche
manuell in den Ordner `ICONS` hochladen. Unterstützte Formate: GIF (max.
32×8 Pixel) und JPG (max. 8×8 Pixel). Dateien können umbenannt werden –
statt der numerischen ID (z. B. `2056.gif`) kann auch ein sprechender Name
verwendet werden (z. B. `temperatur.gif`), der dann als `"icon": "temperatur"`
im Payload referenziert wird.

### Automatischer Download per API

AWTRIX 3 bietet keine offiziell dokumentierte HTTP- oder MQTT-API zum
automatischen Herunterladen von Icons. Der Icon-Download erfolgt aktuell
ausschließlich über die Weboberfläche oder die AWTRIX-3-App.

Als **Alternative** kann im Custom-App-Payload ein 8×8-JPG-Bild als
Base64-String direkt im `icon`-Feld mitgeschickt werden – dafür muss das Icon
nicht vorher auf der AWTRIX gespeichert sein:

```json
{"text": "22.5 °C", "icon": "data:image/jpeg;base64,/9j/4AAQ..."}
```

Diese Methode eignet sich vor allem für dynamische oder einmalige Icons,
ist aber auf statische 8×8-JPGs beschränkt (keine Animationen).

## Automatische Aktualisierung der Statuswerte

Wenn der Automatikmodus aktiv ist und mindestens ein Steuerelement aktiviert
wurde, werden die Werte **regelmäßig** von Loxone abgerufen und auf dem
MQTT-Topic veröffentlicht:

1. In jedem Intervall (konfigurierbar über `AUTOMATIC_INTERVAL`, Standard:
   60 Sekunden) wird die `LoxAPP3.json` vom Miniserver geladen.
2. Für jedes aktivierte Steuerelement werden die zugehörigen Status-UUIDs
   einzeln über die Loxone-Status-API abgefragt
   (`http://<hostname>/jdev/sps/io/<uuid>/state`).
3. Aus den Ergebnissen wird ein AWTRIX-kompatibles JSON-Payload erzeugt und
   per MQTT veröffentlicht.
4. Unveränderte Werte werden nur im App-Modus nach 60 Sekunden erneut
   gesendet; im Notification-Modus werden Duplikate unterdrückt.

Die Aktualisierung läuft vollständig automatisch im Hintergrund – es ist
kein manuelles Eingreifen nötig. Voraussetzung ist, dass die
Loxone-Umgebungsvariablen (`LOXONE_HOSTNAME` oder `LOXONE_URL` sowie ggf.
`LOXONE_USERNAME`/`LOXONE_PASSWORD`) korrekt gesetzt sind.
