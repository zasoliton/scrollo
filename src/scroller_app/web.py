from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .models import AppConfig
from .services import DataCoordinator
from .state import SharedState

PACKAGE_ROOT = Path(__file__).resolve().parent


def create_app(state: SharedState, coordinator: DataCoordinator) -> FastAPI:
    app = FastAPI(title="Market Matrix Admin")
    templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))
    app.mount(
        "/static", StaticFiles(directory=str(PACKAGE_ROOT / "static")), name="static"
    )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        snapshot = state.snapshot()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "snapshot": snapshot,
                "config_json": json.dumps(snapshot.config.to_dict()),
            },
        )

    @app.get("/api/state")
    async def get_state() -> JSONResponse:
        return JSONResponse(state.snapshot().to_dict())

    @app.post("/api/config")
    async def save_config(request: Request) -> JSONResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Expected a JSON object.")

        current = state.get_config()
        merged = current.to_dict()
        merged.update(payload)

        if "theme" in payload and isinstance(payload["theme"], dict):
            theme = current.theme.to_dict()
            theme.update(payload["theme"])
            merged["theme"] = theme

        config = AppConfig.from_dict(merged)
        state.update_config(config)
        coordinator.request_refresh("all")
        return JSONResponse({"ok": True, "config": config.to_dict()})

    @app.post("/api/refresh")
    async def force_refresh(request: Request) -> JSONResponse:
        payload = await request.json()
        kind = str(payload.get("kind", "all"))
        if kind not in {"all", "stocks", "news"}:
            raise HTTPException(
                status_code=400, detail="kind must be one of: all, stocks, news"
            )
        coordinator.request_refresh(kind)
        return JSONResponse({"ok": True, "requested": kind})

    return app
