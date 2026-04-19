"""Integration tests for auth endpoints."""

import pytest
from httpx import AsyncClient


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "password": "NewPass1", "role": "api_user"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["role"] == "api_user"
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@test.com", "password": "DupPass1", "role": "api_user"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.json()["error"] == "conflict"

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@test.com", "password": "short", "role": "api_user"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "ValidPass1"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "logintest@test.com", "password": "LoginPass1"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "logintest@test.com", "password": "LoginPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrongpw@test.com", "password": "CorrectPass1"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "wrongpw@test.com", "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "ghost@test.com", "password": "GhostPass1"},
        )
        assert resp.status_code == 401


class TestMe:
    async def test_me_authenticated(self, client: AsyncClient, api_user_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=api_user_headers)
        assert resp.status_code == 200
        assert "email" in resp.json()

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer garbage.token.here"}
        )
        assert resp.status_code == 401
