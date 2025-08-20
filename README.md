## Project overview

I built a Slack-enabled trading helper that scores and evaluates tickers using multiple market data sources and technical factors. The goal was to create a lightweight engine that can:
- fetch historical market data,
- compute technical indicators (EMA, ATR, RSI, etc.),
- score tickers for swing trading using a composite of liquidity, volatility, momentum and technical flags,
- serialize picks as `Ticker` objects, and
- integrate with external services (Slack for notifications and Alpaca for live trading) when I want to.

This repo is a work-in-progress; below I explain what I did, how the pieces connect, what I left unfinished, how to run the code, and the next steps I recommend.

## What I built (high level)

- `app/` - integrations and data sources
  - `market_data.py` — Twelve Data wrapper `get_bars_12data(symbol, limit=60)` to fetch OHLCV daily bars.
  - `alpaca_client.py` — Alpaca REST wrappers (account, place orders, and a `get_bars` helper).
  - other helper modules (Slack integration, config, fmp client) live here.

- `ticker_engine/` - core scoring and ticker model
  - `factors.py` — indicator computations and factor scoring functions (ATR, RSI, momentum, liquidity, etc.), plus `get_factor_data(symbol)` that assembles the inputs for scoring.
  - `scorer.py` — composes factor outputs into a `swing_score` and will hold other composite scores (e.g., `composite_score`).
  - `ticker.py` — `Ticker` class used to represent a candidate (serializable via `to_dict` / `from_dict`).
  - `portfolio.py`, `strategy.py`, `queue.py`, `scorer.py` — scaffolding for strategy, allocation, and ranking.

- `tasks/` — scheduler for periodic runs
- `main.py`, `run_tasks.py`, `test.py` — top-level scripts I used while developing and testing.

## How the pieces connect (data & control flow)

1. Data source: `app.market_data.get_bars_12data(symbol)` fetches daily OHLCV bars (Twelve Data by default). I also have Alpaca wrappers in `app/alpaca_client.py` and a small `app/test.py` that uses `yfinance` for local testing.
2. Factor assembly: `ticker_engine.factors.get_factor_data(symbol)` fetches bars, computes EMA50/EMA200, RSI and ATR, and returns a dictionary of values used by scoring functions.
3. Scoring: `ticker_engine.scorer.swing_score(symbol)` calls `get_factor_data(symbol)` and computes a weighted score using `liquidity_score`, `rel_strength_vs_xlk`, `atr_volatility_score`, `momentum_score`, `technical_flag_score`, and `rsi_score`.
4. Representation: `ticker_engine.ticker.Ticker` stores symbol, score and timestamps for tracking and later serialization.
5. Orchestration: a scheduler in `tasks/scheduler.py` can call scoring routines on a list of tickers, push results to a queue or Slack alerts, or instruct `alpaca_client` to place trades.

## Environment and secrets

I used environment variables loaded via `python-dotenv`. To run the project you'll want to set:

- `TWELVE_DATA_API_KEY` — Twelve Data API key (used by `app.market_data.get_bars_12data`).
- `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `APCA_API_BASE_URL`, `APCA_API_DATA_URL` — Alpaca credentials for trading/data (optional while developing).
- Slack webhook or bot tokens (if you enable `app/slack.py` notifications).

Keep these secrets out of the repo (I keep them in a local `.env` file for dev). The repo already uses `dotenv.load_dotenv()` in several modules.

## Current status — where I left off (what's done vs TODO)

Done
- Core factor functions implemented in `ticker_engine/factors.py`: ATR, RSI computation, momentum, liquidity, technical flag, and `get_factor_data` that assembles the ingredients for scoring.
- `swing_score` implemented in `ticker_engine/scorer.py` as a weighted combination of factors.
- `Ticker` model updated to include `date_bought` and serialization.
- `app/market_data.py` created as a Twelve Data wrapper and `app/alpaca_client.py` includes Alpaca helpers.

Known issues / TODOs (what I would want to finish next)
- Duplicate / shadowed function: `ticker_engine/factors.py` currently imports `get_bars_12data` from `app.market_data` but also defines a local `get_bars_12data(...)` at the bottom of the same file. The local definition shadows the import, which is confusing. I should keep a single canonical implementation in `app/market_data.py` and remove the duplicate.
- Function signature mismatch: `get_factor_data` calls `get_bars_12data(symbol, timeframe="1Day", limit=60)`, but both implementations expect `(symbol, limit=60)` and do not accept `timeframe` — that will raise a TypeError if executed. Fix: remove the `timeframe=` kw or standardize the signature in `app/market_data.py` to accept `timeframe`.
- `composite_score` in `ticker_engine/scorer.py` is a TODO.
- Add unit tests for `compute_rsi`, `compute_atr`, `get_factor_data`, and the scoring functions (happy path + edge cases).
- Add a small integration test that runs scoring on a cheap ETF (e.g., `XLK`) to validate end-to-end data fetching and scoring (mock Twelve Data where appropriate).

