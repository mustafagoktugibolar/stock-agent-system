import json
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from apps.api.app.schemas.chat import ChatMessage
from apps.api.app.schemas.response import AnalysisResponse
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.4,
            streaming=True,
        )

    async def _get_cached_analysis(self, symbol: str, timeframe: str, language: str) -> str:
        """Fetch the analysis from Redis and format it as a markdown context block."""
        cache_key = f"analysis:{symbol}:{timeframe}:{language}"
        raw = await self.redis.get(cache_key)

        if not raw:
            return "No prior analysis found for this symbol."

        try:
            analysis = AnalysisResponse.model_validate_json(raw)
        except Exception as e:
            logger.error("Failed to parse cached analysis: %s", e)
            return "Error retrieving analysis."

        context = []
        if analysis.recommendation:
            context.append(f"RECOMMENDATION: {analysis.recommendation.recommendation} ({analysis.recommendation.confidence * 100:.0f}% confidence)")
            context.append(f"TARGET PRICE: {analysis.recommendation.target_price}")
            context.append(f"STOP LOSS: {analysis.recommendation.stop_loss}")
            context.append(f"REASONING: {analysis.recommendation.reasoning}")

        if analysis.company_profile:
            context.append(f"COMPANY INFO: {analysis.company_profile.name} ({analysis.company_profile.sector}) - {analysis.company_profile.description}")

        if analysis.technical_analysis:
            context.append(f"TECHNICALS: {analysis.technical_analysis.summary}")

        if analysis.risk_analysis:
            context.append(f"RISK: {analysis.risk_analysis.summary} (Drawdown: {analysis.risk_analysis.max_drawdown*100:.1f}%)")

        if analysis.news_analysis:
            context.append(f"NEWS SENTIMENT: {analysis.news_analysis.summary}")

        return "\n\n".join(context)

    async def stream_chat(
        self,
        symbol: str,
        message: str,
        history: list[ChatMessage],
        timeframe: str = "1d",
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        
        symbol = symbol.upper().strip()
        context_str = await self._get_cached_analysis(symbol, timeframe, language)

        lang_instruction = "IMPORTANT: You MUST write your ENTIRE response in Turkish." if language == "tr" else "Write your response in English."

        system_prompt = (
            f"You are a helpful, expert AI investment assistant taking questions about {symbol}.\n"
            f"{lang_instruction}\n"
            f"Base your answers SOLELY on the context provided below. If the user asks something "
            f"irrelevant or not covered in the context, politely clarify your limits.\n\n"
            f"--- SYSTEM CONTEXT FOR {symbol} ---\n{context_str}\n-----------------------------------\n\n"
            f"Keep your answers concise, professional, and directly address the user's question. "
            f"Use Markdown formatting (bolding, lists) to make the text easy to read."
        )

        langchain_messages = [SystemMessage(content=system_prompt)]
        
        for msg in history:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            else:
                langchain_messages.append(AIMessage(content=msg.content))

        langchain_messages.append(HumanMessage(content=message))

        try:
            async for chunk in self.llm.astream(langchain_messages):
                yield chunk.content
        except Exception as e:
            logger.error("Chat generation failed: %s", e)
            yield f"\n\n*Error: Failed to generate response ({e}).*"
