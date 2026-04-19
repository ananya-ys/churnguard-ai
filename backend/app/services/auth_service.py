from datetime import timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Token, UserRegister

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._user_repo = UserRepository(db)
        self._audit_repo = AuditLogRepository(db)
        self._db = db

    async def register_user(
        self,
        payload: UserRegister,
        ip_address: str | None = None,
    ) -> User:
        if await self._user_repo.exists_by_email(payload.email):
            raise ConflictException(f"Email '{payload.email}' is already registered")

        hashed = hash_password(payload.password)
        user = await self._user_repo.create(
            email=payload.email,
            hashed_password=hashed,
            role=payload.role,
        )

        await self._audit_repo.create(
            action=AuditAction.REGISTER,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip_address=ip_address,
        )
        await self._db.commit()

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def login_user(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> Token:
        user = await self._user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("Account is disabled")

        expire_seconds = settings.access_token_expire_minutes * 60
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

        await self._audit_repo.create(
            action=AuditAction.LOGIN,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip_address=ip_address,
        )
        await self._db.commit()

        logger.info("user_login", user_id=str(user.id), role=user.role.value)
        return Token(access_token=token, token_type="bearer", expires_in=expire_seconds)
