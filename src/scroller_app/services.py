from __future__ import annotations

import logging
import threading
import time

from .data_sources import NewsFeedService, StockQuoteService
from .state import SharedState

LOGGER = logging.getLogger(__name__)


class DataCoordinator:
    def __init__(
        self,
        state: SharedState,
        stop_event: threading.Event,
        stock_service: StockQuoteService | None = None,
        news_service: NewsFeedService | None = None,
    ) -> None:
        self.state = state
        self.stop_event = stop_event
        self.stock_service = stock_service or StockQuoteService()
        self.news_service = news_service or NewsFeedService()
        self._wake_event = threading.Event()
        self._pending_stocks = True
        self._pending_news = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run, name="data-coordinator", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, join_timeout: float = 5.0) -> None:
        self.stop_event.set()
        self._wake_event.set()
        self._thread.join(timeout=join_timeout)

    def request_refresh(self, kind: str = "all") -> None:
        with self._lock:
            if kind in {"all", "stocks"}:
                self._pending_stocks = True
            if kind in {"all", "news"}:
                self._pending_news = True
        self._wake_event.set()

    def _run(self) -> None:
        next_stock = 0.0
        next_news = 0.0

        while not self.stop_event.is_set():
            config = self.state.get_config()
            now = time.monotonic()

            with self._lock:
                run_stocks = self._pending_stocks or now >= next_stock
                run_news = self._pending_news or now >= next_news
                self._pending_stocks = False
                self._pending_news = False

            if run_stocks:
                self._refresh_stocks()
                next_stock = time.monotonic() + config.stock_refresh_seconds

            if run_news:
                self._refresh_news()
                next_news = time.monotonic() + config.news_refresh_seconds

            now = time.monotonic()
            timeout = min(
                max(0.5, next_stock - now),
                max(0.5, next_news - now),
            )
            self._wake_event.wait(timeout)
            self._wake_event.clear()

    def _refresh_stocks(self) -> None:
        config = self.state.get_config()
        try:
            quotes = self.stock_service.fetch_quotes(config.stocks)
        except Exception as exc:  # pragma: no cover - defensive runtime logging
            LOGGER.exception("Failed to refresh stocks")
            self.state.set_error("stocks", str(exc))
            return

        self.state.update_quotes(quotes)

    def _refresh_news(self) -> None:
        config = self.state.get_config()
        try:
            headlines = self.news_service.fetch_headlines(
                config.feeds, config.news_items_per_feed
            )
        except Exception as exc:  # pragma: no cover - defensive runtime logging
            LOGGER.exception("Failed to refresh news")
            self.state.set_error("news", str(exc))
            return

        self.state.update_headlines(headlines)
