"""app/repositories/drift_repository.py — Drift report repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drift_report import DriftReport


class DriftRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        model_version_tag: str,
        overall_drift_score: float,
        drift_detected: bool,
        drifted_feature_count: int,
        severity: str,
        sample_size_train: int,
        sample_size_live: int,
        feature_results: list,
    ) -> DriftReport:
        report = DriftReport(
            model_version_tag=model_version_tag,
            overall_drift_score=overall_drift_score,
            drift_detected=drift_detected,
            drifted_feature_count=drifted_feature_count,
            severity=severity,
            sample_size_train=sample_size_train,
            sample_size_live=sample_size_live,
            feature_results=feature_results,
        )
        self._db.add(report)
        await self._db.flush()
        await self._db.refresh(report)
        return report

    async def get_latest(self, model_version_tag: str | None = None) -> DriftReport | None:
        q = select(DriftReport).order_by(DriftReport.created_at.desc())
        if model_version_tag:
            q = q.where(DriftReport.model_version_tag == model_version_tag)
        result = await self._db.execute(q.limit(1))
        return result.scalar_one_or_none()

    async def list_all(self, page: int = 1, page_size: int = 20) -> list[DriftReport]:
        result = await self._db.execute(
            select(DriftReport)
            .order_by(DriftReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def list_by_model(self, version_tag: str) -> list[DriftReport]:
        result = await self._db.execute(
            select(DriftReport)
            .where(DriftReport.model_version_tag == version_tag)
            .order_by(DriftReport.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())
