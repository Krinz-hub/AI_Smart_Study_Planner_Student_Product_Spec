from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.config import get_settings
from app.common.logging import setup_logging, get_logger
from app.common.middleware import RequestIdAndLoggingMiddleware
from app.common.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.api.router import api_router
from app.api.v1.health import router as health_router
import app.common.all_models  # noqa: F401

setup_logging()
logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app_startup",
        app_name=settings.APP_NAME,
        env=settings.APP_ENV,
        version=settings.VERSION,
    )
    from app.common.mongo import init_mongo_indices, close_mongo_connection
    await init_mongo_indices()
    yield
    await close_mongo_connection()
    logger.info("app_shutdown", app_name=settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Smart Study Planner API",
        description="Evidence-driven adaptive learning platform API",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Middleware registration (Order: RequestId -> CORS)
    app.add_middleware(RequestIdAndLoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Mount API Routers
    app.include_router(api_router)
    # Also mount top-level health checks for root probes (/health, /ready)
    app.include_router(health_router)

    return app


app = create_app()
