from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules.setdefault(
    "feedparser", types.SimpleNamespace(parse=lambda *_, **__: None)
)

from scroller_app.data_sources import StockQuoteService  # noqa: E402
from scroller_app.models import StockQuote  # noqa: E402


class StockQuoteServiceTests(unittest.TestCase):
    def test_falls_back_when_yahoo_provider_rejects_request(self) -> None:
        service = StockQuoteService()
        response = requests.Response()
        response.status_code = 401
        yahoo_error = requests.HTTPError("401 Unauthorized", response=response)

        with (
            self.assertLogs("scroller_app.data_sources", level="WARNING"), patch.object(
                service, "_fetch_quotes_yahoo", side_effect=yahoo_error
            ) as yahoo_fetch,
            patch.object(
                service,
                "_fetch_quotes_stockprices",
                return_value=[
                    StockQuote(symbol="AAPL", price=123.45, change_percent=1.2)
                ],
            ) as fallback_fetch,
        ):
            quotes = service.fetch_quotes(["AAPL"])

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].price, 123.45)
        yahoo_fetch.assert_called_once_with(["AAPL"])
        fallback_fetch.assert_called_once_with(["AAPL"])


if __name__ == "__main__":
    unittest.main()
