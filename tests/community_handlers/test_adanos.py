from unittest.mock import Mock, patch

import pandas as pd
import pytest
import requests
from mindsdb_sql_parser import parse_sql

from community_handlers.adanos_handler import Handler, connection_args, import_error


QUERY = (
    "SELECT * FROM stock_sentiment WHERE ticker = 'AAPL' "
    "AND from_date = '2026-09-01' AND to_date = '2026-09-02'"
)
PAYLOAD = {
    "ticker": "AAPL", "found": True, "buzz_score": 42.5,
    "mentions": 15, "sentiment_score": 0.2,
    "bullish_pct": 55.0, "bearish_pct": 20.0,
}


@pytest.fixture
def http():
    with patch("community_handlers.adanos_handler.adanos_handler.requests.get") as get:
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
        "https://api.adanos.org/reddit/stocks/v1/stock/AAPL",
        headers={"X-API-Key": "dummy"},
        params={"from": "2026-09-01", "to": "2026-09-02"},
        timeout=30, allow_redirects=False,
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


@pytest.mark.parametrize("query", [
    "SELECT * FROM stock_sentiment",
    QUERY.replace("ticker =", "ticker !="),
    QUERY.replace("AAPL", "aapl"),
    QUERY.replace("AAPL", "../search"),
    QUERY.replace("2026-09-01", "2026-09-03"),
    QUERY.replace("2026-09-01", "not-a-date"),
    QUERY + " AND ticker = 'MSFT'",
    QUERY.replace("AND to_date = '2026-09-02'", ""),
    QUERY.replace("from_date =", "from_date >"),
])
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
    assert http.call_args.args[0].endswith("/search")
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


@pytest.mark.parametrize("sql", [
    "DELETE FROM stock_sentiment",
    "UPDATE stock_sentiment SET mentions = 1",
    "INSERT INTO stock_sentiment (ticker) VALUES ('AAPL')",
])
def test_read_only(handler, http, sql):
    with pytest.raises(NotImplementedError):
        handler.query(parse_sql(sql))
    http.assert_not_called()
