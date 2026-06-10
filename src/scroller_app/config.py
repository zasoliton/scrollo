from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import AppConfig

LOGGER = logging.getLogger(__name__)


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig()
            self.save(config)
            return config

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning(
                "Config file %s is invalid JSON; resetting to defaults.", self.path
            )
            config = AppConfig()
            self.save(config)
            return config

        return AppConfig.from_dict(raw)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(config.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
