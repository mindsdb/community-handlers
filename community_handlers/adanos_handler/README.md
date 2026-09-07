# Adanos

Query Reddit stock sentiment from [Adanos](https://adanos.org/) as a read-only
MindsDB table, for example to join attention and sentiment with your own price
or portfolio data. This handler does not fetch prices or generate trading signals.

Adanos is a commercial API with a free plan. Bring your own API key; your plan's
date-window, coverage and quota restrictions apply. See the
[API documentation](https://api.adanos.org/docs) for current entitlements.
No paid plan is assumed and no requests are made until queried or connection-tested.

## Connection

Enable community handlers with `MINDSDB_COMMUNITY_HANDLERS=true` and install the
`adanos` handler through MindsDB's handler installation mechanism. Restart MindsDB
if needed, then create a connection:

```sql
CREATE DATABASE adanos
WITH ENGINE = 'adanos',
PARAMETERS = {"api_key": "placeholder"};
```

Replace `placeholder` with your API key. The key is a secret connection argument
and is sent only in `X-API-Key` to
`https://api.adanos.org`. Connection checking makes one authenticated search request.

## Query

```sql
SELECT * FROM adanos.stock_sentiment
WHERE ticker = 'AAPL'
  AND from_date = '2026-09-06'
  AND to_date = '2026-09-06';
```

Replace the dates with a range available to your plan. Both dates are inclusive
UTC dates and must use `YYYY-MM-DD`. An uppercase ticker and both dates are
required, each exactly once with `=`. The handler uses `from`/`to`, not deprecated
`days`. Each query makes one stock-detail request and returns one aggregate row:

| Column | Meaning |
| --- | --- |
| `ticker` | Requested stock symbol |
| `from_date`, `to_date` | Requested inclusive UTC window |
| `found` | Whether the API found coverage |
| `buzz_score` | API attention score |
| `mentions` | Mention count |
| `sentiment_score` | API sentiment score |
| `bullish_pct`, `bearish_pct` | API sentiment percentages |

Additional filters on result columns use MindsDB's filtering. Missing values are
not replaced with zero: check `found` before interpreting a result. HTTP failures,
including authentication, plan restrictions and rate limits, are errors, not empty
datasets. There are no automatic retries that consume extra quota.

This initial handler intentionally supports only Reddit stocks, not crypto,
other sources, raw mentions, pagination or sentiment scoring. It uses the existing
MindsDB `APIHandler`/`APIResource` framework with `requests`, without an extra SDK.
Use standard MindsDB SQL, not native pass-through queries.

## Tests

With MindsDB 26.1.0 and pytest installed, from this repository:

```sh
python -m pytest tests/community_handlers/test_adanos.py -q
python -m pytest tests/community_handlers/test_handler_registration.py -k adanos -q
```

Tests use the real MindsDB parser/handler with mocked HTTP; no live key is required.
