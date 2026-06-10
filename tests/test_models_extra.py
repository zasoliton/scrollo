from __future__ import annotations

import unittest
from typing import Any

from scroller_app.models import (
    AppConfig,
    FeedConfig,
    _coerce_bool,
    _coerce_float,
    _coerce_int,
    _normalize_symbol_list,
)


class ModelsExtraTests(unittest.TestCase):
    def test_coerce_bool_various(self) -> None:
        self.assertTrue(_coerce_bool(True, False))
        self.assertFalse(_coerce_bool(False, True))
        self.assertTrue(_coerce_bool("yes", False))
        self.assertFalse(_coerce_bool("no", True))
        self.assertEqual(_coerce_bool(None, True), True)

    def test_coerce_int_and_float(self) -> None:
        self.assertEqual(_coerce_int("42", 0), 42)
        self.assertEqual(_coerce_int(None, 5), 5)
        self.assertEqual(_coerce_int("-1", 0, minimum=0), 0)

        self.assertAlmostEqual(_coerce_float("3.14", 0.0), 3.14)
        self.assertEqual(_coerce_float(None, 2.5), 2.5)
        self.assertEqual(_coerce_float("-1", 1.0, minimum=0.0), 0.0)

    def test_normalize_symbol_list(self) -> None:
        self.assertEqual(_normalize_symbol_list(None), [])
        self.assertEqual(
            _normalize_symbol_list("aapl, msft\nnvda"),
            ["AAPL", "MSFT", "NVDA"],
        )

        self.assertEqual(
            _normalize_symbol_list(["aapl", "AAPL", " msft "]),
            ["AAPL", "MSFT"],
        )

    def test_feedconfig_and_appconfig_from_dict(self) -> None:
        f = FeedConfig.from_dict({"name": "", "url": "https://x"})
        self.assertEqual(f.name, "Feed")

        cfg: dict[str, Any] = {
            "title": "My App",
            "stocks": ["goog", ""],
            "feeds": [{"name": "X", "url": "https://x"}],
            "scroll_speed": "300",
        }
        app = AppConfig.from_dict(cfg)
        self.assertEqual(app.title, "My App")
        self.assertIn("GOOG", app.stocks)
        self.assertEqual(app.scroll_speed, 300.0)


if __name__ == "__main__":
    unittest.main()
