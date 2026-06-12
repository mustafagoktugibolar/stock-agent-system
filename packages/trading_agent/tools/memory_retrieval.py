"""pgvector-based memory retrieval and storage tools.

Uses OpenAI text-embedding-3-small to embed market context, then performs
cosine similarity search against the agent_memories table via pgvector.

All DB operations use psycopg2 (sync) so these @tools never need to bridge
into an asyncio event loop — which would conflict with the event loop already
running in the trading cycle job.
"""

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import psycopg2
import psycopg2.extras
from langchain_core.tools import tool
from openai import OpenAI

# Allow passing uuid.UUID values directly to psycopg2 query parameters
psycopg2.extras.register_uuid()

from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_openai_client: Optional[OpenAI] = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _sync_conn():
    """Return a synchronous psycopg2 connection."""
    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return psycopg2.connect(dsn)


@lru_cache(maxsize=256)
def embed_text(text_to_embed: str) -> tuple[float, ...]:
    """Return a cached embedding vector for the given text."""
    settings = get_settings()
    response = _get_openai_client().embeddings.create(
        model=settings.embedding_model,
        input=text_to_embed,
    )
    return tuple(response.data[0].embedding)


def _embed_as_list(text_to_embed: str) -> list[float]:
    return list(embed_text(text_to_embed))


def _retrieve_memories_sync(
    embedding: list[float],
    symbol: str,
    limit: int,
    min_similarity: float,
) -> list[dict]:
    """Run the pgvector similarity query using psycopg2."""
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    query = """
        SELECT
            id::text,
            symbol,
            market_regime,
            outcome_label,
            situation_text,
            decision_text,
            outcome_text,
            lessons_text,
            pnl_pct,
            confidence_at_decision,
            1 - (embedding <=> %s::vector) AS similarity
        FROM agent_memories
        WHERE symbol = %s
          AND 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
    """

    memories: list[dict] = []
    try:
        conn = _sync_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (embedding_str, symbol, embedding_str, min_similarity, embedding_str, limit))
            memories = [dict(row) for row in cur.fetchall()]

            # Fallback: cross-symbol search if not enough symbol-specific memories
            if len(memories) < limit:
                cross_query = """
                    SELECT
                        id::text,
                        symbol,
                        market_regime,
                        outcome_label,
                        situation_text,
                        decision_text,
                        outcome_text,
                        lessons_text,
                        pnl_pct,
                        confidence_at_decision,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM agent_memories
                    WHERE symbol != %s
                      AND 1 - (embedding <=> %s::vector) > %s
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                """
                cur.execute(cross_query, (
                    embedding_str, symbol, embedding_str,
                    min_similarity, embedding_str, limit - len(memories),
                ))
                memories.extend([dict(row) for row in cur.fetchall()])
        conn.close()
    except Exception as e:
        logger.warning("[memory_retrieval] DB query failed: %s", e)

    # Convert Decimal/non-serializable types
    for m in memories:
        for k, v in m.items():
            if hasattr(v, "__float__"):
                m[k] = float(v)
    return memories


def _store_memory_sync(
    symbol: str,
    market_regime: str,
    outcome_label: str,
    situation_text: str,
    decision_text: str,
    outcome_text: str,
    lessons_text: str,
    embedding: list[float],
    pnl_pct: Optional[float],
    confidence_at_decision: Optional[float],
    reflection_id: Optional[str],
) -> str:
    memory_id = uuid.uuid4()
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
    now = datetime.now(timezone.utc)

    insert_query = """
        INSERT INTO agent_memories (
            id, reflection_id, symbol, market_regime, outcome_label,
            situation_text, decision_text, outcome_text, lessons_text,
            embedding, pnl_pct, confidence_at_decision, created_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s::vector, %s, %s, %s
        )
    """
    try:
        conn = _sync_conn()
        with conn.cursor() as cur:
            cur.execute(insert_query, (
                memory_id,
                uuid.UUID(reflection_id) if reflection_id else None,
                symbol, market_regime, outcome_label,
                situation_text, decision_text, outcome_text, lessons_text,
                embedding_str, pnl_pct, confidence_at_decision, now,
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("[memory_retrieval] Store failed: %s", e)
        return json.dumps({"error": str(e)})

    return json.dumps({"memory_id": str(memory_id), "created_at": now.isoformat()})


# Keep _run_async for any callers outside of tools (e.g. reflection_job)
def _run_async(coro):
    import asyncio
    import concurrent.futures
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


@tool
def retrieve_similar_memories(
    context_text: str,
    symbol: str,
    limit: int = 5,
    min_similarity: float = 0.75,
) -> str:
    """Retrieve past market situations similar to the current context via pgvector.

    Args:
        context_text: Description of current market state (price, regime, signals, sentiment)
        symbol: Stock ticker to prioritize (also falls back to cross-symbol search)
        limit: Maximum number of memories to return
        min_similarity: Minimum cosine similarity threshold (0.0–1.0)

    Returns:
        JSON list of memory dicts including situation_text, outcome_label, lessons_text, similarity
    """
    settings = get_settings()
    embedding = _embed_as_list(context_text)
    memories = _retrieve_memories_sync(
        embedding,
        symbol,
        limit or settings.memory_retrieval_limit,
        min_similarity or settings.memory_similarity_threshold,
    )
    logger.info("Retrieved %d memories for %s (min_sim=%.2f)", len(memories), symbol, min_similarity)
    return json.dumps(memories)


@tool
def store_memory(
    symbol: str,
    market_regime: str,
    outcome_label: str,
    situation_text: str,
    decision_text: str,
    outcome_text: str,
    lessons_text: str,
    pnl_pct: Optional[float] = None,
    confidence_at_decision: Optional[float] = None,
    reflection_id: Optional[str] = None,
) -> str:
    """Store a trade outcome as a retrievable memory in the pgvector database.

    Args:
        symbol: Stock ticker
        market_regime: trending_bull | trending_bear | ranging | high_volatility
        outcome_label: profitable | loss | breakeven
        situation_text: Human-readable description of the market state at decision time
        decision_text: What was decided and the key reasoning
        outcome_text: What actually happened (price movement, PnL)
        lessons_text: Specific actionable rule derived from this trade
        pnl_pct: Realized PnL as a percentage
        confidence_at_decision: Model confidence at the time of the trade
        reflection_id: UUID string of the TradeReflection row that generated this memory
    """
    embedding = _embed_as_list(situation_text + " | " + decision_text)
    result = _store_memory_sync(
        symbol=symbol,
        market_regime=market_regime,
        outcome_label=outcome_label,
        situation_text=situation_text,
        decision_text=decision_text,
        outcome_text=outcome_text,
        lessons_text=lessons_text,
        embedding=embedding,
        pnl_pct=pnl_pct,
        confidence_at_decision=confidence_at_decision,
        reflection_id=reflection_id,
    )
    if "error" not in json.loads(result):
        logger.info("Stored memory for %s (outcome=%s)", symbol, outcome_label)
    return result
