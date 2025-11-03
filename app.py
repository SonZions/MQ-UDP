import argparse
import logging
import os
import socket
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import paho.mqtt.client as mqtt

from loxone_data import ControlRow, LoxoneDataFetcher


logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency for logging
    from typing import TYPE_CHECKING
except ImportError:  # pragma: no cover - Python < 3.8 compatibility guard
    TYPE_CHECKING = False

if TYPE_CHECKING:  # pragma: no cover - typing only
    from auto_config import AutoConfigStore


@dataclass
class Config:
    mqtt_broker: str
    mqtt_port: int
    mqtt_topic: str
    udp_ip: str
    udp_port: int
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    automatic_interval: float = 30.0


# Variable zur Verfolgung der gesendeten Nachrichten
sent_messages = set()

# Interne Ablage für Nachrichten, die lokal auf dem MQTT-Broker veröffentlicht
# wurden und daher nicht erneut verarbeitet werden sollen.
_published_messages: Dict[str, int] = defaultdict(int)
_published_lock = threading.Lock()


def reset_message_tracking() -> None:
    """Reset cached message tracking state (hauptsächlich für Tests)."""

    sent_messages.clear()
    with _published_lock:
        _published_messages.clear()


def record_local_mqtt_message(message: str) -> None:
    """Merke, dass eine Nachricht von dieser Anwendung veröffentlicht wurde."""

    with _published_lock:
        _published_messages[message] += 1


def should_ignore_mqtt_message(message: str) -> bool:
    """Prüfe, ob eine eingehende MQTT-Nachricht ignoriert werden sollte."""

    with _published_lock:
        count = _published_messages.get(message, 0)
        if not count:
            return False
        if count == 1:
            _published_messages.pop(message, None)
        else:
            _published_messages[message] = count - 1
        return True


def create_mqtt_client(config: Config) -> mqtt.Client:
    client = mqtt.Client()
    if config.mqtt_username or config.mqtt_password:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
    client.connect(config.mqtt_broker, config.mqtt_port, 60)
    return client


def send_udp_message(message: str, config: Config) -> None:
    """Sende eine Nachricht an das konfigurierte UDP-Ziel."""

    if message not in sent_messages:
        sent_messages.add(message)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (config.udp_ip, config.udp_port))
        logger.info(
            "Weitergeleitete MQTT-Nachricht – Topic: %s, Nachricht: %s",
            config.mqtt_topic,
            message,
        )
        print(f"UDP Nachricht gesendet: {message}")


def create_on_message(config: Config):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        print(f"MQTT Nachricht empfangen: {message}")
        if should_ignore_mqtt_message(message):
            return
        send_udp_message(message, config)

    return on_message


def mqtt_to_udp(config: Config) -> None:
    client = create_mqtt_client(config)
    client.on_message = create_on_message(config)
    client.subscribe(config.mqtt_topic)
    client.loop_forever()


def udp_to_mqtt(client: mqtt.Client, config: Config) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config.udp_ip, config.udp_port))
    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        print(f"UDP Nachricht empfangen: {message}")
        record_local_mqtt_message(message)
        client.publish(config.mqtt_topic, message)
        logger.info(
            "Veröffentlichte UDP-Nachricht – Topic: %s, Nachricht: %s",
            config.mqtt_topic,
            message,
        )


def parse_args(argv=None) -> Config:
    parser = argparse.ArgumentParser(description="MQTT <-> UDP Brücke")
    parser.add_argument("--mqtt-broker", required=True, help="MQTT Broker Adresse")
    parser.add_argument(
        "--mqtt-port", type=int, default=1883, help="MQTT Broker Port (Standard: 1883)"
    )
    parser.add_argument("--mqtt-topic", required=True, help="MQTT Topic")
    parser.add_argument(
        "--udp-ip", default="127.0.0.1", help="UDP Ziel-IP (Standard: 127.0.0.1)"
    )
    parser.add_argument(
        "--udp-port", type=int, default=5005, help="UDP Port (Standard: 5005)"
    )
    parser.add_argument("--mqtt-username", help="MQTT Benutzername", default=None)
    parser.add_argument("--mqtt-password", help="MQTT Passwort", default=None)
    parser.add_argument(
        "--automatic-interval",
        type=float,
        default=30.0,
        help="Intervall in Sekunden für den Automatikmodus (Standard: 30)",
    )

    args = parser.parse_args(argv)
    return Config(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_topic=args.mqtt_topic,
        udp_ip=args.udp_ip,
        udp_port=args.udp_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        automatic_interval=args.automatic_interval,
    )


def config_from_env() -> Config:
    """Build the bridge configuration based on environment variables."""

    broker = os.getenv("MQTT_BROKER")
    topic = os.getenv("MQTT_TOPIC")
    if not broker or not topic:
        raise ValueError("MQTT_BROKER und MQTT_TOPIC müssen gesetzt sein")

    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    udp_ip = os.getenv("UDP_IP", "127.0.0.1")
    udp_port = int(os.getenv("UDP_PORT", "5005"))
    automatic_interval = float(os.getenv("AUTOMATIC_INTERVAL", "30"))

    return Config(
        mqtt_broker=broker,
        mqtt_port=mqtt_port,
        mqtt_topic=topic,
        udp_ip=udp_ip,
        udp_port=udp_port,
        mqtt_username=os.getenv("MQTT_USERNAME") or None,
        mqtt_password=os.getenv("MQTT_PASSWORD") or None,
        automatic_interval=automatic_interval,
    )


def format_control_message(
    control: ControlRow,
    state_resolver: Optional[Callable[[str], Optional[str]]] = None,
) -> str:
    """Render a MQTT friendly payload for a control."""

    if control.states:
        rendered = []
        for key, value in control.states:
            if state_resolver:
                resolved = state_resolver(value)
                if resolved is not None:
                    value = resolved
            rendered.append(f"{key}: {value}")
        values = " | ".join(rendered)
    elif control.details:
        values = " | ".join(f"{key}: {value}" for key, value in control.details)
    else:
        values = "Keine Daten verfügbar"
    return f"{control.name} – {values}"


def resolve_target_topic(base: str, uuid: str) -> str:
    """Derive the target MQTT topic for an automatically published control."""

    if "{uuid}" in base:
        try:
            return base.format(uuid=uuid)
        except Exception:
            return base

    if base.endswith("/"):
        return f"{base}{uuid}"

    return base


def automatic_mode(
    config: Config,
    store: "AutoConfigStore",
    fetcher_factory: Callable[[], LoxoneDataFetcher],
    *,
    interval_override: Optional[float] = None,
) -> None:
    """Publish selected control values to MQTT based on the stored configuration."""

    client = create_mqtt_client(config)
    client.loop_start()
    fetch_failures = 0
    try:
        while True:
            enabled = store.enabled_ids()
            if not enabled:
                time.sleep(interval_override or config.automatic_interval)
                continue

            try:
                fetcher = fetcher_factory()
                payload = fetcher.load()
                controls = {
                    row.uuid: row
                    for row in LoxoneDataFetcher.extract_controls(payload)
                }
                store.sync_from(controls.keys())
                for uuid in enabled:
                    control = controls.get(uuid)
                    if not control:
                        continue
                    message = format_control_message(control, fetcher.resolve_state_value)
                    topic = resolve_target_topic(config.mqtt_topic, uuid)
                    record_local_mqtt_message(message)
                    client.publish(topic, message)
                    logger.info(
                        "Automatikmodus veröffentlichte Nachricht – Topic: %s, Nachricht: %s",
                        topic,
                        message,
                    )
                fetch_failures = 0
            except Exception as exc:  # pragma: no cover - defensive logging only
                fetch_failures += 1
                print(f"Automatikmodus Fehler ({fetch_failures}): {exc}")

            time.sleep(interval_override or config.automatic_interval)
    finally:
        client.loop_stop()
        client.disconnect()


def main(argv=None) -> None:
    config = parse_args(argv)
    publisher_client = create_mqtt_client(config)
    publisher_client.loop_start()

    mqtt_thread = threading.Thread(target=mqtt_to_udp, args=(config,))
    mqtt_thread.start()

    udp_thread = threading.Thread(target=udp_to_mqtt, args=(publisher_client, config))
    udp_thread.start()

    mqtt_thread.join()
    udp_thread.join()


if __name__ == "__main__":
    main()
