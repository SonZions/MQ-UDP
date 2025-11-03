import sys
from pathlib import Path
import types
from unittest.mock import MagicMock, patch

# Füge den Projektstamm zum Python-Pfad hinzu
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Erstelle Dummy-Module für paho.mqtt.client, damit die Tests ohne externe Abhängigkeiten laufen
paho_module = types.ModuleType("paho")
paho_module.__path__ = []
mqtt_module = types.ModuleType("paho.mqtt")
mqtt_module.__path__ = []
client_module = types.ModuleType("paho.mqtt.client")


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.on_message = None

    def connect(self, *args, **kwargs):
        pass

    def subscribe(self, *args, **kwargs):
        pass

    def loop_forever(self):
        pass

    def loop_start(self):
        pass

    def publish(self, *args, **kwargs):
        pass


client_module.Client = DummyClient
paho_module.mqtt = mqtt_module
mqtt_module.client = client_module
sys.modules["paho"] = paho_module
sys.modules["paho.mqtt"] = mqtt_module
sys.modules["paho.mqtt.client"] = client_module

import app


def setup_function(function):
    app.sent_messages.clear()


def test_send_udp_message_sends_only_once():
    with patch.object(app.socket, "socket") as mock_socket:
        socket_instance = mock_socket.return_value

        app.send_udp_message("hello")

        socket_instance.sendto.assert_called_once_with(
            "hello".encode(), (app.UDP_IP, app.UDP_PORT)
        )
        assert "hello" in app.sent_messages

        app.send_udp_message("hello")

        socket_instance.sendto.assert_called_once()


def test_on_message_forwards_payload_to_udp():
    with patch("app.send_udp_message") as mock_send_udp_message:
        mqtt_message = types.SimpleNamespace(payload=b"payload")

        app.on_message(client=MagicMock(), userdata=None, msg=mqtt_message)

        mock_send_udp_message.assert_called_once_with("payload")
