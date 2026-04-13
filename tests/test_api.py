"""FastAPI endpoint tests using httpx AsyncClient."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from packages.agent_core.models.agent_output import FinalRecommendation


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Return a mock Redis client that always reports a cache miss."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_recommendation():
    return FinalRecommendation(
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        recommendation="BUY",
        confidence=0.82,
        time_horizon="medium_term",
        reasoning="Strong technical setup with positive news catalysts and manageable risk.",
        technical_summary="Bullish EMA alignment with RSI in healthy range.",
        news_summary="Positive earnings expectations ahead.",
        risk_summary="Medium risk with acceptable volatility.",
        target_price=195.0,
        stop_loss=182.0,
    )


@pytest.fixture
def app_client(mock_redis):
    """Return a TestClient with Redis mocked out."""
    import apps.api.app.main as main_module
    main_module.redis_client = mock_redis

    from apps.api.app.main import app
    return TestClient(app, raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_ok(self, app_client):
        response = app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Request validation
# ─────────────────────────────────────────────────────────────────────────────

class TestRequestValidation:
    def test_symbol_normalized_to_uppercase(self, app_client, mock_recommendation):
        with patch(
            "apps.api.app.services.analysis_service.AnalysisService.run_analysis",
            new_callable=AsyncMock,
        ) as mock_run:
            from apps.api.app.schemas.response import AnalysisResponse

            mock_run.return_value = AnalysisResponse(
                analysis_id="test-123",
                symbol="AAPL",
                status="completed",
                created_at=datetime.now(timezone.utc),
                recommendation=mock_recommendation,
            )
            response = app_client.post(
                "/api/v1/analyze/sync",
                json={"symbol": "aapl", "timeframe": "1d"},
            )
        assert response.status_code == 200
        # The validator normalizes to uppercase
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get("symbol") == "AAPL" or call_args.args[0] == "AAPL"

    def test_invalid_timeframe_rejected(self, app_client):
        response = app_client.post(
            "/api/v1/analyze/sync",
            json={"symbol": "AAPL", "timeframe": "1w"},  # "1w" not in enum
        )
        assert response.status_code == 422

    def test_empty_symbol_rejected(self, app_client):
        response = app_client.post(
            "/api/v1/analyze/sync",
            json={"symbol": ""},
        )
        assert response.status_code == 422

    def test_symbol_allows_exchange_suffix(self):
        from apps.api.app.schemas.request import AnalysisRequest

        request = AnalysisRequest(symbol="reliance.ns")

        assert request.symbol == "RELIANCE.NS"


# ─────────────────────────────────────────────────────────────────────────────
# Cache behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheEndpoints:
    def test_get_cached_analysis_404_when_missing(self, app_client):
        response = app_client.get("/api/v1/analysis/AAPL")
        assert response.status_code == 404

    def test_delete_cache_returns_204(self, app_client):
        response = app_client.delete("/api/v1/analysis/AAPL")
        assert response.status_code == 204

    def test_get_cached_analysis_returns_data(self, app_client, mock_redis, mock_recommendation):
        from apps.api.app.schemas.response import AnalysisResponse

        cached_response = AnalysisResponse(
            analysis_id="cached-001",
            symbol="AAPL",
            status="completed",
            created_at=datetime.now(timezone.utc),
            recommendation=mock_recommendation,
            cached=False,
        )
        mock_redis.get = AsyncMock(return_value=cached_response.model_dump_json())

        response = app_client.get("/api/v1/analysis/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["cached"] is True
        assert data["recommendation"]["recommendation"] == "BUY"


# ─────────────────────────────────────────────────────────────────────────────
# Async analyze endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestAsyncAnalyzeEndpoint:
    def test_async_analyze_returns_202(self, app_client):
        response = app_client.post(
            "/api/v1/analyze",
            json={"symbol": "MSFT"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["symbol"] == "MSFT"
        assert "analysis_id" in data
