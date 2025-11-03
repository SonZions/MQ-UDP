from pathlib import Path

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
