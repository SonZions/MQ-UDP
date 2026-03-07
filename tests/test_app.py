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


def test_format_control_message_skips_error_state():
    """Error states should not appear in the formatted message."""
    control = ControlRow(
        uuid="uuid-wind",
        name="Windgeschwindigkeit",
        type="InfoOnlyAnalog",
        room="",
        category="",
        details=tuple(),
        states=(
            ("error", "err-uuid-1234-5678-abcdefabcdef"),
            ("value", "val-uuid-1234-5678-abcdefabcdef"),
        ),
        links=tuple(),
    )

    def resolver(candidate: str) -> str:
        if candidate.startswith("val-"):
            return "0.0km/h"
        return "Fehler bei Statusabfrage (url): error"

    message = app.format_control_message(control, resolver)
    parsed = json.loads(message)

    assert parsed == {"text": "Windgeschwindigkeit: 0.0km/h"}
    assert "Fehler" not in parsed["text"]


def test_format_control_message_with_icon():
    control = ControlRow(
        uuid="uuid-1",
        name="Temperatur",
        type="InfoOnlyAnalog",
        room="",
        category="",
        details=tuple(),
        states=(("value", "state-uuid"),),
        links=tuple(),
    )

    message = app.format_control_message(control, lambda _: "21.5°C", icon="2056")
    parsed = json.loads(message)

    assert parsed == {"text": "21.5°C", "icon": "2056"}


def test_format_control_message_without_icon():
    control = ControlRow(
        uuid="uuid-1",
        name="Temperatur",
        type="InfoOnlyAnalog",
        room="",
        category="",
        details=tuple(),
        states=(("value", "state-uuid"),),
        links=tuple(),
    )

    message = app.format_control_message(control, lambda _: "21.5°C")
    parsed = json.loads(message)

    assert parsed == {"text": "Temperatur: 21.5°C"}
    assert "icon" not in parsed


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


def test_resolve_notification_topic_replaces_custom():
    topic = app.resolve_notification_topic("awtrix/device/custom")
    assert topic == "awtrix/device/notify"


def test_resolve_notification_topic_strips_uuid_placeholder():
    topic = app.resolve_notification_topic("awtrix/device/custom/{uuid}")
    assert topic == "awtrix/device/notify"


def test_resolve_notification_topic_fallback():
    topic = app.resolve_notification_topic("some/topic")
    assert topic == "some/topic/notify"


def test_resolve_notification_topic_trailing_slash():
    topic = app.resolve_notification_topic("awtrix/device/custom/")
    assert topic == "awtrix/device/notify"


def test_automatic_mode_notification_publishes_to_notify_topic(monkeypatch):
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
                "name": "Temperatur",
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
    fetcher.resolve_state_value.return_value = "21°"
    fetcher_factory = MagicMock(return_value=fetcher)

    store = MagicMock()
    store.enabled_ids.side_effect = [
        {"uuid-123"},
        KeyboardInterrupt(),
    ]
    store.get_mode.return_value = "notification"
    store.get_icon.return_value = ""
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

    # Should publish to notify topic, not custom app topic
    assert (
        "awtrix/device/notify",
        json.dumps({"text": "Temperatur: 21°"}, ensure_ascii=False),
    ) in topics_messages
    # Must NOT publish to custom app topic
    assert not any(t == "awtrix/device/custom/uuid-123" for t, _ in topics_messages)


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
    store.get_mode.return_value = "app"
    store.get_icon.return_value = ""
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


def test_automatic_mode_app_skips_unchanged_value(monkeypatch):
    """App mode should not re-publish when the value hasn't changed."""
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
                "name": "Temperatur",
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
    fetcher.resolve_state_value.return_value = "21°"
    fetcher_factory = MagicMock(return_value=fetcher)

    call_count = [0]

    def enabled_ids_side_effect():
        call_count[0] += 1
        if call_count[0] <= 2:
            return {"uuid-123"}
        raise KeyboardInterrupt()

    store = MagicMock()
    store.enabled_ids.side_effect = enabled_ids_side_effect
    store.get_mode.return_value = "app"
    store.get_icon.return_value = ""
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

    # Value is the same in both cycles – should publish only once
    expected_msg = json.dumps({"text": "Temperatur: 21°"}, ensure_ascii=False)
    topic_messages = [call.args for call in client.publish.call_args_list]
    publish_count = topic_messages.count(("awtrix/device/custom/uuid-123", expected_msg))
    assert publish_count == 1


def test_automatic_mode_app_publishes_on_value_change(monkeypatch):
    """App mode should re-publish when the value changes."""
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
                "name": "Temperatur",
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

    values = iter(["21°", "22°"])

    def make_fetcher():
        f = MagicMock()
        f.load.return_value = payload
        f.resolve_state_value.return_value = next(values)
        return f

    call_count = [0]

    def enabled_ids_side_effect():
        call_count[0] += 1
        if call_count[0] <= 2:
            return {"uuid-123"}
        raise KeyboardInterrupt()

    store = MagicMock()
    store.enabled_ids.side_effect = enabled_ids_side_effect
    store.get_mode.return_value = "app"
    store.get_icon.return_value = ""
    store.sync_from.return_value = None

    client = MagicMock()
    monkeypatch.setattr(app, "create_mqtt_client", lambda *_: client)

    try:
        app.automatic_mode(
            config,
            store,
            make_fetcher,
            interval_override=0.0,
        )
    except KeyboardInterrupt:
        pass

    topic_messages = [call.args for call in client.publish.call_args_list]
    msg_21 = json.dumps({"text": "Temperatur: 21°"}, ensure_ascii=False)
    msg_22 = json.dumps({"text": "Temperatur: 22°"}, ensure_ascii=False)

    # Both values should be published since they differ
    assert ("awtrix/device/custom/uuid-123", msg_21) in topic_messages
    assert ("awtrix/device/custom/uuid-123", msg_22) in topic_messages
