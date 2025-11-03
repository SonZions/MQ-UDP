from pathlib import Path

import pytest

from loxone_data import ControlRow, LoxoneDataFetcher, LoxoneDataSource


@pytest.fixture()
def sample_payload(tmp_path: Path) -> Path:
    payload = {
        "lastModified": "2024-01-01T00:00:00Z",
        "rooms": {
            "room-1": {"uuid": "room-1", "name": "Wohnzimmer"},
        },
        "cats": {
            "cat-1": {"uuid": "cat-1", "name": "Licht"},
        },
        "controls": {
            "uuid-1": {
                "name": "Deckenlicht",
                "type": "Switch",
                "room": "room-1",
                "cat": "cat-1",
                "details": {"format": "%.0f %%", "unit": "percent"},
                "states": {"active": "on", "inactive": "off"},
                "links": ["uuid-2"],
            },
            "uuid-3": {
                "name": "Fenster",
                "type": "Info",
                "room": "room-2",
                "cat": "cat-2",
            },
        },
    }
    file_path = tmp_path / "lox.json"
    file_path.write_text(__import__("json").dumps(payload))
    return file_path


def test_loads_from_local_file(sample_payload: Path) -> None:
    source = LoxoneDataSource(json_path=sample_payload)
    fetcher = LoxoneDataFetcher(source)

    data = fetcher.load()

    assert data["lastModified"] == "2024-01-01T00:00:00Z"
    assert "controls" in data


def test_extract_controls_creates_rows(sample_payload: Path) -> None:
    source = LoxoneDataSource(json_path=sample_payload)
    fetcher = LoxoneDataFetcher(source)
    payload = fetcher.load()

    rows = fetcher.extract_controls(payload)

    assert isinstance(rows, list)
    assert len(rows) == 2
    assert isinstance(rows[0], ControlRow)

    first = next(row for row in rows if row.uuid == "uuid-1")
    assert first.room == "Wohnzimmer"
    assert ("format", "%.0f %%") in first.details
    assert ("active", "on") in first.states
    assert first.links == ("uuid-2",)

    second = next(row for row in rows if row.uuid == "uuid-3")
    assert second.room == ""
    assert second.category == ""
    assert second.details == tuple()
