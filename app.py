import argparse
from dataclasses import dataclass
import socket
import threading
from typing import Optional

import paho.mqtt.client as mqtt


@dataclass
class Config:
    mqtt_broker: str
    mqtt_port: int
    mqtt_topic: str
    udp_ip: str
    udp_port: int
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None


# Variable zur Verfolgung der gesendeten Nachrichten
sent_messages = set()


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
        print(f"UDP Nachricht gesendet: {message}")


def create_on_message(config: Config):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        print(f"MQTT Nachricht empfangen: {message}")
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
        client.publish(config.mqtt_topic, message)


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

    args = parser.parse_args(argv)
    return Config(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_topic=args.mqtt_topic,
        udp_ip=args.udp_ip,
        udp_port=args.udp_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
    )


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
