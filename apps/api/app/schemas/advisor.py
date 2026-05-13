from typing import Literal

from pydantic import BaseModel

from apps.api.app.schemas.chat import ChatMessage


class UserPreferences(BaseModel):
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    sectors: list[str] = []
    horizon: Literal["short", "medium", "long"] = "medium"


class AdvisorRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    preferences: UserPreferences = UserPreferences()
    language: Literal["en", "tr"] = "en"
