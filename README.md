# MQ-UDP – Loxone-Werte auf der AWTRIX-Uhr anzeigen

MQ-UDP verbindet dein **Loxone Smart-Home** mit einer **AWTRIX-Pixeluhr** (z. B. Ulanzi TC001). Du wählst in einer Weboberfläche aus, welche Loxone-Sensoren oder Steuerelemente auf der Uhr angezeigt werden sollen – der Rest läuft vollautomatisch im Hintergrund.

```
Loxone Miniserver  →  MQ-UDP (dieses Tool)  →  MQTT-Broker  →  AWTRIX-Uhr
```

---

## Inhalt

1. [Was macht die App?](#1-was-macht-die-app)
2. [Voraussetzungen](#2-voraussetzungen)
3. [AWTRIX auf den Ulanzi TC001 flashen](#3-awtrix-auf-den-ulanzi-tc001-flashen)
4. [MQTT-Broker aufsetzen](#4-mqtt-broker-aufsetzen)
5. [AWTRIX mit dem MQTT-Broker verbinden](#5-awtrix-mit-dem-mqtt-broker-verbinden)
6. [Loxone-Benutzer anlegen](#6-loxone-benutzer-anlegen)
7. [MQ-UDP installieren und starten](#7-mq-udp-installieren-und-starten)
8. [Weboberfläche bedienen](#8-weboberfläche-bedienen)
9. [Icons auf der AWTRIX](#9-icons-auf-der-awtrix)
10. [Referenzen](#10-referenzen)

---

## 1. Was macht die App?

MQ-UDP besteht aus zwei Teilen, die gemeinsam laufen:

**Weboberfläche (Hauptfunktion)**
- Liest die Struktur deines Loxone Miniservers aus (alle Räume, Steuerelemente, Sensoren)
- Zeigt alle gefundenen Steuerelemente in einer übersichtlichen Tabelle
- Du aktivierst per Checkbox, welche Werte auf der AWTRIX erscheinen sollen
- Optional kannst du pro Steuerelement ein Icon und den Anzeigemodus (App oder Benachrichtigung) wählen
- Im Hintergrund fragt MQ-UDP die aktuellen Werte bei Loxone ab und schickt sie automatisch per MQTT an die AWTRIX

**MQTT ↔ UDP-Brücke (Zusatzfunktion)**
- Leitet MQTT-Nachrichten als UDP-Pakete weiter und umgekehrt
- Wird mitgestartet, solange `MQTT_BROKER` und `MQTT_TOPIC` gesetzt sind

---

## 2. Voraussetzungen

| Was | Wozu |
|-----|------|
| Ulanzi TC001 (oder kompatible Hardware) | Die Pixeluhr, auf der die Werte angezeigt werden |
| AWTRIX 3 Firmware | Betriebssystem der Uhr, muss geflasht werden |
| MQTT-Broker (z. B. Mosquitto) | Nachrichten-Vermittler zwischen MQ-UDP und AWTRIX |
| Loxone Miniserver | Deine Smart-Home-Zentrale |
| Docker **oder** Python 3.11+ | Zum Ausführen von MQ-UDP |

Alle Komponenten müssen im selben Netzwerk erreichbar sein.

---

## 3. AWTRIX auf den Ulanzi TC001 flashen

Der Ulanzi TC001 wird mit einer eigenen Firmware ausgeliefert. Für MQ-UDP benötigst du die **AWTRIX 3**-Firmware.

### Schritt für Schritt

1. **AWTRIX Web-Flasher öffnen**
   Gehe auf [https://my.awtrix.dev](https://my.awtrix.dev) in einem Chrome- oder Edge-Browser (Firefox wird nicht unterstützt).

2. **Gerät verbinden**
   Verbinde den Ulanzi TC001 per USB mit deinem Computer.

3. **Flashen starten**
   - Klicke auf **„Install AWTRIX 3"**
   - Wähle den richtigen COM-Port (Windows) bzw. `/dev/ttyUSB0` oder `/dev/ttyACM0` (Linux/Mac)
   - Bestätige und warte bis der Vorgang abgeschlossen ist (ca. 1–2 Minuten)

4. **WLAN einrichten**
   Nach dem Flash startet die Uhr im Hotspot-Modus (`AWTRIX-XXXXXX`).
   - Verbinde dein Telefon oder den PC mit diesem WLAN
   - Ein Captive Portal öffnet sich automatisch (oder rufe `http://192.168.4.1` auf)
   - Trage deine WLAN-SSID und das Passwort ein
   - Die Uhr verbindet sich neu und zeigt ihre IP-Adresse an

5. **Weboberfläche der Uhr öffnen**
   Rufe `http://<AWTRIX_IP>` in deinem Browser auf. Hier kannst du alle Einstellungen vornehmen.

> **Offizielle Dokumentation:** [https://blueforcer.github.io/awtrix3](https://blueforcer.github.io/awtrix3)

---

## 4. MQTT-Broker aufsetzen

Ein MQTT-Broker ist ein zentraler Nachrichtenverteiler. Die einfachste Lösung ist **Eclipse Mosquitto**.

### Installation auf einem Raspberry Pi oder Linux-Server

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Benutzer anlegen (empfohlen)

Es ist sinnvoll, einen eigenen MQTT-Benutzer für AWTRIX und einen für MQ-UDP anzulegen.

```bash
# Benutzer anlegen (Passwort wird abgefragt)
sudo mosquitto_passwd -c /etc/mosquitto/passwd awtrix
sudo mosquitto_passwd /etc/mosquitto/passwd mq-udp
```

### Konfiguration anpassen

Erstelle oder bearbeite `/etc/mosquitto/conf.d/local.conf`:

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

```bash
sudo systemctl restart mosquitto
```

### Verbindung testen

```bash
# Subscriber starten (Nachrichten empfangen)
mosquitto_sub -h localhost -u mq-udp -P <PASSWORT> -t "test/#" -v

# Publisher in einem zweiten Terminal (Nachricht senden)
mosquitto_pub -h localhost -u mq-udp -P <PASSWORT> -t "test/hello" -m "Hallo!"
```

---

## 5. AWTRIX mit dem MQTT-Broker verbinden

1. Öffne die **AWTRIX-Weboberfläche** unter `http://<AWTRIX_IP>`
2. Wechsle zu **Settings → MQTT**
3. Trage ein:
   - **Broker:** IP-Adresse deines MQTT-Brokers (z. B. `192.168.1.100`)
   - **Port:** `1883`
   - **Username / Password:** die Zugangsdaten des AWTRIX-Benutzers (aus Schritt 4)
   - **Prefix:** `awtrix` (oder ein Name deiner Wahl – dieser Präfix wird später in MQ-UDP als `MQTT_TOPIC` verwendet)
4. Speichern und Verbindung prüfen – die Statusanzeige sollte grün werden

MQ-UDP schickt Nachrichten an Topics der Form `<prefix>/custom/<uuid>` (persistente App) oder `<prefix>/notify` (einmalige Benachrichtigung).

---

## 6. Loxone-Benutzer anlegen

MQ-UDP liest Daten **nur lesend** vom Loxone Miniserver. Der Benutzer benötigt daher minimale Rechte.

### Benutzer in Loxone Config anlegen

1. Öffne **Loxone Config** und verbinde dich mit deinem Miniserver
2. Gehe zu **Benutzer** → **Neu**
3. Vergib einen Namen (z. B. `mq-udp` oder `dashboard`)
4. Setze ein sicheres Passwort
5. Unter **Berechtigungen** reicht es, folgendes zu aktivieren:
   - **Benutzerrechte:** `Beobachter` (oder „Viewer") – kein Schreibzugriff nötig
   - Zugriff auf **alle Räume** oder gezielt auf die Räume, die du anzeigen möchtest
6. In den **Netzwerkeinstellungen** des Miniservers: HTTP-Zugriff muss erlaubt sein (Standard: aktiv auf Port 80)

> MQ-UDP greift auf zwei Endpunkte zu:
> - `http://<miniserver>/data/LoxAPP3.json` – Struktur aller Steuerelemente
> - `http://<miniserver>/jdev/sps/io/<uuid>/state` – aktueller Wert eines Steuerelements

---

## 7. MQ-UDP installieren und starten

### Variante A: Docker (empfohlen)

```bash
docker run -d \
  --name mq-udp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e MQTT_BROKER=192.168.1.100 \
  -e MQTT_TOPIC=awtrix/custom/{uuid} \
  -e MQTT_USERNAME=mq-udp \
  -e MQTT_PASSWORD=<PASSWORT> \
  -e LOXONE_HOSTNAME=192.168.1.50 \
  -e LOXONE_USERNAME=mq-udp \
  -e LOXONE_PASSWORD=<PASSWORT> \
  -e AUTOMATIC_INTERVAL=60 \
  -v $(pwd)/data:/data \
  -e AUTO_CONFIG_PATH=/data/auto_config.json \
  ghcr.io/sonzions/mq-udp:latest
```

Oder selbst bauen:

```bash
git clone https://github.com/SonZions/MQ-UDP.git
cd MQ-UDP
docker build -t mq-udp .
docker run -d --name mq-udp --restart unless-stopped \
  -p 8000:8000 \
  -e MQTT_BROKER=192.168.1.100 \
  ...  # restliche Variablen wie oben
  -v $(pwd)/data:/data \
  mq-udp
```

### Variante B: Direkt mit Python

```bash
git clone https://github.com/SonZions/MQ-UDP.git
cd MQ-UDP
pip install -r requirements.txt

# Umgebungsvariablen setzen
export MQTT_BROKER=192.168.1.100
export MQTT_TOPIC="awtrix/custom/{uuid}"
export MQTT_USERNAME=mq-udp
export MQTT_PASSWORD=<PASSWORT>
export LOXONE_HOSTNAME=192.168.1.50
export LOXONE_USERNAME=mq-udp
export LOXONE_PASSWORD=<PASSWORT>
export AUTOMATIC_INTERVAL=60

python web_app.py
```

Die Weboberfläche ist danach unter `http://localhost:8000` erreichbar.

### Alle Umgebungsvariablen im Überblick

| Variable | Pflicht | Beschreibung | Standard |
|----------|---------|--------------|---------|
| `MQTT_BROKER` | Ja | IP oder Hostname des MQTT-Brokers | – |
| `MQTT_TOPIC` | Ja | Topic-Muster für AWTRIX, z. B. `awtrix/custom/{uuid}` | – |
| `MQTT_PORT` | Nein | Port des MQTT-Brokers | `1883` |
| `MQTT_USERNAME` | Nein | MQTT-Benutzername | – |
| `MQTT_PASSWORD` | Nein | MQTT-Passwort | – |
| `LOXONE_HOSTNAME` | Ja* | Hostname oder IP des Miniservers | – |
| `LOXONE_URL` | Ja* | Vollständige URL zur `LoxAPP3.json` (Alternative zu HOSTNAME) | – |
| `LOXONE_USERNAME` | Nein | Loxone-Benutzername | – |
| `LOXONE_PASSWORD` | Nein | Loxone-Passwort | – |
| `LOXONE_JSON_PATH` | Nein | Pfad zu einer lokalen JSON-Datei (Offline-Modus) | `json.txt` |
| `AUTOMATIC_INTERVAL` | Nein | Abfrageintervall in Sekunden | `60` |
| `AUTO_CONFIG_PATH` | Nein | Speicherort der Auswahl-Konfiguration | `auto_config.json` |
| `UDP_IP` | Nein | Ziel-IP für UDP-Weiterleitung | `127.0.0.1` |
| `UDP_PORT` | Nein | Ziel-Port für UDP-Weiterleitung | `5005` |

*Entweder `LOXONE_HOSTNAME` **oder** `LOXONE_URL` muss gesetzt sein.

---

## 8. Weboberfläche bedienen

Öffne `http://<HOST>:8000` in deinem Browser.

### Steuerelemente auswählen

Die Tabelle zeigt alle Loxone-Steuerelemente sortiert nach Raum. Für jedes Steuerelement kannst du:

| Spalte | Beschreibung |
|--------|-------------|
| **Aktiv** | Checkbox – wenn aktiv, wird der Wert regelmäßig an AWTRIX geschickt |
| **Icon-ID** | Numerische ID aus der [LaMetric Icon Gallery](https://developer.lametric.com/icons) |
| **Modus** | `App` (dauerhaft sichtbar) oder `Benachrichtigung` (kurz einblenden, dann weg) |

**App-Modus:** Das Steuerelement wird als permanente „Custom App" auf der AWTRIX angezeigt und rotiert mit anderen Apps.

**Benachrichtigungs-Modus:** Der Wert wird kurz als Benachrichtigung eingeblendet und danach nicht mehr angezeigt. Nützlich für Ereignisse wie „Fenster offen".

### Automatische Aktualisierung

Sobald mindestens ein Steuerelement aktiviert ist, läuft die Aktualisierung vollautomatisch:

1. Alle `AUTOMATIC_INTERVAL` Sekunden (Standard: 60 s) werden die aktuellen Werte bei Loxone abgefragt
2. Geänderte Werte werden sofort an AWTRIX geschickt
3. Im App-Modus wird jeder Wert spätestens alle 60 Sekunden erneut gesendet (damit AWTRIX die App nicht vergisst)
4. Deaktivierte Steuerelemente werden automatisch von der Uhr entfernt

---

## 9. Icons auf der AWTRIX

Icons werden über die [LaMetric Icon Gallery](https://developer.lametric.com/icons) ausgewählt. Jedes Icon hat eine numerische ID (z. B. `2056` für ein Thermometer).

### Icon auf der AWTRIX speichern

Das Icon muss einmalig auf die Uhr heruntergeladen werden, bevor es angezeigt werden kann:

1. Öffne `http://<AWTRIX_IP>` → **Icons**-Tab
2. Gib die Icon-ID ein und klicke auf **Download**

Alternativ kannst du eigene Icons (8×8 Pixel JPG oder bis 32×8 Pixel GIF) über den **Dateimanager** der AWTRIX-Weboberfläche hochladen.

### Icon in MQ-UDP eintragen

Trage in der Weboberfläche von MQ-UDP die Icon-ID in das Feld **Icon-ID** neben dem gewünschten Steuerelement ein. Wenn ein Icon gesetzt ist, wird auf der Uhr nur der Wert angezeigt (das Icon ersetzt den Namen des Steuerelements).

---

## 10. Referenzen

- [AWTRIX 3 – Offizielle Dokumentation](https://blueforcer.github.io/awtrix3)
- [AWTRIX Web-Flasher](https://my.awtrix.dev)
- [AWTRIX MQTT API](https://blueforcer.github.io/awtrix3/#/api)
- [LaMetric Icon Gallery](https://developer.lametric.com/icons)
- [Eclipse Mosquitto – MQTT Broker](https://mosquitto.org)
- [Loxone Miniserver HTTP API](https://www.loxone.com/dede/wp-content/uploads/sites/2/2022/01/1100_Communicating-with-the-Miniserver.pdf)
- [Ulanzi TC001 bei Amazon](https://www.amazon.de/s?k=Ulanzi+TC001) *(kein Affiliate-Link)*
