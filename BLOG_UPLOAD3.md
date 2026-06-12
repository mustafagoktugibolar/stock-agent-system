# Multi-Agent Stock Analysis and Paper Trading System - Final Report

**Upload #3 | SEN4018 Semester Project | May 2026**

---

## Executive Summary

This project is an end-to-end AI stock analysis and paper-trading system. It combines:

- A multi-agent analysis graph that produces explainable BUY/HOLD/SELL recommendations.
- An independent LLM judge that evaluates the quality of each recommendation.
- A separate trading graph that can turn market observations into paper-trading decisions.
- A historical backtest engine that replays the trading decision agent over past Alpaca market data.
- A Vue dashboard for analysis, backtesting, paper-trading monitoring, and portfolio guidance.

The most important architectural decision is the separation between **analysis** and **execution**. The supervisor agent writes an investment recommendation; the trading agent decides whether to place or simulate a trade using current portfolio state and safety gates.

---

## Technology Stack

**Backend**

- Python 3.11
- FastAPI
- LangGraph
- LangChain and LangChain-OpenAI
- OpenAI structured outputs
- pandas-ta
- yfinance
- Alpaca Market Data API
- Alpaca Trading API
- Redis
- PostgreSQL
- pgvector
- SQLAlchemy

**Frontend**

- Vue 3
- Vite
- TypeScript
- Pinia

**Infrastructure**

- Docker Compose
- PostgreSQL with pgvector
- Redis
- Separate API, worker, trader, and frontend services

---

## System Architecture

The codebase is split into reusable packages and application services:

```text
packages/agent_core/      analysis agents, tools, models, evaluator
packages/trading_agent/   trading graph, trade decision, Alpaca tools, backtest
packages/shared/          settings, logging, database models and sessions
apps/api/                 FastAPI REST API and Redis cache
apps/frontend/            Vue dashboard
apps/trader/              scheduled/manual trading cycle jobs
apps/worker/              background worker service
app.py                    Gradio demo for Hugging Face Spaces
```

There are two main graphs:

```text
Analysis graph
START
  |-> technical_agent
  |-> news_agent
  |-> risk_agent
  |-> fundamentals_agent
        |
        v
  supervisor_agent
        |
        v
  llm_judge
        |
        v
END
```

```text
Trading graph
START
  -> market_observer
  -> analysis_fetcher
  -> memory_retrieval
  -> trade_decision
  -> route:
       execute          -> Alpaca paper order
       virtual_execute  -> simulated DB position
       skip_execution   -> decision only
  -> END
```

---

## Analysis Pipeline

The analysis pipeline is designed like a team of specialists.

### Technical Agent

The technical agent fetches OHLCV data, computes technical indicators, and returns a structured technical view:

- RSI
- MACD histogram
- Bollinger Bands
- ADX
- ATR
- EMA trend signals
- Support and resistance levels

It produces a technical bias: `bullish`, `neutral`, or `bearish`.

### News Agent

The news agent fetches recent headlines and runs a batched OpenAI sentiment pass. It produces:

- Article-level sentiment scores
- Overall sentiment
- Sentiment confidence
- Human-readable summary

### Risk Agent

The risk agent compares the symbol against market benchmark data and computes:

- Annualized volatility
- Value-at-Risk
- Maximum drawdown
- Sharpe ratio
- Beta vs. SPY
- 30-day return

It returns a risk level: `low`, `medium`, `high`, or `very_high`.

### Fundamentals Agent

The fundamentals agent retrieves company profile and financial statements with no LLM call. It computes ratios such as:

- Gross margin
- Net margin
- ROE
- ROA
- Debt-to-equity
- Current ratio
- Revenue growth
- Free cash flow margin

### Supervisor Agent

The supervisor agent receives all specialist outputs and calls the LLM once using structured output. It returns:

- `recommendation`: BUY/HOLD/SELL
- `confidence`
- `target_price`
- `stop_loss`
- `time_horizon`
- `reasoning`
- technical, news, and risk summaries
- signal weights

The supervisor is not the execution agent. It creates an investment analysis recommendation.

### LLM Judge

The judge is a separate LLM node that evaluates the supervisor result. It scores:

- Coherence
- Evidence grounding
- Risk alignment

The judge returns a pass/fail verdict, critique, and suggestions. This gives the system an LLM-in-the-loop evaluation layer.

---

## Trading Pipeline

The trading pipeline is intentionally separate from the analysis pipeline.

The `trade_decision_agent` receives:

- Current market observation
- Portfolio state
- Retrieved trade memories
- Cached analysis context, if available
- Pre-computed deterministic signal inventory

It produces a `TradeDecisionOutput`:

- action: BUY/SELL/HOLD
- confidence
- reasoning
- position size
- stop loss
- take profit
- signal alignment score

The trading graph then applies deterministic execution gates:

- HOLD never executes.
- Circuit breaker blocks execution.
- `TRADING_ENABLED=false` routes to virtual execution.
- `TRADING_ENABLED=true` routes to Alpaca paper orders.
- Minimum confidence must pass.
- Max open position count must pass.
- BUY should not pyramid into an already open filled position.
- Position size is capped.

This means the LLM proposes a structured decision, but deterministic code controls whether it can become a trade.

---

## Supervisor vs. Trade Decision Agent

These two agents are different:

| Agent | Purpose | Output | Used For |
| --- | --- | --- | --- |
| `supervisor_agent` | Synthesizes specialist analysis | `FinalRecommendation` | Report and second opinion |
| `trade_decision_agent` | Makes trading action decision | `TradeDecisionOutput` | Paper trade or simulation |

The trading agent can use the supervisor result as context, but it does not blindly execute the supervisor recommendation.

Why this matters:

- A supervisor BUY might still be skipped if confidence is too low, a position already exists, or portfolio limits are reached.
- A supervisor HOLD can still be considered alongside raw technical signals.
- A cached supervisor analysis gives the trading agent deeper context, but the final trading action belongs to `trade_decision_agent`.

---

## Alpaca Integration

The system uses two Alpaca APIs for two different purposes:

| Alpaca API | Base URL | Purpose |
| --- | --- | --- |
| Market Data API | `https://data.alpaca.markets` | Historical and current OHLCV bars |
| Trading API | `https://paper-api.alpaca.markets` | Paper account, paper orders, positions |

This distinction is critical.

Historical backtests use Alpaca market data, but they do not create Alpaca paper orders. Alpaca paper orders are real-time paper-account actions. Alpaca cannot create historical fills for a 2024 backtest run.

Paper orders appear in Alpaca only when:

```env
TRADING_ENABLED=true
```

and a live/manual trading cycle sends an order through the trading graph.

---

## Historical Backtesting

The backtest engine replays the trading decision agent over historical daily bars.

Process:

1. User chooses symbols, start date, end date, initial capital, and minimum confidence.
2. The backend starts a background backtest and stores progress in Redis.
3. The engine fetches Alpaca daily bars for the selected range plus a 365-day warmup period.
4. Each simulated trading day builds an observation from bars available up to that day only.
5. The trading decision agent produces BUY/SELL/HOLD.
6. The engine simulates fills locally using daily close/high/low bars.
7. The UI displays equity curve, return, drawdown, trade table, and decision counts.

No lookahead rule:

```text
At simulated day D, the agent only receives bars up to D.
Future bars are used later only to evaluate exits and P&L.
```

Current backtest assumptions:

- Historical news is fixed to neutral.
- Analysis context is disabled in backtest to avoid accidentally using present-day fundamentals/news for past decisions.
- Entry uses the same day's close. A stricter future improvement would enter at the next trading day's open.
- Trades are local simulation results; they do not appear in Alpaca Orders.

---

## API Surface

### Analysis API

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/analyze/sync` | Run full analysis and wait |
| POST | `/api/v1/analyze` | Trigger async analysis |
| GET | `/api/v1/analysis/{symbol}` | Retrieve cached analysis |
| DELETE | `/api/v1/analysis/{symbol}` | Invalidate cached analysis |
| WS | `/api/v1/ws/analysis/{symbol}` | Progress updates |
| POST | `/api/v1/chat/{symbol}` | Chat over current analysis |
| POST | `/api/v1/advisor` | Portfolio advisor stream |

### Trading API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/trader/status` | Trader status and limits |
| POST | `/api/v1/trader/start` | Start scheduled trader |
| POST | `/api/v1/trader/stop` | Stop scheduled trader |
| POST | `/api/v1/trader/cycle/run` | Trigger one cycle immediately |
| GET | `/api/v1/trader/decisions` | Recent decisions |
| GET | `/api/v1/trader/positions` | Open tracked positions |
| GET | `/api/v1/trader/positions/closed` | Closed tracked positions |
| GET | `/api/v1/trader/reflections` | Recent reflections |
| POST | `/api/v1/trader/backtest` | Start historical backtest |
| GET | `/api/v1/trader/backtest/{id}` | Poll backtest result |

---

## Frontend

The Vue dashboard has two main pages:

### Analysis Page

- Symbol search
- Multi-agent analysis result
- Recommendation card
- Technical panel
- News panel
- Risk panel
- Fundamentals panel
- LLM judge verdict
- Context-aware chat
- Portfolio advisor

### Trading Page

- Trader status
- Watchlist management
- Manual cycle trigger
- Scheduled trader start/stop
- Risk limits
- Open positions
- Recent decisions
- Closed trade history
- Reflections
- Historical backtest

---

## Demonstration Result Interpretation

When the backtest UI shows:

```text
Market data: alpaca (warmup from 2023-09-03)
```

that means the historical OHLCV data came from Alpaca. It does not mean orders were sent to Alpaca.

When Alpaca Dashboard shows rows under Orders, those came from live/manual paper-trading cycles, not from historical backtests.

If Alpaca Orders show `status=new` and `filled_qty=0`, the order has been submitted but not filled yet. This commonly happens outside regular market hours with DAY market orders.

---

## Safety and Risk Controls

The system includes several safety mechanisms:

- `TRADING_ENABLED=false` by default.
- Minimum decision confidence.
- Maximum open positions.
- Maximum position size in USD.
- No BUY pyramiding into an already tracked open position.
- Daily drawdown circuit breaker.
- Stop loss and take profit suggestions from the LLM decision.
- Position monitor for stop, target, and time-limit exits.
- Reflection memory to learn from closed trades.

Known limitation: pending Alpaca orders should also be treated as an execution guard to avoid repeated BUY orders before fills create positions.

---

## Deployment Options

### Gradio / Hugging Face Spaces

`app.py` runs the analysis graph directly. It is a lightweight demo that requires only `OPENAI_API_KEY`. It does not need PostgreSQL, Redis, FastAPI, or the trading services.

### Full Stack

The Docker Compose deployment runs:

- API
- Frontend
- Trader service
- Worker
- Redis
- PostgreSQL with pgvector

This is the version used for the full dashboard and paper-trading demo.

---

## What We Learned

1. Multi-agent systems need strict state contracts. LangGraph works best when each node owns clear output keys.
2. Deterministic specialist agents are easier to evaluate than LLM-heavy specialists.
3. A single supervisor LLM is easier to control with structured output.
4. A second judge LLM catches weak reasoning and unsupported claims.
5. Trading execution must be separated from analysis. A recommendation is not automatically an order.
6. Historical backtests must avoid present-day information leakage.
7. Alpaca market data and Alpaca paper orders are separate APIs and should be explained separately in demos.

---

## Team Responsibilities

| Team Member | Responsibilities |
| --- | --- |
| Mustafa Göktuğ İbolar (2101483) | System architecture, LangGraph graphs, backend tools, agents, trading module, Alpaca integration, backtest engine, evaluation, FastAPI, Redis/Postgres integration, Docker setup |
| Kaan Akgül (2004221) | Vue frontend components, UI flows, documentation support |

---

## Conclusion

The final system is more than a stock recommendation chatbot. It is a layered agentic architecture with analysis, evaluation, trading decisions, simulation, paper execution, and learning loops.

The most important engineering principle is separation of responsibility:

- Specialist agents gather evidence.
- The supervisor synthesizes an analysis recommendation.
- The judge evaluates the recommendation.
- The trading agent decides whether a trade should happen.
- Deterministic gates decide whether that trade may execute.
- Backtesting evaluates the trading logic without polluting the Alpaca account.

That separation makes the system explainable, testable, and safer to demonstrate.

---

*This report is part of the SEN4018 Semester Project at Bahçeşehir University.*
