import json
import sys
from pathlib import Path
import types
from unittest.mock import MagicMock, patch

# Füge den Projektstamm zum Python-Pfad hinzu
sys.path.append(str(Path(__file__).resolve().parents[1]))

from loxone_data import ControlRow

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

TEST_CONFIG = app.Config(
    mqtt_broker="broker",
    mqtt_port=1883,
    mqtt_topic="topic",
    udp_ip="127.0.0.1",
    udp_port=5005,
)


def setup_function(function):
    app.reset_message_tracking()


def test_send_udp_message_sends_only_once():
    with patch.object(app.socket, "socket") as mock_socket:
        socket_instance = mock_socket.return_value

        app.send_udp_message("hello", TEST_CONFIG)

        socket_instance.sendto.assert_called_once_with(
            "hello".encode(), (TEST_CONFIG.udp_ip, TEST_CONFIG.udp_port)
        )
        assert "hello" in app.sent_messages

        app.send_udp_message("hello", TEST_CONFIG)

        socket_instance.sendto.assert_called_once()


def test_on_message_forwards_payload_to_udp():
    with patch("app.send_udp_message") as mock_send_udp_message:
        mqtt_message = types.SimpleNamespace(payload=b"payload")

        on_message = app.create_on_message(TEST_CONFIG)

        on_message(client=MagicMock(), userdata=None, msg=mqtt_message)

        mock_send_udp_message.assert_called_once_with("payload", TEST_CONFIG)


def test_on_message_ignores_locally_published_messages():
    app.record_local_mqtt_message("payload")

    with patch("app.send_udp_message") as mock_send_udp_message:
        mqtt_message = types.SimpleNamespace(payload=b"payload")

        on_message = app.create_on_message(TEST_CONFIG)

        on_message(client=MagicMock(), userdata=None, msg=mqtt_message)

        mock_send_udp_message.assert_not_called()


def test_format_control_message_uses_state_resolver():
    control = ControlRow(
        uuid="uuid-1",
        name="Sensor",
        type="InfoOnlyDigital",
        room="",
        category="",
        details=tuple(),
        states=(("value", "01234567-89ab-cdef-0123-456789abcdef"),),
        links=tuple(),
    )

    def resolver(candidate: str) -> str:
        return "43" if candidate.startswith("0123") else None

    message = app.format_control_message(control, resolver)

    assert json.loads(message) == {"text": "Sensor: 43"}


def test_format_control_message_falls_back_to_details():
    control = ControlRow(
        uuid="uuid-2",
        name="Info",
        type="Text",
        room="",
        category="",
        details=(("status", "aktiv"),),
        states=tuple(),
        links=tuple(),
    )

    message = app.format_control_message(control, None)

    assert json.loads(message) == {"text": "Info: status: aktiv"}


def test_resolve_target_topic_defaults_to_base():
    assert app.resolve_target_topic("awtrix/device/custom", "uuid") == "awtrix/device/custom/uuid"


def test_resolve_target_topic_formats_placeholder():
    topic = app.resolve_target_topic("bridge/{uuid}/state", "abc-123")
    assert topic == "bridge/abc-123/state"


def test_resolve_target_topic_appends_on_trailing_slash():
    topic = app.resolve_target_topic("sensors/", "xyz")
    assert topic == "sensors/xyz"


def test_automatic_mode_publishes_clear_message_when_disabled(monkeypatch):
    config = app.Config(
        mqtt_broker="broker",
        mqtt_port=1883,
        mqtt_topic="awtrix/device/custom",
        udp_ip="127.0.0.1",
        udp_port=5005,
    )

    payload = {
        "controls": {
            "uuid-123": {
                "name": "Speichertemperatur",
                "type": "InfoOnlyAnalog",
                "room": "",
                "cat": "",
                "states": {"value": "state-uuid"},
                "links": [],
            }
        },
        "rooms": {},
        "cats": {},
    }

    fetcher = MagicMock()
    fetcher.load.return_value = payload
    fetcher.resolve_state_value.return_value = "59°"
    fetcher_factory = MagicMock(return_value=fetcher)

    store = MagicMock()
    store.enabled_ids.side_effect = [
        {"uuid-123"},
        set(),
        KeyboardInterrupt(),
    ]
    store.sync_from.return_value = None

    client = MagicMock()
    monkeypatch.setattr(app, "create_mqtt_client", lambda *_: client)

    try:
        app.automatic_mode(
            config,
            store,
            fetcher_factory,
            interval_override=0.0,
        )
    except KeyboardInterrupt:
        pass

    topics_messages = [call.args for call in client.publish.call_args_list]

    assert (
        "awtrix/device/custom/uuid-123",
        json.dumps({"text": "Speichertemperatur: 59°"}, ensure_ascii=False),
    ) in topics_messages
    assert ("awtrix/device/custom/uuid-123", "{}") in topics_messages
