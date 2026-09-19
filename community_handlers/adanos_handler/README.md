# Adanos

Access all **53 public operations in Adanos OpenAPI 1.50.1** from MindsDB:
Reddit, X / FinTwit, News and Polymarket for stocks; Reddit for crypto; direct
text sentiment analysis; and global/per-source health. [Adanos](https://adanos.org/)
is a commercial API with a free plan. Bring your own API key.

This handler does not fetch prices, place trades or manage your Adanos account.
Only operations from the public [OpenAPI](https://api.adanos.org/openapi.json)
are allowed; authentication/account-management routes are not part of that API.

## Connection

Use MindsDB 26.1.0 with `MINDSDB_COMMUNITY_HANDLERS=true` and install the `adanos`
community handler. For a source checkout, place or symlink this directory under
`mindsdb/integrations/handlers/` as the repository test workflow does, and install
its `requirements.txt`. Then restart MindsDB and create a connection:

```sql
CREATE DATABASE adanos
WITH ENGINE = 'adanos',
PARAMETERS = {"api_key": "placeholder"};
```

Replace `placeholder` with your key. It is a secret connection argument, sent
only in `X-API-Key` to `https://api.adanos.org`; health requests omit the key.
Connection checking makes one authenticated stock-search request. Construction
and import do not contact Adanos. No extra Adanos SDK is required.

## All Sources and Endpoints

Use MindsDB's native function syntax. Names match Adanos OpenAPI operation IDs.
The [complete operation reference](operations.md) lists every endpoint and argument.
For example:

```sql
SELECT response FROM adanos (
    getNewsTrendingStocks(from_date="2026-09-06", to_date="2026-09-06", limit=5, source="reuters")
);

SELECT response FROM adanos (
    getXStockSentiment(ticker="AAPL", from_date="2026-09-06", to_date="2026-09-06")
);

SELECT response FROM adanos (
    comparePolymarketStocks(tickers="AAPL,TSLA", from_date="2026-09-06", to_date="2026-09-06")
);

SELECT response FROM adanos (
    getRedditCryptoToken(symbol="BTC", from_date="2026-09-06", to_date="2026-09-06")
);

SELECT response FROM adanos (
    getStockRawMentions(ticker="AAPL", from_date="2026-09-06", to_date="2026-09-06", limit=5, offset=0, include_inherited=false)
);

SELECT response FROM adanos (
    analyzeSentimentText(text="Revenue grew, but operating margins fell.")
);

SELECT response FROM adanos (getRootHealth());
```

Dates must be available to your plan. `from_date` and `to_date` map to inclusive
UTC `from` and `to`. They are optional wherever the API permits omission; omitted
values use the API defaults. Deprecated `days` is rejected. Compares take
comma-separated `tickers` or `symbols`, not arrays. News trending supports its
`source` filter. Raw Reddit mentions support `include_inherited`.

Each native call makes **one request** and returns **one row** with a `response`
JSON string containing the entire API response. Arrays, empty lists, nested
`daily_trend`, raw `results`, pagination metadata, source-specific fields and nulls
are preserved, not flattened or renamed. This is deliberately not one SQL row
per asset. Decode `response` in your consuming application to work with its rows.
Use the API's `limit` and `offset` arguments for pagination; an outer SQL `LIMIT`
does not limit remote requests or paginate the API. No automatic page fetching,
retry loops or extra calls for schema discovery are performed.

## Plans and Errors

Free, Hobby and Professional keys use the same connection. Available windows,
quotas and feature access are enforced by Adanos, not hard-coded as a local plan
flag. See [current API documentation](https://api.adanos.org/docs).

- Raw mention operations for all five sources require **Professional**.
- `analyzeSentimentText` requires **Professional** and accepts 1-2048 characters.
- Other operations remain subject to the key's current access and limits.
- HTTP 401/403/422/429 and server errors are reported as errors, not empty data.
  There are no automatic retries, including for charged text analysis.
- `found=false` and null sentiment are coverage information, not a neutral signal.
- Social/news sentiment and Polymarket market signals have different semantics;
  this handler does not invent a cross-source score or trading recommendation.

## Optional Tabular Shortcut

For a simple Reddit stock join, the `stock_sentiment` SQL table remains available:

```sql
SELECT * FROM adanos.stock_sentiment
WHERE ticker = 'AAPL'
  AND from_date = '2026-09-06'
  AND to_date = '2026-09-06';
```

This shortcut returns one aggregate row with `ticker`, `from_date`, `to_date`,
`found`, `buzz_score`, `mentions`, `sentiment_score`, `bullish_pct`, `bearish_pct`.
It requires uppercase ticker and both dates, each once with `=`. Additional result
filters use MindsDB. Use native operations above for other sources or the full
response. Asset data is read-only; text analysis uses POST but does not change it.

## Tests and Contract Updates

With MindsDB 26.1.0 and pytest installed, from this repository:

```sh
python -m pytest tests/community_handlers/test_adanos.py -q
python -m pytest tests/community_handlers/test_handler_registration.py -q
```

Tests use the real MindsDB parser/handler with mocked HTTP and require no live key.
Routing, argument validation and documentation are generated from OpenAPI, not
downloaded at runtime. To verify coverage against a newly downloaded specification:

```sh
curl -fsSL https://api.adanos.org/openapi.json -o /tmp/adanos-openapi.json
python community_handlers/adanos_handler/generate_operations.py /tmp/adanos-openapi.json --check
```

To update, rerun without `--check`, review `operations.json` and `operations.md`,
and rerun tests. The independent route-inventory test must be updated explicitly
when the public endpoint set changes.
