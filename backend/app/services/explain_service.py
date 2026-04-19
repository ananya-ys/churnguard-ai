"""
app/services/explain_service.py — SHAP explainability service layer.

Phase 6: Wraps ml/explainer.py for FastAPI endpoint consumption.
Not on the hot prediction path — only called from /explain endpoint.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PipelineNotLoadedException
from app.ml.pipeline import pipeline_manager
from app.ml.explainer import get_explainer, ExplainerService
from app.schemas.predict import CustomerRecord

logger = structlog.get_logger(__name__)


class ExplainService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _get_explainer(self) -> ExplainerService:
        if not pipeline_manager.is_loaded():
            raise PipelineNotLoadedException()

        pipeline = pipeline_manager._pipeline
        version_tag = pipeline_manager.get_version()
        return get_explainer(pipeline, version_tag)

    async def explain_records(
        self,
        records: list[CustomerRecord],
        top_n: int = 10,
    ) -> dict[str, Any]:
        """
        SHAP explanation for a list of customer records.
        Returns per-record top feature contributions + global summary.
        """
        record_dicts = [r.model_dump() for r in records]
        explainer = self._get_explainer()

        per_record = explainer.explain_records(record_dicts, top_n=top_n)
        global_importance = explainer.global_feature_importance(record_dicts, top_n=top_n)

        return {
            "model_version": pipeline_manager.get_version(),
            "record_count": len(records),
            "per_record_explanations": per_record,
            "global_feature_importance": global_importance,
        }
