import ast
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from mindsdb.integrations.libs.api_handler import APIHandler, APIResource, FuncParser
from mindsdb.integrations.libs.response import HandlerStatusResponse, TableResponse
from mindsdb.integrations.utilities.sql_utils import FilterOperator


OPERATIONS = json.loads(Path(__file__).with_name("operations.json").read_text())[
    "operations"
]


class StockSentimentTable(APIResource):
    """One aggregate row for an explicit ticker and inclusive UTC window."""

    def get_columns(self):
        return [
            "ticker",
            "from_date",
            "to_date",
            "found",
            "buzz_score",
            "mentions",
            "sentiment_score",
            "bullish_pct",
            "bearish_pct",
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
            f"/reddit/stocks/v1/stock/{inputs['ticker']}",
            {"from": inputs["from_date"], "to": inputs["to_date"]},
        )
        if not isinstance(data, dict) or not isinstance(data.get("found"), bool):
            raise ValueError("Invalid Adanos stock sentiment response")
        # Missing coverage stays explicit; never synthesize neutral sentiment.
        return pd.DataFrame([{**data, **inputs}], columns=self.get_columns())


class AdanosHandler(APIHandler):
    """Adanos data and text analysis; no background requests or writes to assets."""

    def __init__(self, name, connection_data, **kwargs):
        super().__init__(name)
        self.api_key = connection_data.get("api_key")
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("An Adanos api_key is required")
        self._register_table("stock_sentiment", StockSentimentTable(self))

    def connect(self):
        self.is_connected = True
        return self

    def request(
        self, path, params=None, *, method="GET", body=None, authenticated=True
    ):
        try:
            response = requests.request(
                method,
                f"https://api.adanos.org{path}",
                headers={"X-API-Key": self.api_key} if authenticated else {},
                params=params,
                json=body,
                timeout=30,
                allow_redirects=False,
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
            self.request("/reddit/stocks/v1/search", {"q": "AAPL", "limit": 1})
            self.is_connected = True
            return HandlerStatusResponse(True)
        except (RuntimeError, ValueError) as exc:
            self.is_connected = False
            return HandlerStatusResponse(False, str(exc))

    def native_query(self, query, **kwargs) -> TableResponse:
        """Call an OpenAPI operation using MindsDB's native function syntax."""
        call = ast.parse(query.strip(), mode="eval").body
        if (
            not isinstance(call, ast.Call)
            or not isinstance(call.func, ast.Name)
            or call.args
            or any(k.arg is None for k in call.keywords)
            or len({k.arg for k in call.keywords}) != len(call.keywords)
        ):
            raise ValueError("Use an operation name with unique named arguments")
        name, arguments = FuncParser().from_string(query)
        if name not in OPERATIONS:
            raise ValueError("Unknown Adanos operation; see the operation reference")
        operation = OPERATIONS[name]
        for alias, parameter in (("from_date", "from"), ("to_date", "to")):
            if alias in arguments:
                if parameter in arguments:
                    raise ValueError(f"Use only {alias}, not both date names")
                arguments[parameter] = arguments.pop(alias)
        try:
            Draft202012Validator(
                operation["schema"], format_checker=FormatChecker()
            ).validate(arguments)
        except ValidationError as exc:
            field = ".".join(map(str, exc.path)) or "parameters"
            raise ValueError(f"Invalid {field}: {exc.validator}") from None
        start, end = arguments.get("from"), arguments.get("to")
        if start is not None and end is not None and start > end:
            raise ValueError("from_date must not be after to_date")
        path = operation["path"]
        for parameter in operation["path_parameters"]:
            value = arguments[parameter]
            if not value or value in {".", ".."} or "/" in value or "\\" in value:
                raise ValueError("Invalid asset path parameter")
            path = path.replace("{" + parameter + "}", quote(value, safe=""))
        params = {
            key: str(arguments[key]).lower()
            if isinstance(arguments[key], bool)
            else arguments[key]
            for key in operation["query_parameters"]
            if key in arguments and arguments[key] is not None
        }
        body = (
            {
                key: arguments[key]
                for key in operation["body_parameters"]
                if key in arguments
            }
            if operation["body_parameters"]
            else None
        )
        data = self.request(
            path,
            params,
            method=operation["method"],
            body=body,
            authenticated=operation["authenticated"],
        )
        # Keep arrays, nested records, coverage and pagination metadata intact.
        return TableResponse(pd.DataFrame({"response": [json.dumps(data)]}))
