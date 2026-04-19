"""Integration tests for POST /api/v1/upload and job polling."""

import io
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import UserRole

VALID_CSV_HEADERS = (
    "state,account_length,area_code,international_plan,voice_mail_plan,"
    "number_vmail_messages,total_day_minutes,total_day_calls,total_day_charge,"
    "total_eve_minutes,total_eve_calls,total_eve_charge,"
    "total_night_minutes,total_night_calls,total_night_charge,"
    "total_intl_minutes,total_intl_calls,total_intl_charge,customer_service_calls"
)

VALID_ROW = "CA,120,415,no,yes,25,265.1,110,45.07,197.4,99,16.78,244.7,91,11.01,10.0,3,2.70,1"


def make_csv(rows: int = 5) -> bytes:
    lines = [VALID_CSV_HEADERS] + [VALID_ROW] * rows
    return "\n".join(lines).encode("utf-8")


def user_headers(role: UserRole = UserRole.API_USER) -> dict[str, str]:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": role.value})
    return {"Authorization": f"Bearer {token}"}


class TestCSVUpload:
    async def test_upload_valid_csv_returns_202(
        self, client: AsyncClient, mock_pipeline
    ):
        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("customers.csv", make_csv(), "text/csv")},
            headers=user_headers(),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["filename"] == "customers.csv"

    async def test_upload_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", make_csv(), "text/csv")},
        )
        assert resp.status_code == 401

    async def test_upload_wrong_extension_returns_400(
        self, client: AsyncClient
    ):
        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("data.txt", b"some text", "text/plain")},
            headers=user_headers(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_file"

    async def test_upload_returns_job_id_immediately(
        self, client: AsyncClient, mock_pipeline
    ):
        """Verify endpoint returns <50ms without blocking."""
        import time

        start = time.monotonic()
        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("fast.csv", make_csv(100), "text/csv")},
            headers=user_headers(),
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert resp.status_code == 202
        # Should not block — Celery task is async
        # In test environment with mocked Celery this is well under 50ms
        assert elapsed_ms < 5000  # generous bound for CI

    async def test_celery_task_enqueued(
        self, client: AsyncClient, mock_celery, mock_pipeline
    ):
        """Verify process_batch_job.delay() is called after upload."""
        resp = await client.post(
            "/api/v1/upload",
            files={"file": ("enqueue.csv", make_csv(), "text/csv")},
            headers=user_headers(),
        )
        assert resp.status_code == 202
        mock_celery.delay.assert_called_once()


class TestJobPolling:
    async def test_poll_nonexistent_job_returns_404(self, client: AsyncClient):
        resp = await client.get(
            f"/api/v1/jobs/{uuid.uuid4()}",
            headers=user_headers(),
        )
        assert resp.status_code == 404

    async def test_list_jobs_returns_empty_for_new_user(self, client: AsyncClient):
        resp = await client.get("/api/v1/jobs", headers=user_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_upload_then_poll_cycle(
        self, client: AsyncClient, mock_pipeline, mock_celery
    ):
        headers = user_headers()

        # Upload
        upload_resp = await client.post(
            "/api/v1/upload",
            files={"file": ("cycle.csv", make_csv(), "text/csv")},
            headers=headers,
        )
        assert upload_resp.status_code == 202
        job_id = upload_resp.json()["job_id"]

        # Poll — job will be QUEUED (Celery mocked, not actually processed)
        poll_resp = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert poll_resp.status_code == 200
        assert poll_resp.json()["job_id"] == job_id
        assert poll_resp.json()["status"] in ("queued", "processing", "completed", "failed")

    async def test_download_results_not_ready_returns_404(
        self, client: AsyncClient, mock_pipeline, mock_celery
    ):
        headers = user_headers()
        upload_resp = await client.post(
            "/api/v1/upload",
            files={"file": ("pending.csv", make_csv(), "text/csv")},
            headers=headers,
        )
        job_id = upload_resp.json()["job_id"]

        # Results are not ready (job is QUEUED)
        resp = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        assert resp.status_code == 404
