"""
Global test configuration and fixtures.
Uses a separate test PostgreSQL database.
Mocks Redis and Celery — no real queue in tests.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = settings.database_url.replace("/churnguard", "/churnguard_test")

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db(setup_database: None) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── Mock Redis ────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_redis():
    mock_r = AsyncMock()
    mock_r.ping.return_value = True
    mock_r.get.return_value = None
    mock_r.setex.return_value = True
    mock_r.delete.return_value = 1
    with patch("app.core.cache._redis_client", mock_r):
        yield mock_r


# ── Mock Celery ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_celery():
    with patch("app.tasks.batch_predict.process_batch_job") as mock_task:
        mock_task.delay = MagicMock(return_value=MagicMock(id=str(uuid.uuid4())))
        yield mock_task


# ── Mock pipeline ─────────────────────────────────────────────────────────────
@pytest.fixture
def mock_pipeline():
    from app.ml.pipeline import PipelineManager, pipeline_manager

    PipelineManager.reset()
    with patch.object(pipeline_manager, "_pipeline", MagicMock()):
        with patch.object(pipeline_manager, "_version_tag", "test-v1"):
            with patch.object(
                pipeline_manager,
                "predict",
                return_value=[0.85, 0.15, 0.92],
            ):
                yield pipeline_manager


# ── HTTP client ───────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── User factories ────────────────────────────────────────────────────────────
def make_user(role: UserRole = UserRole.API_USER, **kwargs: Any) -> dict[str, Any]:
    return {
        "email": kwargs.get("email", f"user-{uuid.uuid4().hex[:8]}@test.com"),
        "password": kwargs.get("password", "TestPass1"),
        "role": role.value,
    }


def auth_headers(user_id: uuid.UUID, role: UserRole) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "role": role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("AdminPass1"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def api_user(db: AsyncSession) -> User:
    user = User(
        email=f"api-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("ApiPass1"),
        role=UserRole.API_USER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    return auth_headers(admin_user.id, UserRole.ADMIN)


@pytest_asyncio.fixture
def api_user_headers(api_user: User) -> dict[str, str]:
    return auth_headers(api_user.id, UserRole.API_USER)
