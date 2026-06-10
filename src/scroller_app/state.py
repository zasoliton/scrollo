from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from .config import ConfigStore
from .models import AppConfig, Headline, StockQuote


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class StateSnapshot:
    config: AppConfig
    quotes: list[StockQuote]
    headlines: list[Headline]
    last_stock_refresh: datetime | None
    last_news_refresh: datetime | None
    errors: dict[str, str]
    revision: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "quotes": [quote.to_dict() for quote in self.quotes],
            "headlines": [headline.to_dict() for headline in self.headlines],
            "last_stock_refresh": self.last_stock_refresh.isoformat()
            if self.last_stock_refresh
            else None,
            "last_news_refresh": self.last_news_refresh.isoformat()
            if self.last_news_refresh
            else None,
            "errors": dict(self.errors),
            "revision": self.revision,
        }


class SharedState:
    def __init__(self, config_store: ConfigStore) -> None:
        self._config_store = config_store
        self._lock = RLock()
        self._config = config_store.load()
        self._quotes: list[StockQuote] = []
        self._headlines: list[Headline] = []
        self._last_stock_refresh: datetime | None = None
        self._last_news_refresh: datetime | None = None
        self._errors: dict[str, str] = {}
        self._revision = 0

    def get_config(self) -> AppConfig:
        with self._lock:
            return copy.deepcopy(self._config)

    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return StateSnapshot(
                config=copy.deepcopy(self._config),
                quotes=copy.deepcopy(self._quotes),
                headlines=copy.deepcopy(self._headlines),
                last_stock_refresh=self._last_stock_refresh,
                last_news_refresh=self._last_news_refresh,
                errors=dict(self._errors),
                revision=self._revision,
            )

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            self._config_store.save(config)
            self._config = copy.deepcopy(config)
            self._revision += 1

    def update_quotes(self, quotes: list[StockQuote]) -> None:
        with self._lock:
            self._quotes = copy.deepcopy(quotes)
            self._last_stock_refresh = _utc_now()
            self._errors.pop("stocks", None)
            self._revision += 1

    def update_headlines(self, headlines: list[Headline]) -> None:
        with self._lock:
            self._headlines = copy.deepcopy(headlines)
            self._last_news_refresh = _utc_now()
            self._errors.pop("news", None)
            self._revision += 1

    def set_error(self, key: str, message: str) -> None:
        with self._lock:
            self._errors[key] = message
            self._revision += 1
