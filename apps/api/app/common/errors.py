from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.common.logging import get_logger

logger = get_logger("errors")


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class InvalidRequestException(AppException):
    def __init__(self, message: str = "Invalid request"):
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


def format_error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning("app_exception", code=exc.code, message=exc.message, path=request.url.path)
    return format_error_response(request, exc.code, exc.message, exc.status_code)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_map = {
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return format_error_response(request, code, msg, exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("validation_error", errors=exc.errors(), path=request.url.path)
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = f"{first_error.get('loc', ['parameter'])[-1]}: {first_error.get('msg', 'validation failed')}"
    return format_error_response(request, "VALIDATION_ERROR", msg, status.HTTP_422_UNPROCESSABLE_ENTITY)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), exc_info=True, path=request.url.path)
    return format_error_response(
        request,
        "INTERNAL_ERROR",
        "An unexpected internal error occurred. Please try again.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
