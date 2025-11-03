"""Persistent storage for the automatic publishing configuration."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Iterable, Set


class AutoConfigStore:
    """Store the enabled state of controls for the automatic mode."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._enabled: Dict[str, bool] = {}
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

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"enabled": self._enabled}
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

    def sync_from(self, uuids: Iterable[str]) -> None:
        """Ensure that only known UUIDs are present in the configuration."""

        with self._lock:
            known = set(str(uuid) for uuid in uuids)
            stale = set(self._enabled) - known
            if stale:
                for key in stale:
                    self._enabled.pop(key, None)
                self._save()
