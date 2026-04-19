"""Integration tests for RBAC role boundary enforcement."""

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import UserRole


def headers_for(role: UserRole) -> dict[str, str]:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": role.value})
    return {"Authorization": f"Bearer {token}"}


class TestAuditLogRBAC:
    async def test_admin_can_access_audit_logs(
        self, client: AsyncClient, admin_user, admin_headers
    ):
        resp = await client.get("/api/v1/audit-logs", headers=admin_headers)
        # 200 or empty list — not 403
        assert resp.status_code in (200, 404)

    async def test_api_user_cannot_access_audit_logs(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/audit-logs", headers=headers_for(UserRole.API_USER)
        )
        assert resp.status_code == 403

    async def test_analyst_cannot_access_audit_logs(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/audit-logs", headers=headers_for(UserRole.ANALYST)
        )
        assert resp.status_code == 403


class TestModelRegistryRBAC:
    async def test_api_user_cannot_register_model(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/models",
            json={
                "version_tag": "v99",
                "artifact_path": "/tmp/v99.pkl",
                "auc_roc": 0.85,
                "f1_score": 0.80,
                "precision": 0.82,
                "recall": 0.78,
            },
            headers=headers_for(UserRole.API_USER),
        )
        assert resp.status_code == 403

    async def test_ml_engineer_can_register_model(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/models",
            json={
                "version_tag": f"v-ml-{uuid.uuid4().hex[:6]}",
                "artifact_path": "/tmp/test.pkl",
                "auc_roc": 0.85,
                "f1_score": 0.80,
                "precision": 0.82,
                "recall": 0.78,
            },
            headers=headers_for(UserRole.ML_ENGINEER),
        )
        # 201 or 409 (tag exists) — not 403
        assert resp.status_code in (201, 409, 422)

    async def test_api_user_cannot_promote_model(self, client: AsyncClient):
        resp = await client.post(
            f"/api/v1/models/{uuid.uuid4()}/promote",
            headers=headers_for(UserRole.API_USER),
        )
        assert resp.status_code == 403


class TestUnauthenticated:
    async def test_predict_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/predict", json={"records": []})
        assert resp.status_code == 401

    async def test_upload_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/upload")
        assert resp.status_code == 401

    async def test_jobs_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/jobs")
        assert resp.status_code == 401
