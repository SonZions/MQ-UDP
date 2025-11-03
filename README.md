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
