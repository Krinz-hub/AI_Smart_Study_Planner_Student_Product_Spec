import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, PasswordResetToken
from app.auth.schemas import RegisterRequest, LoginRequest
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    hash_reset_token,
)
from app.common.mongo import get_mongo_db
from app.common.errors import (
    ConflictException,
    UnauthorizedException,
    NotFoundException,
    InvalidRequestException,
)
from app.common.logging import get_logger

logger = get_logger("auth_service")


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(func.lower(User.email) == email.lower().strip())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, req: RegisterRequest) -> Tuple[User, str]:
    clean_email = req.email.lower().strip()
    clean_display = req.display_name.strip()

    # 1. Check PostgreSQL and MongoDB for existing email
    existing_pg = await get_user_by_email(db, clean_email)
    if existing_pg:
        logger.warning("registration_failed_duplicate_email_pg", email=clean_email)
        raise ConflictException("An account with this email address already exists")

    mongo_db = get_mongo_db()
    existing_mongo = await mongo_db.users.find_one({"email": clean_email})
    if existing_mongo:
        logger.warning("registration_failed_duplicate_email_mongo", email=clean_email)
        raise ConflictException("An account with this email address already exists")

    # 2. Hash password and generate shared UUID
    user_id = uuid.uuid4()
    hashed_pw = hash_password(req.password)
    now = datetime.now(timezone.utc)

    # 3. Insert into MongoDB users collection
    await mongo_db.users.insert_one({
        "user_id": str(user_id),
        "email": clean_email,
        "password_hash": hashed_pw,
        "display_name": clean_display,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # 4. Initialize MongoDB onboarding state
    await mongo_db.student_onboarding.insert_one({
        "user_id": str(user_id),
        "current_step": "ACADEMIC_TYPE",
        "academic_type": None,
        "academic_details": {},
        "created_at": now,
        "updated_at": now,
    })

    # 5. Insert PostgreSQL user identity stub
    user = User(
        id=user_id,
        email=clean_email,
        password_hash=hashed_pw,
        display_name=clean_display,
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.error("registration_pg_sync_failed_rolling_back_mongo", error=str(e))
        await mongo_db.users.delete_one({"user_id": str(user_id)})
        await mongo_db.student_onboarding.delete_one({"user_id": str(user_id)})
        raise

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email},
    )

    logger.info("user_registered_successfully", user_id=str(user.id), email=user.email)
    return user, token


async def authenticate_user(db: AsyncSession, req: LoginRequest) -> Tuple[User, str]:
    clean_email = req.email.lower().strip()
    mongo_db = get_mongo_db()

    # 1. Primary check in MongoDB (Source of Truth for auth)
    mongo_user = await mongo_db.users.find_one({"email": clean_email})

    if mongo_user:
        if not verify_password(req.password, mongo_user["password_hash"]):
            logger.warning("login_failed_incorrect_password", email=clean_email)
            raise UnauthorizedException("Invalid email or password")

        if not mongo_user.get("is_active", True):
            logger.warning("login_failed_inactive_user", email=clean_email)
            raise UnauthorizedException("Account is disabled")

        user_id = uuid.UUID(mongo_user["user_id"])
        # Ensure PostgreSQL identity stub exists
        user = await get_user_by_id(db, user_id)
        if not user:
            user = User(
                id=user_id,
                email=clean_email,
                password_hash=mongo_user["password_hash"],
                display_name=mongo_user.get("display_name", clean_email.split("@")[0]),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    else:
        # Fallback to PostgreSQL (legacy pre-migration users)
        user = await get_user_by_email(db, clean_email)
        if not user:
            logger.warning("login_failed_user_not_found", email=clean_email)
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(req.password, user.password_hash):
            logger.warning("login_failed_incorrect_password", user_id=str(user.id))
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            logger.warning("login_failed_inactive_user", user_id=str(user.id))
            raise UnauthorizedException("Account is disabled")

        # Backfill user into MongoDB
        now = datetime.now(timezone.utc)
        await mongo_db.users.update_one(
            {"user_id": str(user.id)},
            {
                "$set": {
                    "user_id": str(user.id),
                    "email": user.email,
                    "password_hash": user.password_hash,
                    "display_name": user.display_name,
                    "is_active": user.is_active,
                    "created_at": user.created_at or now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        await mongo_db.student_onboarding.update_one(
            {"user_id": str(user.id)},
            {
                "$setOnInsert": {
                    "user_id": str(user.id),
                    "current_step": "ACADEMIC_TYPE",
                    "academic_type": None,
                    "academic_details": {},
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email},
    )

    logger.info("user_authenticated_successfully", user_id=str(user.id))
    return user, token


async def request_password_reset(db: AsyncSession, email: str) -> Optional[str]:
    user = await get_user_by_email(db, email)
    if not user:
        # Don't leak whether user exists
        return None

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_record)
    await db.commit()

    logger.info("password_reset_token_created", user_id=str(user.id))
    return raw_token


async def reset_password(db: AsyncSession, raw_token: str, new_password: str) -> User:
    token_hash = hash_reset_token(raw_token)
    stmt = (
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    result = await db.execute(stmt)
    reset_record = result.scalar_one_or_none()

    if not reset_record:
        logger.warning("password_reset_failed_invalid_or_expired_token")
        raise InvalidRequestException("Invalid or expired password reset token")

    user = await get_user_by_id(db, reset_record.user_id)
    if not user:
        raise NotFoundException("User not found")

    user.password_hash = hash_password(new_password)
    reset_record.used = True
    await db.commit()
    await db.refresh(user)

    # Sync updated password to MongoDB
    mongo_db = get_mongo_db()
    await mongo_db.users.update_one(
        {"user_id": str(user.id)},
        {"$set": {"password_hash": user.password_hash, "updated_at": datetime.now(timezone.utc)}}
    )

    logger.info("password_reset_successful", user_id=str(user.id))
    return user


async def get_user_onboarding_state(user_id: uuid.UUID) -> dict:
    """Retrieves current onboarding progression from MongoDB."""
    mongo_db = get_mongo_db()
    doc = await mongo_db.student_onboarding.find_one({"user_id": str(user_id)})
    if not doc:
        return {
            "current_step": "ACADEMIC_TYPE",
            "academic_type": None,
            "academic_details": {},
        }
    return {
        "current_step": doc.get("current_step", "ACADEMIC_TYPE"),
        "academic_type": doc.get("academic_type"),
        "academic_details": doc.get("academic_details", {}),
    }
