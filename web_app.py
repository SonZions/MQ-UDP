"""FastAPI application that renders the Loxone values as a HTML table."""
from __future__ import annotations

import argparse
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

try:  # pragma: no cover - optional dependency for HTTP access
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency for HTTP access
    requests = None  # type: ignore

from loxone_data import LoxoneDataFetcher, LoxoneDataSource

app = FastAPI(title="Loxone Controls Viewer")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@lru_cache()
def get_fetcher() -> LoxoneDataFetcher:
    source = LoxoneDataSource.from_env()
    return LoxoneDataFetcher(source=source)


@app.get("/", response_class=HTMLResponse)
def render_controls(
    request: Request,
    fetcher: LoxoneDataFetcher = Depends(get_fetcher),
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

    return templates.TemplateResponse(
        "controls.html",
        {
            "request": request,
            "controls": controls,
            "metadata": metadata,
        },
    )


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
