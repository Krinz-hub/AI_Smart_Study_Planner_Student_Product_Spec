from typing import Optional
from pydantic import BaseModel, Field


class UserSettingsResponse(BaseModel):
    user_id: str
    theme: str = "system"
    study_time_preference: str = "evening"
    daily_capacity_minutes: int = 180
    notifications_enabled: bool = True
    ai_tutor_mode: str = "socratic"
    sound_enabled: bool = True
    reduced_motion: bool = False


class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    study_time_preference: Optional[str] = None
    daily_capacity_minutes: Optional[int] = Field(default=None, ge=30, le=720)
    notifications_enabled: Optional[bool] = None
    ai_tutor_mode: Optional[str] = None
    sound_enabled: Optional[bool] = None
    reduced_motion: Optional[bool] = None
