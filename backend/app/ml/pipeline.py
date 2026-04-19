"""
PipelineManager — Singleton ML pipeline loader.

joblib.load() on a large model can take seconds — unacceptable per-request.
Singleton loads once at startup. threading.Lock() ensures atomic swap during
zero-downtime model promotion. No requests are dropped during swap.
"""

import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import structlog

from app.core.exceptions import PipelineNotLoadedException

logger = structlog.get_logger(__name__)

# Column order must match training schema exactly
FEATURE_COLUMNS = [
    "state",
    "account_length",
    "area_code",
    "international_plan",
    "voice_mail_plan",
    "number_vmail_messages",
    "total_day_minutes",
    "total_day_calls",
    "total_day_charge",
    "total_eve_minutes",
    "total_eve_calls",
    "total_eve_charge",
    "total_night_minutes",
    "total_night_calls",
    "total_night_charge",
    "total_intl_minutes",
    "total_intl_calls",
    "total_intl_charge",
    "customer_service_calls",
]


class PipelineManager:
    """Thread-safe singleton ML pipeline manager."""

    _instance: "PipelineManager | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "PipelineManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pipeline = None
                    cls._instance._version_tag = "unloaded"
                    cls._instance._swap_lock = threading.Lock()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for testing only."""
        cls._instance = None

    def load(self, path: str) -> None:
        """Load pipeline from disk. Called once at startup."""
        p = Path(path)
        if not p.exists():
            logger.warning("pipeline_file_not_found", path=path)
            return
        pipeline = joblib.load(p)
        with self._swap_lock:
            self._pipeline = pipeline
            self._version_tag = p.stem
        logger.info("pipeline_loaded", path=path, version=self._version_tag)

    def swap(self, new_path: str, new_version_tag: str) -> None:
        """Atomic zero-downtime model swap. Uses threading.Lock."""
        new_pipeline = joblib.load(new_path)
        with self._swap_lock:
            self._pipeline = new_pipeline
            self._version_tag = new_version_tag
        logger.info("pipeline_swapped", new_version=new_version_tag)

    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def get_version(self) -> str:
        return self._version_tag

    def predict(self, records: list[dict[str, Any]]) -> list[float]:
        """
        Run predict_proba on a list of record dicts.
        Returns list of churn probabilities (positive class).
        Raises PipelineNotLoadedException if no model is loaded.
        """
        if self._pipeline is None:
            raise PipelineNotLoadedException()

        df = pd.DataFrame(records, columns=FEATURE_COLUMNS)
        with self._swap_lock:
            pipeline = self._pipeline
        probas: np.ndarray = pipeline.predict_proba(df)
        # probas shape: (n, 2) — column 1 is P(churn=True)
        return probas[:, 1].tolist()


# Module-level singleton instance
pipeline_manager = PipelineManager()
