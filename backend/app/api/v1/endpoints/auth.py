from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies.auth import get_current_active_user
from app.dependencies.db import DBSession
from app.models.user import User
from app.schemas.auth import Token, UserRegister, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: UserRegister,
    db: DBSession,
    request: Request,
) -> UserResponse:
    service = AuthService(db)
    user = await service.register_user(
        payload, ip_address=request.client.host if request.client else None
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
    request: Request,
) -> Token:
    service = AuthService(db)
    return await service.login_user(
        email=form_data.username,
        password=form_data.password,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
