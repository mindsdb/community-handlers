import json
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests
from mindsdb_sql_parser import parse_sql

from community_handlers.adanos_handler import Handler, connection_args, import_error
from community_handlers.adanos_handler.adanos_handler import OPERATIONS
from community_handlers.adanos_handler.generate_operations import build_contract, render


QUERY = (
    "SELECT * FROM stock_sentiment WHERE ticker = 'AAPL' "
    "AND from_date = '2026-09-01' AND to_date = '2026-09-02'"
)
PAYLOAD = {
    "ticker": "AAPL",
    "found": True,
    "buzz_score": 42.5,
    "mentions": 15,
    "sentiment_score": 0.2,
    "bullish_pct": 55.0,
    "bearish_pct": 20.0,
}


@pytest.fixture
def http():
    with patch(
        "community_handlers.adanos_handler.adanos_handler.requests.request"
    ) as get:
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = PAYLOAD.copy()
        yield get


@pytest.fixture
def handler():
    assert import_error is None
    # Deliberately invalid dummy credential; never contacts the live API.
    return Handler("adanos", connection_data={"api_key": "dummy"})


def test_query_uses_explicit_window_and_header(handler, http):
    result = handler.query(parse_sql(QUERY)).data_frame
    assert result.iloc[0]["sentiment_score"] == 0.2
    assert str(result.iloc[0]["from_date"].date()) == "2026-09-01"
    http.assert_called_once_with(
        "GET",
        "https://api.adanos.org/reddit/stocks/v1/stock/AAPL",
        headers={"X-API-Key": "dummy"},
        params={"from": "2026-09-01", "to": "2026-09-02"},
        json=None,
        timeout=30,
        allow_redirects=False,
    )


def test_result_filters_and_zero_limit(handler, http):
    assert handler.query(parse_sql(QUERY + " AND mentions > 100")).data_frame.empty
    http.reset_mock()
    assert handler.query(parse_sql(QUERY + " LIMIT 0")).data_frame.empty
    http.assert_not_called()


def test_missing_coverage_is_not_neutral(handler, http):
    http.return_value.json.return_value = {"ticker": "AAPL", "found": False}
    result = handler.query(parse_sql(QUERY)).data_frame
    assert len(result) == 1
    assert not result.iloc[0]["found"]
    assert pd.isna(result.iloc[0]["sentiment_score"])


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM stock_sentiment",
        QUERY.replace("ticker =", "ticker !="),
        QUERY.replace("AAPL", "aapl"),
        QUERY.replace("AAPL", "../search"),
        QUERY.replace("2026-09-01", "2026-09-03"),
        QUERY.replace("2026-09-01", "not-a-date"),
        QUERY + " AND ticker = 'MSFT'",
        QUERY.replace("AND to_date = '2026-09-02'", ""),
        QUERY.replace("from_date =", "from_date >"),
    ],
)
def test_invalid_queries_make_no_requests(handler, http, query):
    with pytest.raises(ValueError):
        handler.query(parse_sql(query))
    http.assert_not_called()


@pytest.mark.parametrize("status", [301, 401, 403, 404, 429, 500])
def test_http_errors_not_empty_results(handler, http, status):
    http.return_value.status_code = status
    with pytest.raises(RuntimeError, match=f"Adanos HTTP {status}") as error:
        handler.query(parse_sql(QUERY))
    assert "dummy" not in str(error.value)
    assert http.call_count == 1


def test_timeout_is_redacted(handler, http):
    http.side_effect = requests.Timeout("dummy")
    with pytest.raises(RuntimeError, match="connectivity") as error:
        handler.query(parse_sql(QUERY))
    assert "dummy" not in str(error.value)


@pytest.mark.parametrize("payload", [[], {}, {"found": "false"}])
def test_malformed_response(handler, http, payload):
    http.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="Invalid Adanos"):
        handler.query(parse_sql(QUERY))


def test_invalid_json(handler, http):
    http.return_value.json.side_effect = ValueError("dummy")
    with pytest.raises(ValueError, match="invalid JSON") as error:
        handler.query(parse_sql(QUERY))
    assert "dummy" not in str(error.value)


def test_connection_and_metadata(handler, http):
    assert connection_args["api_key"]["secret"] is True
    assert handler.get_tables().data_frame["table_name"].tolist() == ["stock_sentiment"]
    handler.get_columns("stock_sentiment")
    http.assert_not_called()
    assert handler.check_connection().success
    assert http.call_args.args[1].endswith("/search")
    http.return_value.status_code = 401
    assert not handler.check_connection().success
    assert not handler.is_connected
    handler.connect()
    handler.disconnect()
    assert not handler.is_connected


@pytest.mark.parametrize("key", [None, "", " ", 123])
def test_key_required(key):
    with pytest.raises(ValueError, match="api_key"):
        Handler("adanos", connection_data={"api_key": key})


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM stock_sentiment",
        "UPDATE stock_sentiment SET mentions = 1",
        "INSERT INTO stock_sentiment (ticker) VALUES ('AAPL')",
    ],
)
def test_read_only(handler, http, sql):
    with pytest.raises(NotImplementedError):
        handler.query(parse_sql(sql))
    http.assert_not_called()


SAMPLE_ARGUMENTS = {
    "ticker": "AAPL",
    "symbol": "BTC",
    "from": "2026-09-01",
    "to": "2026-09-02",
    "limit": 2,
    "offset": 1,
    "type": "stock",
    "tickers": "AAPL,TSLA",
    "symbols": "BTC,ETH",
    "q": "tesla",
    "source": "reuters",
    "include_inherited": False,
    "text": "Revenue increased but margins fell.",
}


def native_call(name, arguments):
    aliases = {"from": "from_date", "to": "to_date"}
    return (
        name
        + "("
        + ", ".join(
            f"{aliases.get(key, key)}={value!r}" for key, value in arguments.items()
        )
        + ")"
    )


@pytest.mark.parametrize("name", sorted(OPERATIONS))
def test_every_operation_and_parameter(handler, http, name):
    operation = OPERATIONS[name]
    arguments = {
        key: SAMPLE_ARGUMENTS[key] for key in operation["schema"]["properties"]
    }
    payload = {"results": [{"sentiment_score": -0.25}], "next_offset": 3}
    http.return_value.json.return_value = payload
    result = handler.native_query(native_call(name, arguments)).data_frame
    assert result.columns.tolist() == ["response"]
    assert json.loads(result.iloc[0]["response"]) == payload
    path = operation["path"]
    for key in operation["path_parameters"]:
        path = path.replace("{" + key + "}", arguments[key])
    expected_query = {key: arguments[key] for key in operation["query_parameters"]}
    if "include_inherited" in expected_query:
        expected_query["include_inherited"] = "false"
    expected_body = {
        key: arguments[key] for key in operation["body_parameters"]
    } or None
    expected_headers = {}
    if operation["authenticated"]:
        expected_headers["X-API-Key"] = "dummy"
    http.assert_called_once_with(
        operation["method"],
        "https://api.adanos.org" + path,
        headers=expected_headers,
        params=expected_query,
        json=expected_body,
        timeout=30,
        allow_redirects=False,
    )


def test_complete_public_route_inventory():
    expected = {"/health", "/sentiment/v1/analyze"}
    for source in ("reddit", "x", "news", "polymarket"):
        prefix = f"/{source}/stocks/v1"
        suffixes = {
            "/trending",
            "/trending/sectors",
            "/trending/countries",
            "/stock/{ticker}",
            "/stock/{ticker}/mentions",
            "/search",
            "/compare",
            "/market-sentiment",
            "/stats",
            "/health",
        }
        if source != "polymarket":
            suffixes.add("/stock/{ticker}/explain")
        expected.update(prefix + suffix for suffix in suffixes)
    expected.update(
        "/reddit/crypto/v1" + suffix
        for suffix in (
            "/trending",
            "/token/{symbol}",
            "/token/{symbol}/mentions",
            "/search",
            "/compare",
            "/market-sentiment",
            "/stats",
            "/health",
        )
    )
    assert len(OPERATIONS) == 53
    assert {op["path"] for op in OPERATIONS.values()} == expected
    assert {op["path"] for op in OPERATIONS.values() if op["method"] == "POST"} == {
        "/sentiment/v1/analyze"
    }
    assert all("days" not in op["schema"]["properties"] for op in OPERATIONS.values())


@pytest.mark.parametrize(
    "query",
    [
        "unknownOperation()",
        "getXTrendingStocks(days=7)",
        "getXTrendingStocks(limit=101)",
        "getXTrendingStocks(limit=True)",
        "getXTrendingStocks(offset=-1)",
        "getXTrendingStocks(source='reuters')",
        "getRedditCryptoToken()",
        "getRedditCryptoToken(symbol='../stats')",
        "getStockSentiment(ticker='..')",
        "getStockSentiment(ticker='AAPL', from_date='2026-02-30')",
        "getStockSentiment(ticker='AAPL', from_date='2026-09-02',"
        " to_date='2026-09-01')",
        "getTrendingStocks(to_date='2026-09-01', to='2026-09-02')",
        "searchStocks(q='x')",
        "getStockRawMentions(ticker='AAPL', include_inherited='yes')",
        "analyzeSentimentText()",
        "analyzeSentimentText(text='')",
        "analyzeSentimentText(text=42)",
        "analyzeSentimentText(text=" + repr("x" * 2049) + ")",
        "getStats('ignored')",
        "getStats(limit=1, limit=2)",
        "getStats(**{})",
        "object.getStats()",
    ],
)
def test_native_invalid_inputs_never_call_api(handler, http, query):
    with pytest.raises(ValueError):
        handler.native_query(query)
    http.assert_not_called()


@pytest.mark.parametrize("payload", [[], {}, None, {"found": False, "score": None}])
def test_native_preserves_complete_json(handler, http, payload):
    http.return_value.json.return_value = payload
    result = handler.native_query("getNewsStats()").data_frame
    assert len(result) == 1
    assert json.loads(result.iloc[0]["response"]) == payload


def test_optional_nulls_and_no_implicit_pagination(handler, http):
    handler.native_query("getNewsTrendingStocks(from_date=null, limit=1)")
    assert http.call_args.kwargs["params"] == {"limit": 1}
    assert http.call_count == 1


@pytest.mark.parametrize(
    "query,method,path",
    [
        (
            "getNewsStockMentions(ticker='AAPL', limit=1)",
            "GET",
            "/news/stocks/v1/stock/AAPL/mentions",
        ),
        (
            "analyzeSentimentText(text='Sales increased')",
            "POST",
            "/sentiment/v1/analyze",
        ),
    ],
)
@pytest.mark.parametrize("status", [403, 429])
def test_plan_and_quota_failures_are_not_retried(
    handler, http, query, method, path, status
):
    http.return_value.status_code = status
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        handler.native_query(query)
    assert http.call_count == 1
    assert http.call_args.args == (method, "https://api.adanos.org" + path)


def test_contract_generator_resolves_body_and_excludes_deprecated():
    spec = {
        "info": {"version": "test"},
        "components": {
            "schemas": {
                "Body": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "minLength": 1}},
                    "required": ["text"],
                }
            }
        },
        "paths": {
            "/sentiment/v1/analyze": {
                "post": {
                    "operationId": "analyzeSentimentText",
                    "security": [{"ApiKeyAuth": []}],
                    "parameters": [{"name": "days", "deprecated": True}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Body"}
                            }
                        }
                    },
                }
            }
        },
    }
    contract = build_contract(spec)
    operation = contract["operations"]["analyzeSentimentText"]
    assert operation["method"] == "POST"
    assert operation["authenticated"] is True
    assert operation["schema"]["properties"] == {
        "text": {"type": "string", "minLength": 1}
    }
    assert operation["schema"]["required"] == ["text"]
    assert json.loads(render(contract)) == contract


def test_committed_contract_schemas_are_valid():
    from jsonschema import Draft202012Validator

    path = (
        Path(__file__).parents[2] / "community_handlers/adanos_handler/operations.json"
    )
    assert json.loads(path.read_text())["api_version"] == "1.50.1"
    for operation in OPERATIONS.values():
        Draft202012Validator.check_schema(operation["schema"])


def test_readme_native_sql_examples(handler, http):
    readme = Path(__file__).parents[2] / "community_handlers/adanos_handler/README.md"
    examples = re.findall(r"SELECT response FROM adanos .*?;", readme.read_text(), re.S)
    assert len(examples) == 7
    for example in examples:
        query = parse_sql(example)
        result = handler.native_query(query.from_table.query).data_frame
        assert json.loads(result.iloc[0]["response"]) == PAYLOAD


def test_generator_rejects_unsupported_method():
    with pytest.raises(ValueError, match="Unsupported API method"):
        build_contract({"paths": {"/unexpected": {"delete": {}}}})
