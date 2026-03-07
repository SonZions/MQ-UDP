"""Persistent storage for the automatic publishing configuration."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Iterable, Set


VALID_MODES = ("app", "notification")


class AutoConfigStore:
    """Store the enabled state and display mode of controls for the automatic mode."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._enabled: Dict[str, bool] = {}
        self._modes: Dict[str, str] = {}
        self._icons: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Wenn die Datei beschädigt ist, ignorieren wir sie und starten frisch.
            return

        enabled = raw.get("enabled") if isinstance(raw, dict) else None
        if isinstance(enabled, dict):
            # Sicherstellen, dass nur boolesche Werte gespeichert werden.
            cleaned = {str(key): bool(value) for key, value in enabled.items()}
            self._enabled.update(cleaned)

        modes = raw.get("modes") if isinstance(raw, dict) else None
        if isinstance(modes, dict):
            cleaned = {
                str(key): str(value)
                for key, value in modes.items()
                if str(value) in VALID_MODES
            }
            self._modes.update(cleaned)

        icons = raw.get("icons") if isinstance(raw, dict) else None
        if isinstance(icons, dict):
            self._icons.update({str(k): str(v) for k, v in icons.items()})

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"enabled": self._enabled, "modes": self._modes, "icons": self._icons}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def as_mapping(self) -> Dict[str, bool]:
        with self._lock:
            return dict(self._enabled)

    def set_enabled(self, uuid: str, enabled: bool) -> None:
        with self._lock:
            self._enabled[str(uuid)] = bool(enabled)
            self._save()

    def is_enabled(self, uuid: str) -> bool:
        with self._lock:
            return bool(self._enabled.get(str(uuid)))

    def enabled_ids(self) -> Set[str]:
        with self._lock:
            return {uuid for uuid, enabled in self._enabled.items() if enabled}

    def get_mode(self, uuid: str) -> str:
        with self._lock:
            return self._modes.get(str(uuid), "app")

    def set_mode(self, uuid: str, mode: str) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Ungültiger Modus: {mode}")
        with self._lock:
            self._modes[str(uuid)] = mode
            self._save()

    def modes_mapping(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._modes)

    def get_icon(self, uuid: str) -> str:
        with self._lock:
            return self._icons.get(str(uuid), "")

    def set_icon(self, uuid: str, icon: str) -> None:
        with self._lock:
            if icon:
                self._icons[str(uuid)] = str(icon)
            else:
                self._icons.pop(str(uuid), None)
            self._save()

    def icons_mapping(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._icons)

    def sync_from(self, uuids: Iterable[str]) -> None:
        """Ensure that only known UUIDs are present in the configuration."""

        with self._lock:
            known = set(str(uuid) for uuid in uuids)
            stale_enabled = set(self._enabled) - known
            stale_modes = set(self._modes) - known
            stale_icons = set(self._icons) - known
            if stale_enabled or stale_modes or stale_icons:
                for key in stale_enabled:
                    self._enabled.pop(key, None)
                for key in stale_modes:
                    self._modes.pop(key, None)
                for key in stale_icons:
                    self._icons.pop(key, None)
                self._save()
