import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Depends, Header, Request
import jwt

from app.auth.models import User
from app.auth.security import decode_access_token
from app.auth.service import get_user_by_id
from app.common.config import get_settings
from app.common.database import get_db
from app.common.errors import UnauthorizedException, AppException
from sqlalchemy.ext.asyncio import AsyncSession


class InMemoryRateLimiter:
    """Sliding-window rate limiter for sensitive authentication routes."""
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.hits: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str):
        now = time.time()
        window_start = now - 60.0
        self.hits[key] = [t for t in self.hits[key] if t > window_start]
        if len(self.hits[key]) >= self.rpm:
            raise AppException(
                message="Rate limit exceeded. Please wait a moment before trying again.",
                code="TOO_MANY_REQUESTS",
                status_code=429,
            )
        self.hits[key].append(now)


auth_rate_limiter = InMemoryRateLimiter(requests_per_minute=100)


def rate_limit_auth(request: Request):
    settings = get_settings()
    if settings.APP_ENV in ("testing", "test"):
        return
    client_ip = request.client.host if request.client else "unknown"
    auth_rate_limiter.check(client_ip)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization:
        raise UnauthorizedException("Authentication credentials were not provided")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Invalid authorization header format. Expected 'Bearer <token>'")

    token = parts[1]

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Session has expired. Please log in again.")
    except (jwt.InvalidTokenError, Exception):
        raise UnauthorizedException("Could not validate credentials")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token subject")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed user identifier in token")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise UnauthorizedException("User no longer exists")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive")

    return user
