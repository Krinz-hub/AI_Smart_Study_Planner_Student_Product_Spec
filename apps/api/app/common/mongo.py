import logging
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.common.config import get_settings
from app.common.logging import get_logger

logging.getLogger("pymongo").setLevel(logging.WARNING)

logger = get_logger("mongo")
settings = get_settings()

_mongo_client: Optional[AsyncIOMotorClient] = None


import asyncio

def get_mongo_client() -> AsyncIOMotorClient:
    """Returns Motor AsyncIO client matching the active event loop."""
    global _mongo_client
    if _mongo_client is not None:
        try:
            client_loop = _mongo_client.get_io_loop()
            if client_loop is None or client_loop.is_closed():
                _mongo_client = None
            else:
                try:
                    running_loop = asyncio.get_running_loop()
                    if client_loop != running_loop:
                        _mongo_client = None
                except RuntimeError:
                    pass
        except Exception:
            _mongo_client = None

    if _mongo_client is None:
        # Check if running in mock mode or test environment
        if os.getenv("USE_MOCK_MONGO", "false").lower() == "true":
            try:
                import mongomock_motor
                logger.info("mongo_init_mock", reason="USE_MOCK_MONGO enabled")
                _mongo_client = mongomock_motor.AsyncMongoMockClient()
                return _mongo_client
            except ImportError:
                pass

        logger.info("mongo_client_init", uri=settings.MONGODB_URI, database=settings.MONGODB_DATABASE)
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=3000,
        )
    return _mongo_client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency / service helper to get MongoDB database."""
    client = get_mongo_client()
    return client[settings.MONGODB_DATABASE]


async def init_mongo_indices(db: Optional[AsyncIOMotorDatabase] = None) -> None:
    """Initializes required unique and query indexes on MongoDB collections."""
    if db is None:
        db = get_mongo_db()

    try:
        # users collection
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("email", unique=True)

        # onboarding collection
        await db.student_onboarding.create_index("user_id", unique=True)

        # preferences collection
        await db.student_preferences.create_index("user_id", unique=True)

        # notes summaries collection
        await db.notes_summaries.create_index("document_id")
        await db.notes_summaries.create_index("user_id")

        logger.info("mongo_indices_initialized")
    except Exception as e:
        logger.warning("mongo_indices_init_error", error=str(e))


async def ping_mongo() -> bool:
    """Checks MongoDB connection health."""
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return True
    except Exception as e:
        logger.warning("mongo_health_ping_failed", error=str(e))
        return False


async def close_mongo_connection() -> None:
    """Closes Motor client on application shutdown."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        logger.info("mongo_client_closed")
