# Native Operations

Generated from Adanos OpenAPI 1.50.1. Do not edit.

Call these names inside `SELECT * FROM adanos (...)`.
`*` means required. `from_date`/`to_date` map to API `from`/`to`.
See [README](README.md) for examples, responses and plan restrictions.

| Operation | Method and path | Arguments |
| --- | --- | --- |
| `analyzeSentimentText` | `POST /sentiment/v1/analyze` | `text`* |
| `compareNewsStocks` | `GET /news/stocks/v1/compare` | `from_date`, `to_date`, `tickers`* |
| `comparePolymarketStocks` | `GET /polymarket/stocks/v1/compare` | `from_date`, `to_date`, `tickers`* |
| `compareRedditCryptoTokens` | `GET /reddit/crypto/v1/compare` | `from_date`, `to_date`, `symbols`* |
| `compareStocks` | `GET /reddit/stocks/v1/compare` | `from_date`, `to_date`, `tickers`* |
| `compareXStocks` | `GET /x/stocks/v1/compare` | `from_date`, `to_date`, `tickers`* |
| `getHealth` | `GET /reddit/stocks/v1/health` |  |
| `getNewsHealth` | `GET /news/stocks/v1/health` |  |
| `getNewsMarketSentiment` | `GET /news/stocks/v1/market-sentiment` | `from_date`, `to_date` |
| `getNewsStats` | `GET /news/stocks/v1/stats` |  |
| `getNewsStockExplanation` | `GET /news/stocks/v1/stock/{ticker}/explain` | `ticker`* |
| `getNewsStockMentions` | `GET /news/stocks/v1/stock/{ticker}/mentions` | `ticker`*, `from_date`, `to_date`, `limit`, `offset` |
| `getNewsStockSentiment` | `GET /news/stocks/v1/stock/{ticker}` | `ticker`*, `from_date`, `to_date` |
| `getNewsTrendingCountries` | `GET /news/stocks/v1/trending/countries` | `from_date`, `to_date`, `limit`, `offset`, `source` |
| `getNewsTrendingSectors` | `GET /news/stocks/v1/trending/sectors` | `from_date`, `to_date`, `limit`, `offset`, `source` |
| `getNewsTrendingStocks` | `GET /news/stocks/v1/trending` | `from_date`, `to_date`, `limit`, `offset`, `type`, `source` |
| `getPolymarketHealth` | `GET /polymarket/stocks/v1/health` |  |
| `getPolymarketMarketSentiment` | `GET /polymarket/stocks/v1/market-sentiment` | `from_date`, `to_date` |
| `getPolymarketStats` | `GET /polymarket/stocks/v1/stats` |  |
| `getPolymarketStock` | `GET /polymarket/stocks/v1/stock/{ticker}` | `ticker`*, `from_date`, `to_date` |
| `getPolymarketStockRawMentions` | `GET /polymarket/stocks/v1/stock/{ticker}/mentions` | `ticker`*, `from_date`, `to_date`, `limit`, `offset` |
| `getPolymarketTrendingCountries` | `GET /polymarket/stocks/v1/trending/countries` | `from_date`, `to_date`, `limit`, `offset` |
| `getPolymarketTrendingSectors` | `GET /polymarket/stocks/v1/trending/sectors` | `from_date`, `to_date`, `limit`, `offset` |
| `getPolymarketTrendingStocks` | `GET /polymarket/stocks/v1/trending` | `from_date`, `to_date`, `limit`, `offset`, `type` |
| `getRedditCryptoHealth` | `GET /reddit/crypto/v1/health` |  |
| `getRedditCryptoMarketSentiment` | `GET /reddit/crypto/v1/market-sentiment` | `from_date`, `to_date` |
| `getRedditCryptoStats` | `GET /reddit/crypto/v1/stats` |  |
| `getRedditCryptoToken` | `GET /reddit/crypto/v1/token/{symbol}` | `symbol`*, `from_date`, `to_date` |
| `getRedditCryptoTokenMentions` | `GET /reddit/crypto/v1/token/{symbol}/mentions` | `symbol`*, `from_date`, `to_date`, `limit`, `offset`, `include_inherited` |
| `getRedditCryptoTrending` | `GET /reddit/crypto/v1/trending` | `from_date`, `to_date`, `limit`, `offset` |
| `getRedditMarketSentiment` | `GET /reddit/stocks/v1/market-sentiment` | `from_date`, `to_date` |
| `getRootHealth` | `GET /health` |  |
| `getStats` | `GET /reddit/stocks/v1/stats` |  |
| `getStockExplanation` | `GET /reddit/stocks/v1/stock/{ticker}/explain` | `ticker`* |
| `getStockRawMentions` | `GET /reddit/stocks/v1/stock/{ticker}/mentions` | `ticker`*, `from_date`, `to_date`, `limit`, `offset`, `include_inherited` |
| `getStockSentiment` | `GET /reddit/stocks/v1/stock/{ticker}` | `ticker`*, `from_date`, `to_date` |
| `getTrendingCountries` | `GET /reddit/stocks/v1/trending/countries` | `from_date`, `to_date`, `limit`, `offset` |
| `getTrendingSectors` | `GET /reddit/stocks/v1/trending/sectors` | `from_date`, `to_date`, `limit`, `offset` |
| `getTrendingStocks` | `GET /reddit/stocks/v1/trending` | `from_date`, `to_date`, `limit`, `offset`, `type` |
| `getXHealth` | `GET /x/stocks/v1/health` |  |
| `getXMarketSentiment` | `GET /x/stocks/v1/market-sentiment` | `from_date`, `to_date` |
| `getXStats` | `GET /x/stocks/v1/stats` |  |
| `getXStockExplanation` | `GET /x/stocks/v1/stock/{ticker}/explain` | `ticker`* |
| `getXStockRawMentions` | `GET /x/stocks/v1/stock/{ticker}/mentions` | `ticker`*, `from_date`, `to_date`, `limit`, `offset` |
| `getXStockSentiment` | `GET /x/stocks/v1/stock/{ticker}` | `ticker`*, `from_date`, `to_date` |
| `getXTrendingCountries` | `GET /x/stocks/v1/trending/countries` | `from_date`, `to_date`, `limit`, `offset` |
| `getXTrendingSectors` | `GET /x/stocks/v1/trending/sectors` | `from_date`, `to_date`, `limit`, `offset` |
| `getXTrendingStocks` | `GET /x/stocks/v1/trending` | `from_date`, `to_date`, `limit`, `offset`, `type` |
| `searchNewsStocks` | `GET /news/stocks/v1/search` | `q`*, `limit` |
| `searchPolymarketStocks` | `GET /polymarket/stocks/v1/search` | `q`*, `limit` |
| `searchRedditCrypto` | `GET /reddit/crypto/v1/search` | `q`*, `limit` |
| `searchStocks` | `GET /reddit/stocks/v1/search` | `q`*, `limit` |
| `searchXStocks` | `GET /x/stocks/v1/search` | `q`*, `limit` |
