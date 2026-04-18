"""Bridge between the FastAPI layer and the LangGraph agent core."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from apps.api.app.schemas.response import AnalysisResponse
from packages.agent_core.orchestrator.graph import get_analysis_graph
from packages.agent_core.state.agent_state import AgentState
from packages.shared.config.settings import get_settings
from packages.shared.db.models.analysis import Analysis
from packages.shared.db.session import get_session_factory
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


class AnalysisService:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._graph = get_analysis_graph()

    def _cache_key(self, symbol: str, timeframe: str, language: str) -> str:
        return f"analysis:{symbol.upper()}:{timeframe}:{language}"

    def _build_response(self, state: AgentState, analysis_id: str) -> AnalysisResponse:
        return AnalysisResponse(
            analysis_id=analysis_id,
            symbol=state["symbol"],
            status="completed" if not state.get("errors") else "failed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            recommendation=state.get("final_recommendation"),
            company_profile=state.get("company_profile"),
            financial_statements=state.get("financial_statements"),
            technical_analysis=state.get("technical_analysis"),
            news_analysis=state.get("news_analysis"),
            risk_analysis=state.get("risk_analysis"),
            errors=state.get("errors", []),
            cached=False,
        )

    async def _save_to_db(self, response: AnalysisResponse, timeframe: str) -> None:
        rec = response.recommendation
        try:
            async with get_session_factory()() as session:
                row = Analysis(
                    id=uuid.UUID(response.analysis_id),
                    symbol=response.symbol,
                    timeframe=timeframe,
                    status=response.status,
                    recommendation=rec.recommendation if rec else None,
                    confidence=rec.confidence if rec else None,
                    target_price=rec.target_price if rec else None,
                    stop_loss=rec.stop_loss if rec else None,
                    time_horizon=rec.time_horizon if rec else None,
                    reasoning=rec.reasoning if rec else None,
                    technical_json=(
                        response.technical_analysis.model_dump(mode="json")
                        if response.technical_analysis else None
                    ),
                    news_json=(
                        response.news_analysis.model_dump(mode="json")
                        if response.news_analysis else None
                    ),
                    risk_json=(
                        response.risk_analysis.model_dump(mode="json")
                        if response.risk_analysis else None
                    ),
                    errors=response.errors or [],
                    created_at=response.created_at,
                    completed_at=response.completed_at,
                )
                session.add(row)
                await session.commit()
                logger.info("Saved analysis %s to DB", response.analysis_id)
        except Exception as e:
            logger.warning("DB write failed for %s: %s", response.analysis_id, e)

    async def run_analysis(
        self,
        symbol: str,
        timeframe: str = "1d",
        language: str = "en",
        force_refresh: bool = False,
    ) -> AnalysisResponse:
        """Run the full multi-agent analysis and return a structured response.

        Checks Redis cache first (unless force_refresh=True). The LangGraph
        invocation runs in a thread pool executor since the tools are synchronous.
        Results are persisted to PostgreSQL after every fresh run.
        """
        symbol = symbol.upper().strip()
        cache_key = self._cache_key(symbol, timeframe, language)
        settings = get_settings()

        if not force_refresh:
            try:
                cached_raw = await self._redis.get(cache_key)
                if cached_raw:
                    response = AnalysisResponse.model_validate_json(cached_raw)
                    response = response.model_copy(update={"cached": True})
                    logger.info("Cache hit for %s/%s", symbol, timeframe)
                    return response
            except Exception as e:
                logger.warning("Cache read failed for %s: %s", symbol, e)

        analysis_id = str(uuid.uuid4())
        logger.info("Starting analysis %s for %s/%s", analysis_id, symbol, timeframe)

        initial_state: AgentState = {
            "symbol": symbol,
            "timeframe": timeframe,
            "language": language,
            "analysis_id": analysis_id,
            "messages": [],
            "technical_analysis": None,
            "news_analysis": None,
            "risk_analysis": None,
            "company_profile": None,
            "financial_statements": None,
            "final_recommendation": None,
            "current_agent": "start",
            "errors": [],
        }

        result_state = initial_state.copy()
        
        try:
            async for output in self._graph.astream(initial_state, stream_mode=["updates", "values"]):
                mode, payload = output
                if mode == "values":
                    result_state = payload
                elif mode == "updates":
                    for node_name, _ in payload.items():
                        await self._redis.publish(
                            f"analysis_progress:{symbol}",
                            json.dumps({"agent": node_name, "status": "completed"})
                        )


        except Exception as e:
            logger.error("Graph invocation failed for %s: %s", symbol, e)
            return AnalysisResponse(
                analysis_id=analysis_id,
                symbol=symbol,
                status="failed",
                created_at=datetime.now(timezone.utc),
                errors=[f"Graph execution failed: {e}"],
            )

        response = self._build_response(result_state, analysis_id)

        await self._save_to_db(response, timeframe)

        try:
            await self._redis.setex(
                cache_key,
                settings.analysis_cache_ttl,
                response.model_dump_json(),
            )
        except Exception as e:
            logger.warning("Cache write failed for %s: %s", symbol, e)

        return response
