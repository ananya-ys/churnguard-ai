"""
Smoke tests — run against a live deployed instance.
These tests verify the critical happy paths after deployment.

Usage:
    BASE_URL=http://localhost:8000 pytest tests/smoke/ -v
"""

import os

import pytest
from httpx import AsyncClient

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")


@pytest.fixture
async def smoke_client() -> AsyncClient:
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        yield client


class TestSmokeHealth:
    async def test_health_endpoint_returns_200(self, smoke_client: AsyncClient):
        resp = await smoke_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "database" in data
        assert "redis" in data

    async def test_health_database_ok(self, smoke_client: AsyncClient):
        resp = await smoke_client.get("/health")
        assert resp.json()["database"] == "ok"

    async def test_health_redis_ok(self, smoke_client: AsyncClient):
        resp = await smoke_client.get("/health")
        assert resp.json()["redis"] == "ok"


class TestSmokeAuth:
    async def test_register_and_login_cycle(self, smoke_client: AsyncClient):
        import uuid

        email = f"smoke-{uuid.uuid4().hex[:8]}@test.com"
        password = "SmokeTest1"

        # Register
        reg = await smoke_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "role": "api_user"},
        )
        assert reg.status_code == 201, f"Register failed: {reg.text}"

        # Login
        login = await smoke_client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert token

        # Me
        me = await smoke_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email

    async def test_docs_accessible(self, smoke_client: AsyncClient):
        resp = await smoke_client.get("/docs")
        # Either 200 (dev/staging) or 404 (production — docs disabled)
        assert resp.status_code in (200, 404)

    async def test_request_id_present_on_every_response(
        self, smoke_client: AsyncClient
    ):
        resp = await smoke_client.get("/health")
        assert "X-Request-ID" in resp.headers

    async def test_401_on_protected_route_no_token(self, smoke_client: AsyncClient):
        resp = await smoke_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
