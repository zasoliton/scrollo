from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scroller_app.config import ConfigStore
from scroller_app.models import AppConfig


class ConfigStoreTests(unittest.TestCase):
    def test_load_creates_default_config_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            store = ConfigStore(config_path)

            config = store.load()

            self.assertEqual(config.title, "Market Matrix")
            self.assertTrue(config_path.exists())
            self.assertEqual(config.feeds[0].name, "CNBC Top News")

    def test_load_normalizes_symbols_and_feeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            config_path.write_text(
                json.dumps(
                    {
                        "stocks": ["aapl", " msft ", "AAPL", ""],
                        "feeds": [
                            {
                                "name": "Reuters",
                                "url": "https://example.com/rss",
                                "enabled": True,
                            },
                            {"name": "", "url": "", "enabled": True},
                        ],
                        "scroll_speed": "300",
                    }
                ),
                encoding="utf-8",
            )
            store = ConfigStore(config_path)

            config = store.load()

            self.assertEqual(config.stocks, ["AAPL", "MSFT"])
            self.assertEqual(len(config.feeds), 1)
            self.assertEqual(config.scroll_speed, 300.0)

    def test_save_round_trips_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            store = ConfigStore(config_path)
            config = AppConfig(title="Desk Ticker", stocks=["QQQ"])

            store.save(config)
            loaded = store.load()

            self.assertEqual(loaded.title, "Desk Ticker")
            self.assertEqual(loaded.stocks, ["QQQ"])


if __name__ == "__main__":
    unittest.main()
