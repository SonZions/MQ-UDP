import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from auto_config import AutoConfigStore


def test_store_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    store = AutoConfigStore(config_path)

    assert store.as_mapping() == {}

    store.set_enabled("abc", True)
    store.set_enabled("def", False)

    reloaded = AutoConfigStore(config_path)
    assert reloaded.is_enabled("abc") is True
    assert reloaded.is_enabled("def") is False
    assert reloaded.enabled_ids() == {"abc"}


def test_store_sync(tmp_path: Path) -> None:
    store = AutoConfigStore(tmp_path / "config.json")
    store.set_enabled("keep", True)
    store.set_enabled("remove", True)

    store.sync_from(["keep"])

    assert store.is_enabled("keep") is True
    assert store.is_enabled("remove") is False


def test_icon_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    store = AutoConfigStore(config_path)

    assert store.get_icon("uuid-1") == ""

    store.set_icon("uuid-1", "2056")
    assert store.get_icon("uuid-1") == "2056"
    assert store.icons_mapping() == {"uuid-1": "2056"}

    reloaded = AutoConfigStore(config_path)
    assert reloaded.get_icon("uuid-1") == "2056"


def test_icon_removal(tmp_path: Path) -> None:
    store = AutoConfigStore(tmp_path / "config.json")
    store.set_icon("uuid-1", "2056")
    store.set_icon("uuid-1", "")

    assert store.get_icon("uuid-1") == ""
    assert "uuid-1" not in store.icons_mapping()


def test_icon_sync(tmp_path: Path) -> None:
    store = AutoConfigStore(tmp_path / "config.json")
    store.set_icon("keep", "100")
    store.set_icon("remove", "200")

    store.sync_from(["keep"])

    assert store.get_icon("keep") == "100"
    assert store.get_icon("remove") == ""
