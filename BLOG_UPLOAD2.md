# Multi-Agent Real-Time Stock Analysis and Decision Support System — Technical Report

**Upload #2 | SEN4018 Semester Project | May 2026**

---

## Overview

Since our first post, the system has moved from concept to a fully running implementation. This report covers the technical architecture, the frameworks and data sources we use, and each team member's responsibilities.

---

## Technology Stack

**Backend**
- **Python 3.11** — primary language
- **FastAPI** — async HTTP API layer
- **LangGraph** — multi-agent orchestration framework; models the agent pipeline as a compiled `StateGraph`
- **LangChain / LangChain-OpenAI** — LLM bindings and tool decorators
- **OpenAI model via LangChain** — configurable LLM backbone for supervisor, judge, trading decision, advisor, and sentiment tasks
- **pandas-ta** — technical indicator library (RSI, MACD, Bollinger Bands, ADX, ATR, EMAs)
- **yfinance** — free market data and news fallback
- **Alpaca Markets API** — primary OHLCV data source
- **Redis** — analysis result caching (TTL-based, default 5 minutes)
- **PostgreSQL** — persistent storage for analysis records and backtests
- **SQLAlchemy** — ORM layer

**Frontend**
- **Vue 3 + Vite** — SPA framework with `<script setup>` composition API
- **Pinia** — state management store
- **TypeScript** — all service types mirror backend Pydantic models

---

## Datasets and Data Sources

| Source | What it provides |
|--------|-----------------|
| Alpaca Markets API | Real-time and historical OHLCV bars (primary) |
| yfinance | OHLCV fallback, company news, financial statements, company profile |
| OpenAI API | Sentiment scoring of news headlines, final synthesis |
| SPY (S&P 500 ETF) | Benchmark data for beta calculation |

No static dataset files are used — all data is fetched live at analysis time.

---

## System Architecture

The system is organized into three layers:

```
packages/agent_core/   ← all business logic; no FastAPI dependency
packages/shared/       ← settings, logger, database session
apps/api/              ← FastAPI HTTP layer, Redis cache, streaming endpoints
apps/frontend/         ← Vue 3 SPA
apps/trader/           ← scheduled/manual paper-trading cycles
packages/trading_agent/ ← trade decision, Alpaca tools, reflection, backtest
```

### LangGraph Agent Pipeline

The heart of the system is a compiled `StateGraph` where four specialist agents run **in parallel**, then converge to a supervisor:

```
START
  ├── technical_agent    (market data + indicators)
  ├── news_agent         (news fetch + sentiment)
  ├── risk_agent         (volatility, VaR, beta vs. SPY)
  └── fundamentals_agent (company profile + financial ratios)
        ↓ (all four finish)
  supervisor_agent       (structured LLM output → BUY/HOLD/SELL)
        ↓
  llm_judge              (independent LLM evaluation)
        ↓
END
```

All four specialist agents are **deterministic** (no LLM involved) — they call their tools directly and return typed Pydantic objects. The supervisor agent calls the LLM with `with_structured_output(FinalRecommendation)` to guarantee a schema-validated result. The final `llm_judge` node then independently reviews that recommendation.

### AgentState — the shared contract

Every node reads from and writes back to a single `AgentState` TypedDict:

```python
class AgentState(TypedDict):
    symbol: str
    timeframe: str          # "1d", "1h", "5m"
    language: str           # "en" or "tr"
    messages: Annotated[Sequence[AnyMessage], add_messages]   # append-only
    technical_analysis: Optional[TechnicalOutput]
    news_analysis: Optional[NewsOutput]
    risk_analysis: Optional[RiskOutput]
    company_profile: Optional[CompanyProfile]
    financial_statements: Optional[FinancialStatements]
    final_recommendation: Optional[FinalRecommendation]
    errors: Annotated[list[str], _append_errors]              # append-only
```

Errors in any individual agent are collected without crashing the pipeline — the supervisor synthesizes whatever analyses are available.

---

## Agent Details

### 1. Technical Agent

Fetches 6 months of daily OHLCV data and computes:
- **RSI (14)** — oversold (<30) / overbought (>70) signal
- **MACD Histogram** — momentum direction signal
- **EMA 20 / EMA 50** — trend bias (price position relative to moving averages)
- **ATR (14)** — volatility / stop-loss sizing
- **ADX (14)** — trend strength (adjusts confidence score up/down)
- **Support & Resistance** — derived from 60-bar highs/lows

Outputs: `TechnicalOutput` with `overall_technical_bias` (bullish / neutral / bearish) and a `confidence` score.

### 2. News Agent

Fetches up to 10 recent articles from yfinance and passes them to a single batched OpenAI call that scores each headline on a −1 to +1 scale. Aggregates into an `overall_sentiment` label and `sentiment_score`. Confidence scales with article count.

### 3. Risk Agent

Fetches 1 year of daily data for both the target symbol and SPY. Computes:
- **Annualized Volatility** — classifies risk level (low / medium / high / very_high)
- **Daily VaR 95%** — estimated one-day downside
- **Maximum Drawdown** — worst peak-to-trough decline
- **Sharpe Ratio** — risk-adjusted return
- **Beta vs. SPY** — market sensitivity
- **30-day Return** — recent momentum

### 4. Fundamentals Agent

Uses yfinance to retrieve company profile (sector, market cap, P/E, 52-week range) and financial statements (income statement, balance sheet, cash flow). Computes derived ratios: gross margin, net margin, ROE, ROA, debt-to-equity, current ratio, revenue growth YoY, and FCF margin. No LLM is involved.

### 5. Supervisor Agent

The synthesis node. It receives JSON-serialized outputs from all four specialist agents and calls the configured OpenAI model with a structured output schema:

```python
class FinalRecommendation(BaseModel):
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: float          # 0.0–1.0
    time_horizon: str
    reasoning: str
    technical_summary: str
    news_summary: str
    risk_summary: str
    key_factors: list[str]
    risks: list[str]
```

Supports bilingual output (English / Turkish) via a language directive in the system prompt.

### 6. Portfolio Advisor

A separate streaming chatbot built on top of the same LLM infrastructure. It takes user preferences (risk tolerance, investment horizon, preferred sectors) and streams personalized stock/ETF recommendations. Tickers mentioned in responses use a `$TICKER` format that the frontend parses into clickable analysis triggers.

---

## Evaluation Framework

The project includes a `RecommendationEvaluator` class with three evaluation methods:

1. **Directional accuracy** — compares the recommendation (BUY/HOLD/SELL) against actual subsequent price movement. A BUY is "correct" if the stock rose >2%, a SELL if it fell >2%, a HOLD if it stayed within ±5%.

2. **Consistency scoring** — runs the full pipeline multiple times on the same symbol and measures the `consistency_ratio` (fraction of runs that agree on the majority recommendation) plus confidence standard deviation. Detects non-determinism.

3. **Agent agreement scoring** — checks whether technical bias, news sentiment, and risk level all point in the same direction as the final recommendation. Returns a 0–1 agreement score.

This constitutes the "LLM-in-the-loop" evaluation required by the course: the supervisor LLM produces the final decision, and the evaluator checks whether that decision was coherent across all input signals and accurate against real price outcomes.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/analyze/sync` | Full analysis, blocks until done (~10–30 s) |
| POST | `/api/v1/analyze` | Async analysis trigger |
| GET | `/api/v1/analysis/{symbol}` | Retrieve cached analysis |
| DELETE | `/api/v1/analysis/{symbol}` | Invalidate cached analysis |
| WS | `/api/v1/ws/analysis/{symbol}` | Real-time analysis progress |
| POST | `/api/v1/chat/{symbol}` | Context-aware analysis chatbot |
| GET | `/api/v1/stocks/search` | Symbol autocomplete |
| POST | `/api/v1/advisor` | Portfolio advisor stream |
| GET | `/api/v1/trader/status` | Paper-trading scheduler and risk limits |
| POST | `/api/v1/trader/cycle/run` | Trigger one trading cycle immediately |
| POST | `/api/v1/trader/backtest` | Start historical backtest |
| GET | `/api/v1/trader/backtest/{id}` | Poll backtest progress/result |

---

## Frontend Features

- **Stock Screener** — watchlist with live analysis triggers
- **Analysis Dashboard** — tabbed panels for Technical, News, Risk, and Financials
- **Recommendation Card** — BUY/HOLD/SELL with confidence score and key factors
- **AI Analysis Chatbot** — ask follow-up questions about the current analysis
- **Portfolio Advisor** — conversational stock discovery based on user preferences
- **Language toggle** — full Turkish / English support

---

## Team Responsibilities

| Team Member | Responsibilities |
|-------------|-----------------|
| **Mustafa Göktuğ İbolar** (2101483) | System architecture, LangGraph graph design, technical agent, news agent, risk agent, fundamentals agent, supervisor agent, evaluation framework, FastAPI layer, Redis caching, all backend tools, deployment |
| **Kaan Akgül** (2004221) | Frontend components (Vue 3 SPA), project documentation |

---

## Current Status Update

Upload #3 expands this system into the complete final version:

- The LLM judge is now part of the live analysis graph.
- The full Vue dashboard includes Analysis and Trading pages.
- The trading module has a separate `trade_decision_agent`, virtual execution mode, Alpaca paper-order mode, position monitoring, reflection, and pgvector memory.
- Historical backtesting uses Alpaca market data for the selected historical dates, but simulates trades locally. Backtest trades do not appear in Alpaca Orders; only live paper-trading cycles can create Alpaca paper orders.

---

*This report is part of the SEN4018 Semester Project at Bahçeşehir University.*
