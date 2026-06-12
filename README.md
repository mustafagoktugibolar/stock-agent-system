---
title: Multi-Agent Stock Agent System
emoji: 📈
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.18.0
app_file: app.py
pinned: false
license: mit
---

# Multi-Agent Stock Analysis and Paper Trading System

**SEN4018 Semester Project** — an end-to-end AI stock analysis, evaluation, historical backtesting, and Alpaca paper-trading system built with LangGraph, FastAPI, Vue, Redis, PostgreSQL, and Alpaca.

This is an educational decision-support project. It is not investment advice.

## What The System Does

The project has two connected but separate agent pipelines:

```text
Analysis pipeline
Fundamentals + Technical + News + Risk
  -> supervisor_agent
  -> llm_judge
  -> explanation, recommendation, critique

Trading pipeline
market_observer + cached analysis context + memory + portfolio state
  -> trade_decision_agent
  -> virtual execution or Alpaca paper order
```

The key distinction:

- `supervisor_agent` synthesizes the analysis report into a BUY/HOLD/SELL recommendation.
- `trade_decision_agent` makes the actual trading decision. It can use the supervisor report as context when a completed analysis is already cached.
- Historical backtests use Alpaca market data but simulate trades locally. Backtest trades do not appear in Alpaca Orders or Positions.
- Paper trading sends real paper orders to Alpaca only when `TRADING_ENABLED=true`.

## Main Features

- Multi-agent stock analysis with four deterministic specialist agents:
  - Fundamentals
  - Technical
  - News
  - Risk
- LLM supervisor with structured BUY/HOLD/SELL output.
- Independent LLM judge that scores coherence, evidence grounding, and risk alignment.
- Vue trading dashboard with watchlist, recent decisions, open positions, closed trades, reflections, and historical backtests.
- Alpaca historical market data for backtests, with yfinance fallback.
- Alpaca paper order execution for live paper trading mode.
- Redis caching for analysis results and trader state.
- PostgreSQL persistence for analyses, decisions, orders, positions, reflections, and vector memories.
- pgvector-backed memory retrieval for learning from past trade outcomes.
- Gradio app for a lightweight Hugging Face Spaces demo of the analysis pipeline.

## Repository Layout

```text
apps/api/              FastAPI app, REST endpoints, Redis cache, DB initialization
apps/frontend/         Vue 3 + Vite + Pinia dashboard
apps/trader/           Scheduled and manual trading-cycle jobs
apps/worker/           Background worker service
packages/agent_core/   Analysis agents, tools, models, evaluator, LangGraph analysis graph
packages/trading_agent/ Trading agents, Alpaca tools, backtest engine, reflection graph
packages/shared/       Settings, logging, database models and sessions
app.py                 Gradio/Hugging Face Spaces entrypoint
```

## Data Sources

| Source | Used For |
| --- | --- |
| Alpaca Market Data API | Primary OHLCV source for current analysis and historical backtests |
| Alpaca Trading API | Paper account, orders, positions, account state |
| yfinance | Market-data fallback, news, company profile, financial statements |
| OpenAI API | Supervisor, news sentiment, judge, trading decision, reflection, advisor |
| SPY | Benchmark data for beta and market-relative risk |

Alpaca endpoint split:

- Market data: `https://data.alpaca.markets/v2/stocks/bars`
- Paper trading orders: `https://paper-api.alpaca.markets/v2/orders`

## Running Locally

### 1. Configure environment

Create `.env` in the repo root:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_URL=https://data.alpaca.markets

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stockagent
REDIS_URL=redis://localhost:6379/0
ANALYSIS_API_URL=http://localhost:8000

# Safety default: keep false unless you intentionally want Alpaca paper orders.
TRADING_ENABLED=false
TRADING_WATCHLIST=["AAPL","MSFT","NVDA","SPY"]
MIN_DECISION_CONFIDENCE=0.60
MAX_OPEN_POSITIONS=5
MAX_POSITION_SIZE_USD=1000
```

### 2. Full stack with Docker

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 3. Lightweight Gradio demo

The Hugging Face Spaces style app runs only the analysis pipeline:

```bash
python app.py
```

Open `http://localhost:7860`.

## Core API Endpoints

### Analysis

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/analyze/sync` | Run full analysis and wait for the result |
| POST | `/api/v1/analyze` | Trigger async analysis |
| GET | `/api/v1/analysis/{symbol}` | Read cached completed analysis |
| DELETE | `/api/v1/analysis/{symbol}` | Invalidate cached analysis |
| WS | `/api/v1/ws/analysis/{symbol}` | Analysis progress events |
| POST | `/api/v1/chat/{symbol}` | Chat over the current analysis context |
| POST | `/api/v1/advisor` | Portfolio advisor stream |

### Trading

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/trader/status` | Scheduler, watchlist, limits, mode |
| POST | `/api/v1/trader/start` | Start scheduled trading cycle |
| POST | `/api/v1/trader/stop` | Stop scheduled trading cycle |
| POST | `/api/v1/trader/cycle/run` | Run one cycle immediately |
| GET | `/api/v1/trader/decisions` | Recent trade decisions |
| GET | `/api/v1/trader/positions` | Open tracked positions |
| GET | `/api/v1/trader/positions/closed` | Closed tracked positions |
| GET | `/api/v1/trader/reflections` | Recent reflection outputs |
| POST | `/api/v1/trader/backtest` | Start historical backtest |
| GET | `/api/v1/trader/backtest/{id}` | Poll backtest progress/result |

## Trading Modes

### Dry-run / virtual mode

Default mode:

```env
TRADING_ENABLED=false
```

The agent still makes decisions, but orders are not sent to Alpaca. BUY/SELL decisions are stored as virtual positions in PostgreSQL.

### Alpaca paper trading mode

Enable only when you want paper orders in Alpaca:

```env
TRADING_ENABLED=true
```

The trading cycle submits orders to Alpaca using the paper account. These orders appear in the Alpaca dashboard.

Important: market orders submitted outside regular market hours can remain `new` with `filled_qty=0` until the market opens.

## Historical Backtesting

The backtest engine:

1. Pulls daily OHLCV history from Alpaca for the selected range plus a 365-day warmup window.
2. Replays the trading decision agent day by day.
3. Gives the agent only bars up to the current simulated day.
4. Simulates entries/exits locally using daily close/high/low data.
5. Reports equity curve, P&L, drawdown, trade list, and decision counts.

The UI shows the market-data source, for example:

```text
Market data: alpaca (warmup from 2023-09-03)
```

Backtest trades do not create Alpaca dashboard orders because Alpaca paper trading cannot create historical fills.

## Presentation Demo Flow

Recommended live demo:

1. Show the Analysis page and run `NVDA`.
2. Walk through Fundamentals, Technical, News, Risk, Supervisor, and LLM Judge.
3. Switch to Trading Dashboard.
4. Show dry-run vs trading-enabled mode.
5. Run a historical backtest and point out `Market data: alpaca`.
6. Explain why backtest trades are local simulation.
7. If `TRADING_ENABLED=true`, run one live paper cycle and show the order in Alpaca Orders.
8. Close with the safety gates: confidence threshold, max positions, max size, no pyramiding on filled positions, circuit breaker.

See `PRESENTATION_GUIDE.md` for the full speaker script and Q&A.

## Known Limitations

- Backtest uses historical OHLCV and neutral historical news. It does not reconstruct exact past news/fundamental context yet.
- Backtest currently enters at the same day's close after making a day-close decision. A stricter version would enter at the next trading day's open.
- Alpaca paper orders outside market hours may remain `new` until the market opens.
- The current paper-trading flow should avoid duplicate filled positions, but pending Alpaca orders should also be treated as an execution guard before placing repeated BUY orders.

## Disclaimer

This is an educational project for SEN4018. It is not financial advice, and it should not be used for real-money trading without further testing, risk controls, monitoring, and compliance review.
