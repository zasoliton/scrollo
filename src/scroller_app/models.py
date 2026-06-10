from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _coerce_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _coerce_float(value: Any, default: float, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _normalize_symbol_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    items = raw.replace("\n", ",").split(",") if isinstance(raw, str) else list(raw)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        symbol = str(item).strip().upper()
        if not symbol or symbol in seen:
            continue
        normalized.append(symbol)
        seen.add(symbol)
    return normalized


@dataclass(slots=True)
class FeedConfig:
    name: str
    url: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedConfig:
        return cls(
            name=str(data.get("name", "")).strip() or "Feed",
            url=str(data.get("url", "")).strip(),
            enabled=_coerce_bool(data.get("enabled", True), True),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ThemeConfig:
    background_color: str = "#050505"
    panel_color: str = "#111111"
    primary_text_color: str = "#ff5c5c"
    secondary_text_color: str = "#ffd166"
    accent_color: str = "#00d4ff"
    positive_color: str = "#52d273"
    negative_color: str = "#ff5a76"
    muted_color: str = "#7d8896"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThemeConfig:
        base = cls()
        return cls(
            background_color=str(data.get("background_color", base.background_color)),
            panel_color=str(data.get("panel_color", base.panel_color)),
            primary_text_color=str(
                data.get("primary_text_color", base.primary_text_color)
            ),
            secondary_text_color=str(
                data.get("secondary_text_color", base.secondary_text_color)
            ),
            accent_color=str(data.get("accent_color", base.accent_color)),
            positive_color=str(data.get("positive_color", base.positive_color)),
            negative_color=str(data.get("negative_color", base.negative_color)),
            muted_color=str(data.get("muted_color", base.muted_color)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    title: str = "Market Matrix"
    stocks: list[str] = field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "SPY", "TSLA"]
    )
    feeds: list[FeedConfig] = field(
        default_factory=lambda: [
            FeedConfig(
                name="CNBC Top News",
                url="https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
            ),
            FeedConfig(
                name="MarketWatch",
                url="https://feeds.marketwatch.com/marketwatch/topstories/",
            ),
            FeedConfig(
                name="Investing.com Stock Market News",
                url="https://www.investing.com/rss/news_25.rss",
            ),
        ]
    )
    fullscreen: bool = True
    screen_width: int = 1920
    screen_height: int = 1080
    target_fps: int = 60
    scroll_speed: float = 260.0
    stock_refresh_seconds: int = 120
    news_refresh_seconds: int = 300
    news_items_per_feed: int = 8
    headline_separator: str = "   •   "
    font_name: str = "dejavusansmono"
    web_host: str = "0.0.0.0"
    web_port: int = 8787
    theme: ThemeConfig = field(default_factory=ThemeConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        base = cls()
        raw_stocks = data.get("stocks", base.stocks)
        raw_feeds = (
            data["feeds"]
            if "feeds" in data
            else [feed.to_dict() for feed in base.feeds]
        )
        normalized_feeds = [
            feed
            for feed in (FeedConfig.from_dict(item) for item in raw_feeds)
            if feed.url
        ]

        return cls(
            title=str(data.get("title", base.title)).strip() or base.title,
            stocks=_normalize_symbol_list(raw_stocks),
            feeds=normalized_feeds,
            fullscreen=_coerce_bool(
                data.get("fullscreen", base.fullscreen), base.fullscreen
            ),
            screen_width=_coerce_int(
                data.get("screen_width", base.screen_width),
                base.screen_width,
                minimum=640,
            ),
            screen_height=_coerce_int(
                data.get("screen_height", base.screen_height),
                base.screen_height,
                minimum=360,
            ),
            target_fps=_coerce_int(
                data.get("target_fps", base.target_fps), base.target_fps, minimum=15
            ),
            scroll_speed=_coerce_float(
                data.get("scroll_speed", base.scroll_speed),
                base.scroll_speed,
                minimum=10.0,
            ),
            stock_refresh_seconds=_coerce_int(
                data.get("stock_refresh_seconds", base.stock_refresh_seconds),
                base.stock_refresh_seconds,
                minimum=15,
            ),
            news_refresh_seconds=_coerce_int(
                data.get("news_refresh_seconds", base.news_refresh_seconds),
                base.news_refresh_seconds,
                minimum=30,
            ),
            news_items_per_feed=_coerce_int(
                data.get("news_items_per_feed", base.news_items_per_feed),
                base.news_items_per_feed,
                minimum=1,
            ),
            headline_separator=str(
                data.get("headline_separator", base.headline_separator)
            )
            or base.headline_separator,
            font_name=str(data.get("font_name", base.font_name)).strip()
            or base.font_name,
            web_host=str(data.get("web_host", base.web_host)).strip() or base.web_host,
            web_port=_coerce_int(
                data.get("web_port", base.web_port), base.web_port, minimum=1
            ),
            theme=ThemeConfig.from_dict(data.get("theme", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "stocks": list(self.stocks),
            "feeds": [feed.to_dict() for feed in self.feeds],
            "fullscreen": self.fullscreen,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "target_fps": self.target_fps,
            "scroll_speed": self.scroll_speed,
            "stock_refresh_seconds": self.stock_refresh_seconds,
            "news_refresh_seconds": self.news_refresh_seconds,
            "news_items_per_feed": self.news_items_per_feed,
            "headline_separator": self.headline_separator,
            "font_name": self.font_name,
            "web_host": self.web_host,
            "web_port": self.web_port,
            "theme": self.theme.to_dict(),
        }


@dataclass(slots=True)
class StockQuote:
    symbol: str
    price: float | None = None
    change_percent: float | None = None
    currency: str = "USD"
    market_state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Headline:
    source: str
    title: str
    link: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
