from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from datetime import datetime

import pygame

from .models import AppConfig, ThemeConfig
from .state import SharedState, StateSnapshot


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    if len(raw) != 6:
        return (255, 255, 255)
    try:
        return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (255, 255, 255)


def _format_quote_price(price: float | None) -> str:
    if price is None:
        return "--"
    return f"{price:,.2f}"


def _format_change(change: float | None) -> str:
    if change is None:
        return "--"
    prefix = "+" if change >= 0 else ""
    return f"{prefix}{change:.2f}%"


@dataclass(slots=True)
class MarqueeCache:
    text: str = ""
    font_key: tuple[str, int, bool] | None = None
    surface: pygame.Surface | None = None
    gap_px: int = 120


class Hub75Renderer:
    def __init__(self, state: SharedState, stop_event: threading.Event) -> None:
        self.state = state
        self.stop_event = stop_event
        self._fonts: dict[tuple[str, int, bool], pygame.font.Font] = {}
        self._marquee = MarqueeCache()
        self._marquee_offset = 0.0
        self._background_cache: (
            tuple[tuple[int, int], tuple[str, str], pygame.Surface] | None
        ) = None

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption("Market Matrix")
        screen: pygame.Surface | None = None
        display_key: tuple[bool, int, int] | None = None
        clock = pygame.time.Clock()

        while not self.stop_event.is_set():
            snapshot = self.state.snapshot()
            next_display_key = (
                snapshot.config.fullscreen,
                snapshot.config.screen_width,
                snapshot.config.screen_height,
            )
            if screen is None or next_display_key != display_key:
                flags = pygame.FULLSCREEN if snapshot.config.fullscreen else 0
                size = (
                    (0, 0)
                    if snapshot.config.fullscreen
                    else (snapshot.config.screen_width, snapshot.config.screen_height)
                )
                screen = pygame.display.set_mode(size, flags)
                display_key = next_display_key
                self._background_cache = None

            self._handle_events()
            self._draw(screen, snapshot)
            pygame.display.flip()

            delta_seconds = clock.tick(snapshot.config.target_fps) / 1000.0
            self._update_marquee(delta_seconds, snapshot.config.scroll_speed)

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if (
                event.type == pygame.QUIT
                or (
                    event.type == pygame.KEYDOWN
                    and event.key
                    in (pygame.K_ESCAPE, pygame.K_q)
                )
            ):
                self.stop_event.set()

    def _draw(self, screen: pygame.Surface, snapshot: StateSnapshot) -> None:
        width, height = screen.get_size()
        theme = snapshot.config.theme
        screen.blit(self._get_background((width, height), theme), (0, 0))

        padding = int(width * 0.025)
        header_height = int(height * 0.16)
        board_top = padding + header_height
        board_height = int(height * 0.34)
        marquee_height = int(height * 0.18)
        marquee_top = height - marquee_height - padding

        self._draw_header(
            screen, snapshot.config, snapshot.errors, padding, width, header_height
        )
        self._draw_stock_board(
            screen, snapshot, padding, board_top, width - (padding * 2), board_height
        )
        self._draw_marquee(
            screen,
            snapshot,
            padding,
            marquee_top,
            width - (padding * 2),
            marquee_height,
        )

    def _draw_header(
        self,
        screen: pygame.Surface,
        config: AppConfig,
        errors: dict[str, str],
        padding: int,
        width: int,
        header_height: int,
    ) -> None:
        theme = config.theme
        panel_rect = pygame.Rect(padding, padding, width - (padding * 2), header_height)
        self._draw_panel(screen, panel_rect, theme)

        title_font = self._get_font(config.font_name, 52, True)
        meta_font = self._get_font(config.font_name, 26, False)
        time_font = self._get_font(config.font_name, 38, True)

        title_surface = title_font.render(
            config.title.upper(), True, _hex_to_rgb(theme.primary_text_color)
        )
        screen.blit(title_surface, (panel_rect.x + 22, panel_rect.y + 18))

        subtitle = "Stocks and headlines live ticker"
        subtitle_surface = meta_font.render(
            subtitle, True, _hex_to_rgb(theme.secondary_text_color)
        )
        screen.blit(subtitle_surface, (panel_rect.x + 24, panel_rect.y + 80))

        now_text = datetime.now().strftime("%a %b %d  %H:%M:%S")
        time_surface = time_font.render(now_text, True, _hex_to_rgb(theme.accent_color))
        screen.blit(
            time_surface,
            (panel_rect.right - time_surface.get_width() - 22, panel_rect.y + 20),
        )

        status_parts = []
        if errors.get("stocks"):
            status_parts.append("Stock refresh issue")
        if errors.get("news"):
            status_parts.append("News refresh issue")
        if not status_parts:
            status_parts.append(f"Web admin on port {config.web_port}")
        status_surface = meta_font.render(
            " | ".join(status_parts),
            True,
            _hex_to_rgb(theme.muted_color),
        )
        screen.blit(
            status_surface,
            (panel_rect.right - status_surface.get_width() - 22, panel_rect.y + 72),
        )

    def _draw_stock_board(
        self,
        screen: pygame.Surface,
        snapshot: StateSnapshot,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> None:
        theme = snapshot.config.theme
        board_rect = pygame.Rect(left, top, width, height)
        self._draw_panel(screen, board_rect, theme)

        label_font = self._get_font(snapshot.config.font_name, 28, False)
        title_surface = label_font.render(
            "MARKET BOARD", True, _hex_to_rgb(theme.secondary_text_color)
        )
        screen.blit(title_surface, (board_rect.x + 18, board_rect.y + 16))

        quotes = snapshot.quotes
        if not quotes:
            fallback_font = self._get_font(snapshot.config.font_name, 44, True)
            text = "Waiting for stock quotes..."
            surface = fallback_font.render(text, True, _hex_to_rgb(theme.muted_color))
            screen.blit(
                surface,
                (
                    board_rect.centerx - (surface.get_width() // 2),
                    board_rect.centery - (surface.get_height() // 2),
                ),
            )
            return

        gap = 16
        tile_min_width = 230
        columns = max(1, min(len(quotes), max(1, width // (tile_min_width + gap))))
        rows = max(1, math.ceil(len(quotes) / columns))
        inner_top = board_rect.y + 58
        tile_width = int((width - ((columns + 1) * gap)) / columns)
        tile_height = int((height - 72 - ((rows + 1) * gap)) / rows)

        symbol_font = self._get_font(snapshot.config.font_name, 34, True)
        price_font = self._get_font(snapshot.config.font_name, 46, True)
        detail_font = self._get_font(snapshot.config.font_name, 24, False)

        for index, quote in enumerate(quotes):
            row = index // columns
            col = index % columns
            tile_rect = pygame.Rect(
                board_rect.x + gap + (col * (tile_width + gap)),
                inner_top + gap + (row * (tile_height + gap)),
                tile_width,
                tile_height,
            )
            self._draw_tile(screen, tile_rect, theme)

            symbol_surface = symbol_font.render(
                quote.symbol, True, _hex_to_rgb(theme.accent_color)
            )
            screen.blit(symbol_surface, (tile_rect.x + 16, tile_rect.y + 12))

            price_surface = price_font.render(
                _format_quote_price(quote.price),
                True,
                _hex_to_rgb(theme.primary_text_color),
            )
            screen.blit(price_surface, (tile_rect.x + 16, tile_rect.y + 54))

            change_color = theme.muted_color
            if quote.change_percent is not None:
                change_color = (
                    theme.positive_color
                    if quote.change_percent >= 0
                    else theme.negative_color
                )

            change_surface = detail_font.render(
                _format_change(quote.change_percent),
                True,
                _hex_to_rgb(change_color),
            )
            screen.blit(change_surface, (tile_rect.x + 18, tile_rect.bottom - 42))

            status_surface = detail_font.render(
                quote.market_state or quote.currency,
                True,
                _hex_to_rgb(theme.muted_color),
            )
            screen.blit(
                status_surface,
                (
                    tile_rect.right - status_surface.get_width() - 16,
                    tile_rect.bottom - 42,
                ),
            )

    def _draw_marquee(
        self,
        screen: pygame.Surface,
        snapshot: StateSnapshot,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> None:
        theme = snapshot.config.theme
        rect = pygame.Rect(left, top, width, height)
        self._draw_panel(screen, rect, theme)

        label_font = self._get_font(snapshot.config.font_name, 28, False)
        label_surface = label_font.render(
            "HEADLINES", True, _hex_to_rgb(theme.secondary_text_color)
        )
        screen.blit(label_surface, (rect.x + 18, rect.y + 16))

        headline_font = self._get_font(snapshot.config.font_name, 48, True)
        marquee_text = self._build_marquee_text(snapshot)
        self._ensure_marquee_surface(
            marquee_text,
            snapshot.config.font_name,
            headline_font,
            _hex_to_rgb(theme.primary_text_color),
        )

        if self._marquee.surface is None:
            return

        clip_rect = pygame.Rect(
            rect.x + 18, rect.y + 58, rect.width - 36, rect.height - 76
        )
        previous_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        text_y = clip_rect.y + max(
            0, (clip_rect.height - self._marquee.surface.get_height()) // 2
        )
        base_x = clip_rect.x + int(self._marquee_offset)
        screen.blit(self._marquee.surface, (base_x, text_y))
        screen.blit(
            self._marquee.surface,
            (base_x + self._marquee.surface.get_width() + self._marquee.gap_px, text_y),
        )
        screen.set_clip(previous_clip)

    def _build_marquee_text(self, snapshot: StateSnapshot) -> str:
        if not snapshot.headlines:
            return "Waiting for RSS headlines..."
        return snapshot.config.headline_separator.join(
            f"[{headline.source}] {headline.title}" for headline in snapshot.headlines
        )

    def _ensure_marquee_surface(
        self,
        text: str,
        font_name: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
    ) -> None:
        font_key = (font_name, font.get_height(), font.get_bold())
        if (
            self._marquee.text == text
            and self._marquee.font_key == font_key
            and self._marquee.surface
        ):
            return

        self._marquee.text = text
        self._marquee.font_key = font_key
        self._marquee.surface = font.render(text, True, color)
        self._marquee_offset = 0.0

    def _update_marquee(self, delta_seconds: float, scroll_speed: float) -> None:
        if self._marquee.surface is None:
            return
        self._marquee_offset -= scroll_speed * delta_seconds
        loop_width = self._marquee.surface.get_width() + self._marquee.gap_px
        if self._marquee_offset <= -loop_width:
            self._marquee_offset = 0.0

    def _get_font(self, font_name: str, size: int, bold: bool) -> pygame.font.Font:
        key = (font_name, size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(font_name, size, bold=bold)
        return self._fonts[key]

    def _get_background(
        self,
        size: tuple[int, int],
        theme: ThemeConfig,
    ) -> pygame.Surface:
        cache_key = (size, (theme.background_color, theme.panel_color))
        if self._background_cache and self._background_cache[:2] == cache_key:
            return self._background_cache[2]

        width, height = size
        surface = pygame.Surface(size)
        surface.fill(_hex_to_rgb(theme.background_color))

        dot_color = _hex_to_rgb(theme.panel_color)
        for y in range(10, height, 22):
            for x in range(10, width, 22):
                pygame.draw.circle(surface, dot_color, (x, y), 2)

        self._background_cache = (
            size,
            (theme.background_color, theme.panel_color),
            surface,
        )
        return surface

    def _draw_panel(
        self, screen: pygame.Surface, rect: pygame.Rect, theme: ThemeConfig
    ) -> None:
        base = _hex_to_rgb(theme.panel_color)
        accent = _hex_to_rgb(theme.accent_color)
        pygame.draw.rect(screen, base, rect, border_radius=18)
        pygame.draw.rect(screen, accent, rect, width=2, border_radius=18)

    def _draw_tile(
        self, screen: pygame.Surface, rect: pygame.Rect, theme: ThemeConfig
    ) -> None:
        inner = tuple(
            min(255, component + 12) for component in _hex_to_rgb(theme.panel_color)
        )
        pygame.draw.rect(screen, inner, rect, border_radius=14)
        pygame.draw.rect(
            screen,
            _hex_to_rgb(theme.secondary_text_color),
            rect,
            width=1,
            border_radius=14,
        )
