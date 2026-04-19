"""app/repositories/ab_test_repository.py — A/B test repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ab_test import ABTest


class ABTestRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        name: str,
        control_version_tag: str,
        treatment_version_tag: str,
        treatment_traffic_fraction: float = 0.5,
        description: str | None = None,
    ) -> ABTest:
        test = ABTest(
            name=name,
            control_version_tag=control_version_tag,
            treatment_version_tag=treatment_version_tag,
            treatment_traffic_fraction=treatment_traffic_fraction,
            description=description,
        )
        self._db.add(test)
        await self._db.flush()
        await self._db.refresh(test)
        return test

    async def get_active(self) -> ABTest | None:
        result = await self._db.execute(
            select(ABTest)
            .where(ABTest.is_active.is_(True))
            .order_by(ABTest.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ABTest | None:
        result = await self._db.execute(
            select(ABTest).where(ABTest.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, test_id: uuid.UUID) -> ABTest | None:
        result = await self._db.execute(
            select(ABTest).where(ABTest.id == test_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ABTest]:
        result = await self._db.execute(
            select(ABTest).order_by(ABTest.created_at.desc())
        )
        return list(result.scalars().all())

    async def record_prediction(
        self,
        test_id: uuid.UUID,
        variant: str,
        churn_probability: float,
    ) -> None:
        """Increment request counter and churn sum for a variant. Uses SELECT FOR UPDATE."""
        from sqlalchemy import update
        if variant == "control":
            await self._db.execute(
                update(ABTest)
                .where(ABTest.id == test_id)
                .values(
                    control_requests=ABTest.control_requests + 1,
                    control_churn_sum=ABTest.control_churn_sum + churn_probability,
                )
            )
        else:
            await self._db.execute(
                update(ABTest)
                .where(ABTest.id == test_id)
                .values(
                    treatment_requests=ABTest.treatment_requests + 1,
                    treatment_churn_sum=ABTest.treatment_churn_sum + churn_probability,
                )
            )

    async def stop(self, test_id: uuid.UUID) -> ABTest | None:
        from datetime import UTC, datetime
        test = await self.get_by_id(test_id)
        if test:
            test.is_active = False
            test.ended_at = datetime.now(UTC)
        return test
