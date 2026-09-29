from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserProfileResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.auth.service import (
    register_user,
    authenticate_user,
    request_password_reset,
    reset_password,
    get_user_onboarding_state,
)
from app.auth.dependencies import get_current_user, rate_limit_auth
from app.common.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, token = await register_user(db, req)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, token = await authenticate_user(db, req)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    # In stateless JWT, logout signals client clearance and can be extended with Valkey blacklist
    return {
        "status": "success",
        "message": "Successfully logged out",
    }


@router.get(
    "/me",
    response_model=UserProfileResponse,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    onboarding = await get_user_onboarding_state(current_user.id)
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        onboarding_step=onboarding.get("current_step", "ACADEMIC_TYPE"),
        created_at=current_user.created_at,
    )


@router.post(
    "/password-reset/request",
    dependencies=[Depends(rate_limit_auth)],
)
async def password_reset_request(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    token = await request_password_reset(db, req.email)
    # Never reveal whether an email exists
    resp: Dict[str, Any] = {
        "status": "success",
        "message": "If this email exists in our records, a reset token has been issued.",
    }
    # In development mode, provide token for testing convenience
    if token:
        resp["dev_token"] = token
    return resp


@router.post(
    "/password-reset/confirm",
    dependencies=[Depends(rate_limit_auth)],
)
async def password_reset_confirm(
    req: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await reset_password(db, req.token, req.new_password)
    return {
        "status": "success",
        "message": "Password has been successfully updated. Please log in with your new credentials.",
    }
