"""Utilities for loading and presenting data from a Loxone Miniserver."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse, urlunparse


@dataclass
class LoxoneDataSource:
    """Configuration describing where the JSON payload can be loaded from."""

    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    json_path: Optional[Path] = None
    state_url_template: Optional[str] = None

    @property
    def auth(self) -> Optional[Tuple[str, str]]:
        """Return HTTP basic auth credentials if available."""

        if self.username or self.password:
            return (self.username or "", self.password or "")
        return None

    @classmethod
    def from_env(cls) -> "LoxoneDataSource":
        """Create a data source based on environment variables.

        The following variables are supported:
            LOXONE_URL:        Optional URL to the LoxAPP3.json endpoint.
            LOXONE_USERNAME:   Optional username for HTTP basic authentication.
            LOXONE_PASSWORD:   Optional password for HTTP basic authentication.
            LOXONE_JSON_PATH:  Optional fallback path to a local JSON file.
        """

        path_value = os.getenv("LOXONE_JSON_PATH", "json.txt")
        json_path = Path(path_value) if path_value else None
        url = os.getenv("LOXONE_URL") or None
        template = os.getenv("LOXONE_STATE_URL_TEMPLATE") or None
        if not template and url:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
                template = f"{base}/dev/sps/io/{{uuid}}"

        return cls(
            url=url,
            username=os.getenv("LOXONE_USERNAME") or None,
            password=os.getenv("LOXONE_PASSWORD") or None,
            json_path=json_path,
            state_url_template=template,
        )


@dataclass
class ControlRow:
    """Flattened representation of a single control entry."""

    uuid: str
    name: str
    type: str
    room: str
    category: str
    details: Sequence[Tuple[str, str]]
    states: Sequence[Tuple[str, str]]
    links: Sequence[str]


class LoxoneDataFetcher:
    """Load and normalise data returned by the Loxone Miniserver."""

    def __init__(self, source: LoxoneDataSource, timeout: float = 10.0):
        self.source = source
        self.timeout = timeout
        self._state_cache: Dict[str, Optional[str]] = {}

    def load(self) -> Dict[str, Any]:
        """Load JSON data either from the configured URL or the local file."""

        if self.source.url:
            try:
                import requests  # type: ignore
            except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "Zum Abrufen per HTTP wird das 'requests'-Paket benötigt."
                ) from exc

            response = requests.get(
                self.source.url,
                auth=self.source.auth,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        if not self.source.json_path:
            raise FileNotFoundError("No local JSON path configured and no URL provided")

        path = self.source.json_path
        if not path.is_absolute():
            path = (Path(__file__).resolve().parent / path).resolve()

        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def resolve_state_value(self, candidate: str) -> Optional[str]:
        """Resolve a state UUID to its current value using the Miniserver API."""

        if not candidate or not isinstance(candidate, str):
            return None

        if candidate in self._state_cache:
            return self._state_cache[candidate]

        template = self.source.state_url_template
        if not template or not _UUID_PATTERN.fullmatch(candidate):
            self._state_cache[candidate] = None
            return None

        url = template.format(uuid=candidate)
        try:
            import requests  # type: ignore
        except ModuleNotFoundError as exc:
            message = f"Fehler bei Statusabfrage ({url}): {exc}"
            self._state_cache[candidate] = message
            return message
        try:
            response = requests.get(
                url,
                auth=self.source.auth,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception as exc:
            message = f"Fehler bei Statusabfrage ({url}): {exc}"
            self._state_cache[candidate] = message
            return message

        value: Any
        try:
            data = response.json()
        except ValueError:
            extracted: Any = response.text.strip()
        else:
            extracted = _extract_state_payload(data)
            if extracted is None:
                extracted = response.text.strip()

        if isinstance(extracted, (dict, list)):
            extracted = json.dumps(extracted, ensure_ascii=False)

        resolved = str(extracted)
        self._state_cache[candidate] = resolved
        return resolved

    @staticmethod
    def extract_controls(data: Dict[str, Any]) -> List[ControlRow]:
        """Transform the controls payload into table friendly rows."""

        rooms = data.get("rooms", {})
        categories = data.get("cats", {})
        room_lookup = _build_lookup(rooms, default_label="Raum unbekannt")
        category_lookup = _build_lookup(categories, default_label="Kategorie unbekannt")

        controls = data.get("controls", {})
        rows: List[ControlRow] = []
        for uuid, control in controls.items():
            row = ControlRow(
                uuid=uuid,
                name=str(control.get("name", "")),
                type=str(control.get("type", "")),
                room=room_lookup.get(control.get("room"), ""),
                category=category_lookup.get(control.get("cat"), ""),
                details=_flatten_mapping(control.get("details")),
                states=_flatten_mapping(control.get("states")),
                links=tuple(str(link) for link in control.get("links", []) if link),
            )
            rows.append(row)

        rows.sort(key=lambda item: (item.room.lower(), item.name.lower(), item.uuid))
        return rows


def _build_lookup(entries: Dict[str, Dict[str, Any]], default_label: str) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for key, payload in entries.items():
        name = payload.get("name") if isinstance(payload, dict) else None
        lookup[key] = str(name) if name is not None else default_label
    return lookup


def _extract_state_payload(payload: Any) -> Optional[Any]:
    """Extract the scalar value from a Loxone state response payload."""

    if isinstance(payload, dict):
        for key in ("value", "val", "state"):
            if key in payload:
                candidate = payload[key]
                if isinstance(candidate, (dict, list)):
                    return _extract_state_payload(candidate)
                return candidate

        nested = payload.get("LL")
        if nested is not None:
            return _extract_state_payload(nested)

        # Fall back to the first scalar entry in the dict, if any.
        for item in payload.values():
            result = _extract_state_payload(item)
            if result is not None:
                return result
        return payload

    if isinstance(payload, (list, tuple)):
        for item in payload:
            result = _extract_state_payload(item)
            if result is not None:
                return result
        return payload

    return payload


def _flatten_mapping(mapping: Optional[Dict[str, Any]]) -> Tuple[Tuple[str, str], ...]:
    if not mapping:
        return tuple()

    flattened: List[Tuple[str, str]] = []
    for key, value in mapping.items():
        flattened.append((str(key), _stringify(value)))

    flattened.sort(key=lambda item: item[0].lower())
    return tuple(flattened)


def _stringify(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_stringify(item) for item in value)
    if isinstance(value, dict):
        inner = ", ".join(f"{_stringify(k)}: {_stringify(v)}" for k, v in value.items())
        return f"{{{inner}}}"
    return str(value)


_UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")
