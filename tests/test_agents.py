"""Unit and integration tests for agent tools and the LangGraph graph."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_ohlcv_json(n: int = 60) -> str:
    """Generate minimal synthetic OHLCV data for testing."""
    import random
    price = 150.0
    bars = []
    for i in range(n):
        change = random.uniform(-2, 2)
        price = max(50, price + change)
        bars.append(
            {
                "timestamp": f"2024-01-{(i % 28) + 1:02d}T00:00:00Z",
                "open": round(price - 0.5, 2),
                "high": round(price + 1.0, 2),
                "low": round(price - 1.0, 2),
                "close": round(price, 2),
                "volume": random.randint(1_000_000, 10_000_000),
            }
        )
    return json.dumps({"symbol": "TEST", "source": "test", "bars": bars})


def _make_initial_state(symbol: str = "AAPL") -> dict:
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "analysis_id": str(uuid.uuid4()),
        "messages": [],
        "technical_analysis": None,
        "news_analysis": None,
        "risk_analysis": None,
        "final_recommendation": None,
        "current_agent": "start",
        "errors": [],
    }


# ───────────────────────────────────────────────────────���─────────────────────
# Tool unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateTechnicalIndicators:
    def test_returns_expected_keys(self):
        from packages.agent_core.tools.indicators import calculate_technical_indicators

        ohlcv = _make_ohlcv_json(n=220)
        result = json.loads(calculate_technical_indicators.invoke({"ohlcv_json": ohlcv}))

        assert "rsi" in result
        assert "macd_line" in result
        assert "bb_upper" in result
        assert "ema_20" in result
        assert "symbol_price" in result

    def test_rsi_in_valid_range(self):
        from packages.agent_core.tools.indicators import calculate_technical_indicators

        ohlcv = _make_ohlcv_json(n=60)
        result = json.loads(calculate_technical_indicators.invoke({"ohlcv_json": ohlcv}))

        rsi = result.get("rsi")
        if rsi is not None:
            assert 0 <= rsi <= 100

    def test_insufficient_data_returns_error(self):
        from packages.agent_core.tools.indicators import calculate_technical_indicators

        ohlcv = _make_ohlcv_json(n=5)  # fewer than 30 bars
        result = json.loads(calculate_technical_indicators.invoke({"ohlcv_json": ohlcv}))

        assert "error" in result


class TestCalculateRiskMetrics:
    def test_returns_expected_keys(self):
        from packages.agent_core.tools.risk_metrics import calculate_risk_metrics

        ohlcv = _make_ohlcv_json(n=120)
        result = json.loads(calculate_risk_metrics.invoke({"ohlcv_json": ohlcv}))

        assert "annualized_volatility" in result
        assert "max_drawdown" in result
        assert "sharpe_ratio" in result
        assert "var_95_daily" in result

    def test_max_drawdown_is_negative_or_zero(self):
        from packages.agent_core.tools.risk_metrics import calculate_risk_metrics

        ohlcv = _make_ohlcv_json(n=120)
        result = json.loads(calculate_risk_metrics.invoke({"ohlcv_json": ohlcv}))

        md = result.get("max_drawdown")
        if md is not None:
            assert md <= 0


class TestFetchRecentNews:
    @patch("yfinance.Ticker")
    def test_returns_articles_list(self, mock_ticker_cls):
        from packages.agent_core.tools.news_fetcher import fetch_recent_news

        mock_ticker = MagicMock()
        mock_ticker.news = [
            {
                "title": "Apple reports record earnings",
                "publisher": "Reuters",
                "link": "https://example.com/1",
                "providerPublishTime": 1710000000,
            },
            {
                "title": "Apple unveils new product line",
                "publisher": "Bloomberg",
                "link": "https://example.com/2",
                "providerPublishTime": 1710086400,
            },
        ]
        mock_ticker_cls.return_value = mock_ticker

        result = json.loads(fetch_recent_news.invoke({"symbol": "AAPL", "max_articles": 5}))

        assert result["symbol"] == "AAPL"
        assert len(result["articles"]) == 2
        assert result["articles"][0]["title"] == "Apple reports record earnings"

    @patch("yfinance.Ticker")
    def test_empty_news_returns_empty_list(self, mock_ticker_cls):
        from packages.agent_core.tools.news_fetcher import fetch_recent_news

        mock_ticker = MagicMock()
        mock_ticker.news = []
        mock_ticker_cls.return_value = mock_ticker

        result = json.loads(fetch_recent_news.invoke({"symbol": "XYZ"}))
        assert result["articles"] == []


class TestAnalyzeNewsSentiment:
    @pytest.fixture(autouse=True)
    def _clear_settings_cache(self):
        from packages.shared.config.settings import get_settings

        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @patch("openai.OpenAI")
    def test_gpt5_model_uses_max_completion_tokens(self, mock_openai_cls, monkeypatch):
        from packages.agent_core.tools.sentiment import analyze_news_sentiment

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "sentiments": [0.4],
                            "overall_score": 0.4,
                            "overall_label": "positive",
                            "key_themes": ["earnings"],
                            "summary": "NVDA news is positive.",
                        }
                    )
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        news_json = json.dumps(
            {"articles": [{"title": "Nvidia rises after strong earnings", "source": "Reuters"}]}
        )
        result = json.loads(
            analyze_news_sentiment.invoke({"news_json": news_json, "symbol": "NVDA"})
        )

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert result["symbol"] == "NVDA"
        assert kwargs["model"] == "gpt-5.4-mini"
        assert kwargs["max_completion_tokens"] == 512
        assert "max_tokens" not in kwargs
        assert "temperature" not in kwargs

    @patch("openai.OpenAI")
    def test_non_reasoning_model_keeps_low_temperature(self, mock_openai_cls, monkeypatch):
        from packages.agent_core.tools.sentiment import analyze_news_sentiment

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "sentiments": [0.2],
                            "overall_score": 0.2,
                            "overall_label": "positive",
                            "key_themes": ["product demand"],
                            "summary": "AAPL news is positive.",
                        }
                    )
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        news_json = json.dumps(
            {"articles": [{"title": "Apple demand improves", "source": "Bloomberg"}]}
        )
        analyze_news_sentiment.invoke({"news_json": news_json, "symbol": "AAPL"})

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["max_completion_tokens"] == 512
        assert "max_tokens" not in kwargs
        assert kwargs["temperature"] == 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Graph structure test (compile-only, no LLM calls)
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphCompilation:
    def test_graph_compiles_without_error(self):
        from packages.agent_core.orchestrator.graph import create_analysis_graph

        graph = create_analysis_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        from packages.agent_core.orchestrator.graph import create_analysis_graph

        graph = create_analysis_graph()
        node_names = set(graph.get_graph().nodes.keys())
        assert "technical_agent" in node_names
        assert "news_agent" in node_names
        assert "risk_agent" in node_names
        assert "supervisor_agent" in node_names


# ─────────────────────────────────────────────────────────────────────────────
# Evaluator tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRecommendationEvaluator:
    def _make_recommendation(self, rec: str, confidence: float = 0.8) -> object:
        from packages.agent_core.models.agent_output import FinalRecommendation

        return FinalRecommendation(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            recommendation=rec,
            confidence=confidence,
            time_horizon="medium_term",
            reasoning="Test reasoning.",
            technical_summary="Bullish.",
            news_summary="Positive.",
            risk_summary="Low risk.",
        )

    def test_buy_correct_when_price_rises(self):
        from packages.agent_core.evaluation.evaluator import RecommendationEvaluator

        evaluator = RecommendationEvaluator()
        rec = self._make_recommendation("BUY")
        score = evaluator.score_accuracy(rec, entry_price=100.0, exit_price=106.0)
        assert score.correct is True
        assert score.pct_change == 6.0

    def test_buy_wrong_when_price_falls(self):
        from packages.agent_core.evaluation.evaluator import RecommendationEvaluator

        evaluator = RecommendationEvaluator()
        rec = self._make_recommendation("BUY")
        score = evaluator.score_accuracy(rec, entry_price=100.0, exit_price=94.0)
        assert score.correct is False

    def test_consistency_with_unanimous_recs(self):
        from packages.agent_core.evaluation.evaluator import RecommendationEvaluator

        evaluator = RecommendationEvaluator()
        recs = [self._make_recommendation("BUY", 0.8 + i * 0.02) for i in range(5)]
        score = evaluator.measure_agent_consistency(recs)
        assert score.majority_recommendation == "BUY"
        assert score.consistency_ratio == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Integration test (requires real API keys — marked separately)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_full_graph_invocation_aapl():
    """End-to-end test: run the full analysis graph for AAPL.

    Requires OPENAI_API_KEY to be set.  Run with:
        pytest tests/test_agents.py -m integration
    """
    from packages.agent_core.orchestrator.graph import create_analysis_graph

    graph = create_analysis_graph()
    state = _make_initial_state("AAPL")
    result = graph.invoke(state)

    assert result["final_recommendation"] is not None
    assert result["final_recommendation"].recommendation in ("BUY", "HOLD", "SELL")
    assert 0.0 <= result["final_recommendation"].confidence <= 1.0
