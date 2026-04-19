"""Unit tests for PipelineManager singleton."""

import os
import threading
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.exceptions import PipelineNotLoadedException
from app.ml.pipeline import PipelineManager, pipeline_manager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    PipelineManager.reset()
    yield
    PipelineManager.reset()


def make_mock_pipeline(proba: list[float] | None = None) -> MagicMock:
    mock = MagicMock()
    n = len(proba) if proba else 3
    proba_val = proba or [0.8, 0.2, 0.6]
    mock.predict_proba.return_value = np.array(
        [[1 - p, p] for p in proba_val]
    )
    return mock


class TestPipelineManagerSingleton:
    def test_singleton_same_instance(self):
        a = PipelineManager()
        b = PipelineManager()
        assert a is b

    def test_not_loaded_initially(self):
        pm = PipelineManager()
        assert not pm.is_loaded()
        assert pm.get_version() == "unloaded"

    def test_raises_when_not_loaded(self):
        pm = PipelineManager()
        with pytest.raises(PipelineNotLoadedException):
            pm.predict([{"state": "CA", "account_length": 100}])


class TestPipelineLoad:
    def test_load_nonexistent_file_does_not_raise(self, tmp_path):
        pm = PipelineManager()
        pm.load(str(tmp_path / "missing.pkl"))
        assert not pm.is_loaded()

    def test_load_valid_pipeline(self, tmp_path):
        mock_pipeline = make_mock_pipeline()
        artifact = tmp_path / "model_v1.pkl"
        joblib.dump(mock_pipeline, artifact)

        pm = PipelineManager()
        pm.load(str(artifact))
        assert pm.is_loaded()
        assert pm.get_version() == "model_v1"

    def test_predict_after_load(self, tmp_path):
        mock_pipeline = make_mock_pipeline([0.9, 0.1])
        artifact = tmp_path / "v1.pkl"
        joblib.dump(mock_pipeline, artifact)

        pm = PipelineManager()
        pm.load(str(artifact))
        results = pm.predict([{} for _ in range(2)])
        assert len(results) == 2
        assert abs(results[0] - 0.9) < 0.01
        assert abs(results[1] - 0.1) < 0.01


class TestPipelineSwap:
    def test_atomic_swap(self, tmp_path):
        mock1 = make_mock_pipeline([0.5])
        mock2 = make_mock_pipeline([0.9])

        artifact1 = tmp_path / "v1.pkl"
        artifact2 = tmp_path / "v2.pkl"
        joblib.dump(mock1, artifact1)
        joblib.dump(mock2, artifact2)

        pm = PipelineManager()
        pm.load(str(artifact1))
        assert pm.get_version() == "v1"

        pm.swap(str(artifact2), "v2")
        assert pm.get_version() == "v2"
        results = pm.predict([{}])
        assert abs(results[0] - 0.9) < 0.01

    def test_concurrent_swap_no_corruption(self, tmp_path):
        """Verify threading.Lock prevents state corruption during concurrent swap."""
        mock1 = make_mock_pipeline([0.2] * 10)
        mock2 = make_mock_pipeline([0.8] * 10)

        artifact1 = tmp_path / "v1.pkl"
        artifact2 = tmp_path / "v2.pkl"
        joblib.dump(mock1, artifact1)
        joblib.dump(mock2, artifact2)

        pm = PipelineManager()
        pm.load(str(artifact1))

        errors: list[Exception] = []

        def swap_v2():
            try:
                pm.swap(str(artifact2), "v2")
            except Exception as e:
                errors.append(e)

        def predict_loop():
            try:
                for _ in range(50):
                    pm.predict([{}] * 10)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=predict_loop) for _ in range(5)]
        threads.append(threading.Thread(target=swap_v2))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
