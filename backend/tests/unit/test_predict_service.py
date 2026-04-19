"""Unit tests for PredictService — confidence bands, hash, churn threshold."""

import pytest

from app.services.predict_service import (
    CHURN_THRESHOLD,
    _compute_hash,
    _confidence_band,
)


class TestConfidenceBand:
    def test_low_band(self):
        assert _confidence_band(0.0) == "low"
        assert _confidence_band(0.29) == "low"

    def test_mid_band(self):
        assert _confidence_band(0.3) == "mid"
        assert _confidence_band(0.5) == "mid"
        assert _confidence_band(0.69) == "mid"

    def test_high_band(self):
        assert _confidence_band(0.7) == "high"
        assert _confidence_band(0.99) == "high"
        assert _confidence_band(1.0) == "high"


class TestChurnThreshold:
    def test_threshold_value(self):
        assert CHURN_THRESHOLD == 0.5

    def test_at_threshold_is_churn(self):
        assert 0.5 >= CHURN_THRESHOLD

    def test_below_threshold_not_churn(self):
        assert 0.499 < CHURN_THRESHOLD


class TestInputHash:
    def test_same_input_same_hash(self):
        record = {"state": "CA", "account_length": 100, "area_code": 415}
        assert _compute_hash(record) == _compute_hash(record)

    def test_different_input_different_hash(self):
        r1 = {"state": "CA", "account_length": 100}
        r2 = {"state": "NY", "account_length": 100}
        assert _compute_hash(r1) != _compute_hash(r2)

    def test_hash_is_hex_string(self):
        record = {"state": "TX"}
        h = _compute_hash(record)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_key_order_invariant(self):
        r1 = {"a": 1, "b": 2}
        r2 = {"b": 2, "a": 1}
        assert _compute_hash(r1) == _compute_hash(r2)
