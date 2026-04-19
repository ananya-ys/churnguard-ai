"""Integration tests for POST /api/v1/predict."""

import pytest
from httpx import AsyncClient


VALID_RECORD = {
    "state": "CA",
    "account_length": 120,
    "area_code": 415,
    "international_plan": "no",
    "voice_mail_plan": "yes",
    "number_vmail_messages": 25,
    "total_day_minutes": 265.1,
    "total_day_calls": 110,
    "total_day_charge": 45.07,
    "total_eve_minutes": 197.4,
    "total_eve_calls": 99,
    "total_eve_charge": 16.78,
    "total_night_minutes": 244.7,
    "total_night_calls": 91,
    "total_night_charge": 11.01,
    "total_intl_minutes": 10.0,
    "total_intl_calls": 3,
    "total_intl_charge": 2.70,
    "customer_service_calls": 1,
}


class TestPredictEndpoint:
    async def test_predict_success(
        self, client: AsyncClient, api_user_headers: dict, mock_pipeline
    ):
        resp = await client.post(
            "/api/v1/predict",
            json={"records": [VALID_RECORD]},
            headers=api_user_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 1
        pred = data["predictions"][0]
        assert "churn" in pred
        assert "churn_probability" in pred
        assert pred["confidence_band"] in ("low", "mid", "high")
        assert len(pred["input_hash"]) == 64

    async def test_predict_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/predict", json={"records": [VALID_RECORD]}
        )
        assert resp.status_code == 401

    async def test_predict_missing_field(
        self, client: AsyncClient, api_user_headers: dict
    ):
        bad_record = {k: v for k, v in VALID_RECORD.items() if k != "state"}
        resp = await client.post(
            "/api/v1/predict",
            json={"records": [bad_record]},
            headers=api_user_headers,
        )
        assert resp.status_code == 422

    async def test_predict_invalid_state(
        self, client: AsyncClient, api_user_headers: dict
    ):
        record = {**VALID_RECORD, "state": "TOOLONG"}
        resp = await client.post(
            "/api/v1/predict",
            json={"records": [record]},
            headers=api_user_headers,
        )
        assert resp.status_code == 422

    async def test_predict_negative_field(
        self, client: AsyncClient, api_user_headers: dict
    ):
        record = {**VALID_RECORD, "account_length": -1}
        resp = await client.post(
            "/api/v1/predict",
            json={"records": [record]},
            headers=api_user_headers,
        )
        assert resp.status_code == 422

    async def test_predict_empty_records(
        self, client: AsyncClient, api_user_headers: dict
    ):
        resp = await client.post(
            "/api/v1/predict",
            json={"records": []},
            headers=api_user_headers,
        )
        assert resp.status_code == 422

    async def test_predict_503_no_model(
        self, client: AsyncClient, api_user_headers: dict
    ):
        from app.ml.pipeline import PipelineManager, pipeline_manager
        from unittest.mock import patch

        with patch.object(pipeline_manager, "_pipeline", None):
            resp = await client.post(
                "/api/v1/predict",
                json={"records": [VALID_RECORD]},
                headers=api_user_headers,
            )
        assert resp.status_code == 503

    async def test_predict_returns_request_id(
        self, client: AsyncClient, api_user_headers: dict, mock_pipeline
    ):
        resp = await client.post(
            "/api/v1/predict",
            json={"records": [VALID_RECORD]},
            headers=api_user_headers,
        )
        assert "X-Request-ID" in resp.headers
