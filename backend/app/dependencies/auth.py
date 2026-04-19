import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import TTL_USER_PROFILE, cache_get, cache_set, user_profile_key
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    #db: Annotated[AsyncSession, Depends(lambda: None)],  # overridden below
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_access_token(token)
    user_id_str = str(payload.get("sub", ""))

    # Try cache first
    cached = await cache_get(user_profile_key(user_id_str))
    if cached:
        user = User(
            id=uuid.UUID(cached["id"]),
            email=cached["email"],
            role=UserRole(cached["role"]),
            is_active=cached["is_active"],
            is_verified=cached["is_verified"],
        )
        return user

    # DB lookup
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id_str))
    if user is None:
        raise UnauthorizedException("User not found")

    # Cache for subsequent requests
    await cache_set(
        user_profile_key(user_id_str),
        {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
        TTL_USER_PROFILE,
    )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise UnauthorizedException("Account is disabled")
    return current_user


def require_role(*roles: UserRole) -> Callable:
    """
    Factory: returns a FastAPI Dependency that enforces role membership.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.ML_ENGINEER))
    Zero-trust: role re-verified from DB/cache on every request.
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"Required role(s): {[r.value for r in roles]}. "
                f"Your role: {current_user.role.value}"
            )
        return current_user

    return role_checker
