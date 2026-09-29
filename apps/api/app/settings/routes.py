from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.common.mongo import get_mongo_db
from app.settings.schemas import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> UserSettingsResponse:
    """Retrieves user application preferences from MongoDB product store."""
    record = await mongo_db.user_settings.find_one({"user_id": str(current_user.id)})
    if not record:
        return UserSettingsResponse(user_id=str(current_user.id))

    return UserSettingsResponse(
        user_id=str(current_user.id),
        theme=record.get("theme", "system"),
        study_time_preference=record.get("study_time_preference", "evening"),
        daily_capacity_minutes=record.get("daily_capacity_minutes", 180),
        notifications_enabled=record.get("notifications_enabled", True),
        ai_tutor_mode=record.get("ai_tutor_mode", "socratic"),
        sound_enabled=record.get("sound_enabled", True),
        reduced_motion=record.get("reduced_motion", False),
    )


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    req: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> UserSettingsResponse:
    """Updates user application preferences in MongoDB product store."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await mongo_db.user_settings.update_one(
        {"user_id": str(current_user.id)},
        {"$set": update_data, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    record = await mongo_db.user_settings.find_one({"user_id": str(current_user.id)})
    return UserSettingsResponse(
        user_id=str(current_user.id),
        theme=record.get("theme", "system"),
        study_time_preference=record.get("study_time_preference", "evening"),
        daily_capacity_minutes=record.get("daily_capacity_minutes", 180),
        notifications_enabled=record.get("notifications_enabled", True),
        ai_tutor_mode=record.get("ai_tutor_mode", "socratic"),
        sound_enabled=record.get("sound_enabled", True),
        reduced_motion=record.get("reduced_motion", False),
    )
