"""FastAPI application that renders the Loxone values as a HTML table."""
from __future__ import annotations

import argparse
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

try:  # pragma: no cover - optional dependency for HTTP access
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency for HTTP access
    requests = None  # type: ignore

from auto_config import AutoConfigStore
from app import (
    Config,
    automatic_mode,
    config_from_env,
    create_mqtt_client,
    mqtt_to_udp,
    udp_to_mqtt,
)
from loxone_data import LoxoneDataFetcher, LoxoneDataSource

app = FastAPI(title="Loxone Controls Viewer")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
AUTO_CONFIG_PATH = Path(os.getenv("AUTO_CONFIG_PATH", "auto_config.json"))


class AutoConfigUpdate(BaseModel):
    enabled: bool


@lru_cache()
def get_fetcher() -> LoxoneDataFetcher:
    source = LoxoneDataSource.from_env()
    return LoxoneDataFetcher(source=source)


@lru_cache()
def get_auto_config_store() -> AutoConfigStore:
    return AutoConfigStore(AUTO_CONFIG_PATH)


@lru_cache()
def get_bridge_config() -> Config:
    return config_from_env()


@app.on_event("startup")
def start_bridge() -> None:
    try:
        config = get_bridge_config()
    except ValueError as exc:
        print(f"Bridge Konfiguration unvollständig: {exc}")
        return

    store = get_auto_config_store()
    fetcher = get_fetcher()

    publisher_client = create_mqtt_client(config)
    publisher_client.loop_start()

    threading.Thread(target=mqtt_to_udp, args=(config,), daemon=True).start()
    threading.Thread(
        target=udp_to_mqtt,
        args=(publisher_client, config),
        daemon=True,
    ).start()
    threading.Thread(
        target=automatic_mode,
        args=(config, store, lambda: fetcher),
        daemon=True,
    ).start()


@app.get("/", response_class=HTMLResponse)
def render_controls(
    request: Request,
    fetcher: LoxoneDataFetcher = Depends(get_fetcher),
    store: AutoConfigStore = Depends(get_auto_config_store),
) -> HTMLResponse:
    try:
        payload: Dict[str, object] = fetcher.load()
    except Exception as exc:
        if requests is not None and isinstance(exc, requests.RequestException):  # pragma: no cover - depends on network
            raise HTTPException(status_code=502, detail=f"Fehler beim Abruf der Daten: {exc}") from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    controls = fetcher.extract_controls(payload)
    metadata = {
        "last_modified": payload.get("lastModified"),
        "control_count": len(payload.get("controls", {})),
        "room_count": len(payload.get("rooms", {})),
        "category_count": len(payload.get("cats", {})),
    }

    store.sync_from(control.uuid for control in controls)

    return templates.TemplateResponse(
        "controls.html",
        {
            "request": request,
            "controls": controls,
            "metadata": metadata,
            "auto_config": store.as_mapping(),
        },
    )


@app.get("/api/auto-config")
def read_auto_config(store: AutoConfigStore = Depends(get_auto_config_store)) -> Dict[str, bool]:
    return store.as_mapping()


@app.post("/api/auto-config/{control_uuid}")
def update_auto_config(
    control_uuid: str,
    payload: AutoConfigUpdate,
    store: AutoConfigStore = Depends(get_auto_config_store),
):
    store.set_enabled(control_uuid, payload.enabled)
    return {"uuid": control_uuid, "enabled": store.is_enabled(control_uuid)}


def _default_host() -> str:
    return os.getenv("WEBAPP_HOST", "0.0.0.0")


def _default_port() -> int:
    try:
        return int(os.getenv("WEBAPP_PORT", "8000"))
    except ValueError:  # pragma: no cover - defensive programming for user input
        raise ValueError("WEBAPP_PORT muss eine ganze Zahl sein")


def main() -> None:
    parser = argparse.ArgumentParser(description="Starte die Loxone Webansicht.")
    parser.add_argument(
        "--host",
        default=_default_host(),
        help="Host, auf dem der Server lauschen soll (Standard: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_default_port(),
        help="Port, auf dem der Server lauschen soll (Standard: %(default)s)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Aktiviere Uvicorn Reload-Modus (nur für Entwicklung)",
    )
    args = parser.parse_args()

    uvicorn.run(
        "web_app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
