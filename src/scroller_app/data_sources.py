from __future__ import annotations

import html
import logging
import re
from collections.abc import Callable, Iterable

import feedparser
import requests

from .models import FeedConfig, Headline, StockQuote

LOGGER = logging.getLogger(__name__)

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
STOCKPRICES_STOCK_URL = "https://stockprices.dev/api/stocks/{symbol}"
STOCKPRICES_ETF_URL = "https://stockprices.dev/api/etfs/{symbol}"
USER_AGENT = "MarketMatrixScroller/0.1 (+https://localhost)"


class StockQuoteService:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_quotes(self, symbols: list[str]) -> list[StockQuote]:
        if not symbols:
            return []

        fetch_attempts: list[tuple[str, Callable[[list[str]], list[StockQuote]]]] = [
            ("Yahoo Finance", self._fetch_quotes_yahoo),
            ("stockprices.dev", self._fetch_quotes_stockprices),
        ]
        last_error: Exception | None = None

        for index, (provider_name, fetcher) in enumerate(fetch_attempts):
            try:
                quotes = fetcher(symbols)
            except Exception as exc:
                last_error = exc
                if index < len(fetch_attempts) - 1:
                    LOGGER.warning(
                        "%s quote lookup failed; falling back to the next provider: %s",
                        provider_name,
                        exc,
                    )
                    continue
                raise

            if any(quote.price is not None for quote in quotes):
                return quotes

            if index < len(fetch_attempts) - 1:
                LOGGER.warning(
                    "%s returned no quote prices; falling back to the next provider.",
                    provider_name,
                )

        if last_error is not None:
            raise last_error
        return [StockQuote(symbol=symbol) for symbol in symbols]

    def _fetch_quotes_yahoo(self, symbols: list[str]) -> list[StockQuote]:
        response = self.session.get(
            YAHOO_QUOTE_URL,
            params={"symbols": ",".join(symbols)},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("quoteResponse", {}).get("result", [])

        by_symbol: dict[str, StockQuote] = {}
        for item in results:
            symbol = str(item.get("symbol", "")).upper()
            if not symbol:
                continue
            by_symbol[symbol] = StockQuote(
                symbol=symbol,
                price=_coerce_optional_float(item.get("regularMarketPrice")),
                change_percent=_coerce_optional_float(
                    item.get("regularMarketChangePercent")
                ),
                currency=str(item.get("currency", "USD")),
                market_state=str(item.get("marketState", "")),
            )

        return [by_symbol.get(symbol, StockQuote(symbol=symbol)) for symbol in symbols]

    def _fetch_quotes_stockprices(self, symbols: list[str]) -> list[StockQuote]:
        quotes = [self._fetch_stockprices_symbol(symbol) for symbol in symbols]
        if not any(quote.price is not None for quote in quotes):
            raise RuntimeError("Fallback quote provider returned no price data.")
        return quotes

    def _fetch_stockprices_symbol(self, symbol: str) -> StockQuote:
        for template in (STOCKPRICES_STOCK_URL, STOCKPRICES_ETF_URL):
            response = self.session.get(template.format(symbol=symbol), timeout=10)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            return StockQuote(
                symbol=str(payload.get("Ticker", symbol)).upper(),
                price=_coerce_optional_float(payload.get("Price")),
                change_percent=_coerce_optional_float(payload.get("ChangePercentage")),
                currency="USD",
            )

        return StockQuote(symbol=symbol)


class NewsFeedService:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_headlines(
        self, feeds: Iterable[FeedConfig], per_feed_limit: int
    ) -> list[Headline]:
        headlines: list[Headline] = []
        seen: set[str] = set()

        for feed in feeds:
            if not feed.enabled:
                continue

            try:
                response = self.session.get(feed.url, timeout=10)
                response.raise_for_status()
            except requests.RequestException as exc:
                LOGGER.warning("Feed request failed for %s: %s", feed.url, exc)
                continue

            parsed = feedparser.parse(response.content)
            source_name = feed.name or str(parsed.feed.get("title", "Feed"))

            if getattr(parsed, "bozo", False) and not parsed.entries:
                LOGGER.warning(
                    "Feed parse issue for %s: %s",
                    feed.url,
                    getattr(parsed, "bozo_exception", "unknown"),
                )
                continue

            for entry in parsed.entries[:per_feed_limit]:
                title = _clean_text(entry.get("title", ""))
                if not title:
                    continue
                key = title.casefold()
                if key in seen:
                    continue
                seen.add(key)
                headlines.append(
                    Headline(
                        source=source_name,
                        title=title,
                        link=str(entry.get("link", "")),
                    )
                )

        return headlines


def _clean_text(text: str) -> str:
    decoded = html.unescape(str(text))
    return re.sub(r"\s+", " ", decoded).strip()


def _coerce_optional_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
