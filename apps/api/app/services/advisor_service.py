from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from apps.api.app.schemas.advisor import UserPreferences
from apps.api.app.schemas.chat import ChatMessage
from packages.shared.config.settings import get_settings
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)

_HORIZON_LABEL = {"short": "short-term (days to weeks)", "medium": "medium-term (months)", "long": "long-term (years)"}
_RISK_LABEL = {"low": "low risk / capital preservation", "medium": "moderate risk / balanced growth", "high": "high risk / aggressive growth"}


class AdvisorService:
    def __init__(self) -> None:
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.5,
            streaming=True,
        )

    async def stream_chat(
        self,
        message: str,
        history: list[ChatMessage],
        preferences: UserPreferences,
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        lang_instruction = (
            "IMPORTANT: You MUST write your ENTIRE response in Turkish."
            if language == "tr"
            else "Write your response in English."
        )

        sector_str = ", ".join(preferences.sectors) if preferences.sectors else "no specific sector preference"
        prefs_context = (
            f"- Risk tolerance: {_RISK_LABEL.get(preferences.risk_tolerance, preferences.risk_tolerance)}\n"
            f"- Sectors of interest: {sector_str}\n"
            f"- Investment horizon: {_HORIZON_LABEL.get(preferences.horizon, preferences.horizon)}"
        )

        system_prompt = (
            "You are an expert investment advisor AI. You help users discover stocks and ETFs to invest in "
            "based on their goals and preferences. You do NOT have real-time price data, so focus on "
            "fundamental reasoning (sector outlook, company quality, risk profile).\n\n"
            f"{lang_instruction}\n\n"
            "USER PREFERENCES:\n"
            f"{prefs_context}\n\n"
            "IMPORTANT FORMATTING RULE: Whenever you recommend a specific stock or ETF, always write the "
            "ticker symbol using the $TICKER format (e.g. $XOM, $CVX, $NEE). This lets the user click the "
            "ticker to run a live analysis. Do not omit the $ prefix for any ticker recommendation.\n\n"
            "Keep responses concise, structured with bullet points or short paragraphs, and directly address "
            "the user's question. Use Markdown formatting for readability."
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
            logger.error("Advisor generation failed: %s", e)
            yield f"\n\n*Error: Failed to generate response ({e}).*"
