import re
from datetime import date

import pandas as pd
import requests

from mindsdb.integrations.libs.api_handler import APIHandler, APIResource
from mindsdb.integrations.libs.response import HandlerStatusResponse
from mindsdb.integrations.utilities.sql_utils import FilterOperator


class StockSentimentTable(APIResource):
    """One aggregate row for an explicit ticker and inclusive UTC window."""

    def get_columns(self):
        return [
            "ticker", "from_date", "to_date", "found", "buzz_score",
            "mentions", "sentiment_score", "bullish_pct", "bearish_pct",
        ]

    def list(self, conditions=None, limit=None, sort=None, targets=None):
        inputs = {}
        for condition in conditions or []:
            if condition.column in ("ticker", "from_date", "to_date"):
                if condition.op != FilterOperator.EQUAL:
                    raise ValueError(
                        "ticker, from_date and to_date require '=' filters"
                    )
                if condition.column in inputs:
                    raise ValueError(f"Duplicate filter: {condition.column}")
                inputs[condition.column] = condition.value
        if set(inputs) != {"ticker", "from_date", "to_date"}:
            raise ValueError("Provide ticker, from_date and to_date with '=' filters")
        if not isinstance(inputs["ticker"], str) or not re.fullmatch(
            r"[A-Z0-9][A-Z0-9.-]{0,19}", inputs["ticker"]
        ):
            raise ValueError("ticker must be an uppercase stock symbol")
        for key in ("from_date", "to_date"):
            value = inputs[key]
            if (
                not isinstance(value, str)
                or date.fromisoformat(value).isoformat() != value
            ):
                raise ValueError(f"{key} must be YYYY-MM-DD")
        if inputs["from_date"] > inputs["to_date"]:
            raise ValueError("from_date must not be after to_date")
        if limit == 0:
            return pd.DataFrame(columns=self.get_columns())
        data = self.handler.request(
            f"stock/{inputs['ticker']}",
            {"from": inputs["from_date"], "to": inputs["to_date"]},
        )
        if not isinstance(data, dict) or not isinstance(data.get("found"), bool):
            raise ValueError("Invalid Adanos stock sentiment response")
        # Missing coverage stays explicit; never synthesize neutral sentiment.
        return pd.DataFrame([{**data, **inputs}], columns=self.get_columns())


class AdanosHandler(APIHandler):
    """Optional read-only Adanos data source; no background requests."""

    def __init__(self, name, connection_data, **kwargs):
        super().__init__(name)
        self.api_key = connection_data.get("api_key")
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("An Adanos api_key is required")
        self._register_table("stock_sentiment", StockSentimentTable(self))

    def connect(self):
        self.is_connected = True
        return self

    def request(self, path, params):
        try:
            response = requests.get(
                f"https://api.adanos.org/reddit/stocks/v1/{path}",
                headers={"X-API-Key": self.api_key},
                params=params, timeout=30, allow_redirects=False,
            )
        except requests.RequestException:
            raise RuntimeError("Adanos request failed; check connectivity") from None
        if response.status_code != 200:
            raise RuntimeError(
                f"Adanos HTTP {response.status_code}; check your API key, "
                "plan access, date window and request quota"
            )
        try:
            return response.json()
        except ValueError:
            raise ValueError("Adanos returned invalid JSON") from None

    def check_connection(self):
        try:
            self.request("search", {"q": "AAPL", "limit": 1})
            self.is_connected = True
            return HandlerStatusResponse(True)
        except (RuntimeError, ValueError) as exc:
            self.is_connected = False
            return HandlerStatusResponse(False, str(exc))
