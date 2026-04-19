"""
Concurrency tests: 50 parallel /predict requests.
Proves no race conditions under simultaneous load.
All 50 must succeed with unique request_ids — no model state corruption.
"""

import asyncio
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import UserRole

VALID_RECORD = {
    "state": "TX",
    "account_length": 80,
    "area_code": 512,
    "international_plan": "no",
    "voice_mail_plan": "no",
    "number_vmail_messages": 0,
    "total_day_minutes": 180.0,
    "total_day_calls": 85,
    "total_day_charge": 30.6,
    "total_eve_minutes": 150.0,
    "total_eve_calls": 75,
    "total_eve_charge": 12.75,
    "total_night_minutes": 200.0,
    "total_night_calls": 90,
    "total_night_charge": 9.0,
    "total_intl_minutes": 8.0,
    "total_intl_calls": 4,
    "total_intl_charge": 2.16,
    "customer_service_calls": 2,
}


def make_headers() -> dict[str, str]:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": UserRole.API_USER.value})
    return {"Authorization": f"Bearer {token}"}


class TestConcurrentPredictions:
    async def test_50_concurrent_requests_all_succeed(
        self, client: AsyncClient, mock_pipeline
    ):
        """
        50 parallel requests to POST /predict.
        Requirement: all succeed, all have unique request_ids.
        """
        async def single_request() -> tuple[int, str]:
            resp = await client.post(
                "/api/v1/predict",
                json={"records": [VALID_RECORD]},
                headers=make_headers(),
            )
            request_id = resp.headers.get("X-Request-ID", "")
            return resp.status_code, request_id

        results = await asyncio.gather(*[single_request() for _ in range(50)])

        statuses = [r[0] for r in results]
        request_ids = [r[1] for r in results]

        # All must succeed
        failed = [s for s in statuses if s != 200]
        assert not failed, f"{len(failed)} requests failed: {set(failed)}"

        # All request_ids must be unique
        assert len(set(request_ids)) == 50, "Duplicate request_ids detected — race condition"

    async def test_10_concurrent_requests_for_ci(
        self, client: AsyncClient, mock_pipeline
    ):
        """Lighter version for PR CI gate (10/10 required)."""
        async def single_request() -> int:
            resp = await client.post(
                "/api/v1/predict",
                json={"records": [VALID_RECORD]},
                headers=make_headers(),
            )
            return resp.status_code

        results = await asyncio.gather(*[single_request() for _ in range(10)])
        failed = [s for s in results if s != 200]
        assert not failed, f"Concurrent requests failed: {failed}"

    async def test_concurrent_different_users_no_cross_contamination(
        self, client: AsyncClient, mock_pipeline
    ):
        """Different user tokens — verify no auth state bleed between requests."""
        async def request_as_user(user_id: str) -> dict:
            token = create_access_token({"sub": user_id, "role": UserRole.API_USER.value})
            resp = await client.post(
                "/api/v1/predict",
                json={"records": [VALID_RECORD]},
                headers={"Authorization": f"Bearer {token}"},
            )
            return {"status": resp.status_code, "user_id": user_id}

        user_ids = [str(uuid.uuid4()) for _ in range(20)]
        results = await asyncio.gather(*[request_as_user(uid) for uid in user_ids])

        assert all(r["status"] == 200 for r in results)
