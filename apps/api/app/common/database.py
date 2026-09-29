from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from app.common.config import get_settings
from app.common.logging import get_logger

logger = get_logger("database")
settings = get_settings()

# Normalize connection string for async engine:
# psycopg 3 async dialect: postgresql+psycopg_async:// or postgresql+psycopg://
# In SQLAlchemy 2.0, postgresql+psycopg:// works asynchronously when using AsyncEngine
db_url = settings.DATABASE_URL

engine = create_async_engine(
    db_url,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
