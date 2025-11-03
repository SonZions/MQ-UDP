import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

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


def test_data_source_from_env_derives_template(monkeypatch):
    monkeypatch.setenv("LOXONE_URL", "http://miniserver.local/data/LoxAPP3.json")
    monkeypatch.delenv("LOXONE_STATE_URL_TEMPLATE", raising=False)

    source = LoxoneDataSource.from_env()

    assert source.state_url_template == "http://miniserver.local/dev/sps/io/{uuid}"


def test_resolve_state_value_fetches_and_caches(monkeypatch):
    source = LoxoneDataSource(state_url_template="http://host/dev/sps/io/{uuid}")
    fetcher = LoxoneDataFetcher(source)

    response = MagicMock()
    response.json.return_value = {"value": 48.7}
    response.text = "48.7"
    response.raise_for_status.return_value = None

    mock_requests = MagicMock()
    mock_requests.get.return_value = response

    monkeypatch.setitem(sys.modules, "requests", mock_requests)

    uuid = "01234567-89ab-cdef-0123-456789abcdef"

    first = fetcher.resolve_state_value(uuid)
    second = fetcher.resolve_state_value(uuid)

    assert first == "48.7"
    assert second == "48.7"
    mock_requests.get.assert_called_once_with(
        "http://host/dev/sps/io/01234567-89ab-cdef-0123-456789abcdef",
        auth=source.auth,
        timeout=fetcher.timeout,
    )


def test_resolve_state_value_handles_ll_payload(monkeypatch):
    source = LoxoneDataSource(state_url_template="http://host/dev/sps/io/{uuid}")
    fetcher = LoxoneDataFetcher(source)

    response = MagicMock()
    response.json.return_value = {"LL": {"value": 72.5, "Code": 200}}
    response.text = "{\"LL\":{\"value\":72.5}}"
    response.raise_for_status.return_value = None

    mock_requests = MagicMock()
    mock_requests.get.return_value = response

    monkeypatch.setitem(sys.modules, "requests", mock_requests)

    uuid = "89abcdef-0123-4567-89ab-cdef01234567"

    result = fetcher.resolve_state_value(uuid)

    assert result == "72.5"
