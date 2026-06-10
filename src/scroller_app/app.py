from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path

import uvicorn

from .config import ConfigStore
from .renderer import Hub75Renderer
from .services import DataCoordinator
from .state import SharedState
from .web import create_app

LOGGER = logging.getLogger(__name__)


class WebServerThread:
    def __init__(self, state: SharedState, coordinator: DataCoordinator) -> None:
        config = state.get_config()
        self._server = uvicorn.Server(
            uvicorn.Config(
                create_app(state, coordinator),
                host=config.web_host,
                port=config.web_port,
                log_level="info",
            )
        )
        self._thread = threading.Thread(
            target=self._run, name="web-server", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, join_timeout: float = 5.0) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=join_timeout)

    def _run(self) -> None:
        asyncio.run(self._server.serve())


def _build_config_store() -> ConfigStore:
    config_path = os.environ.get("SCROLLER_CONFIG_PATH")
    path = Path(config_path) if config_path else Path.cwd() / "data" / "settings.json"
    return ConfigStore(path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    stop_event = threading.Event()
    state = SharedState(_build_config_store())
    coordinator = DataCoordinator(state=state, stop_event=stop_event)
    web_server = WebServerThread(state=state, coordinator=coordinator)
    renderer = Hub75Renderer(state=state, stop_event=stop_event)

    LOGGER.info(
        "Starting Market Matrix. Web admin will be served on port %s",
        state.get_config().web_port,
    )

    try:
        coordinator.start()
        web_server.start()
        renderer.run()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down from keyboard interrupt")
    finally:
        stop_event.set()
        coordinator.stop()
        web_server.stop()
