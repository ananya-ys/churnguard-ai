"""app/services/experiment_service.py — Experiment tracking service."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.experiment_repository import ExperimentRepository
from app.schemas.experiment import (
    ExperimentCompareResponse,
    ExperimentRunResponse,
    MetricComparison,
)
from app.core.exceptions import NotFoundException

logger = structlog.get_logger(__name__)

COMPARE_METRICS = ["auc_roc", "f1_score", "precision", "recall", "accuracy"]


class ExperimentService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ExperimentRepository(db)

    async def list_runs(self, page: int = 1, page_size: int = 20) -> list[ExperimentRunResponse]:
        runs = await self._repo.list_all(page=page, page_size=page_size)
        return [ExperimentRunResponse.model_validate(r) for r in runs]

    async def get_run(self, run_id: str) -> ExperimentRunResponse:
        run = await self._repo.get_by_run_id(run_id)
        if run is None:
            raise NotFoundException(f"Experiment run '{run_id}' not found")
        return ExperimentRunResponse.model_validate(run)

    async def compare_runs(
        self, run_id_a: str, run_id_b: str
    ) -> ExperimentCompareResponse:
        run_a = await self._repo.get_by_run_id(run_id_a)
        run_b = await self._repo.get_by_run_id(run_id_b)

        if run_a is None:
            raise NotFoundException(f"Run '{run_id_a}' not found")
        if run_b is None:
            raise NotFoundException(f"Run '{run_id_b}' not found")

        metrics_a: dict = run_a.metrics or {}
        metrics_b: dict = run_b.metrics or {}

        comparisons: list[MetricComparison] = []
        a_wins = 0
        b_wins = 0

        for metric in COMPARE_METRICS:
            val_a = metrics_a.get(metric, 0.0)
            val_b = metrics_b.get(metric, 0.0)
            delta = val_b - val_a

            if abs(delta) < 1e-6:
                winner = "tie"
            elif delta > 0:
                winner = "b"
                b_wins += 1
            else:
                winner = "a"
                a_wins += 1

            comparisons.append(MetricComparison(
                metric=metric,
                value_a=round(val_a, 6),
                value_b=round(val_b, 6),
                delta=round(delta, 6),
                winner=winner,
            ))

        if a_wins > b_wins:
            overall_winner = f"a ({run_id_a})"
        elif b_wins > a_wins:
            overall_winner = f"b ({run_id_b})"
        else:
            overall_winner = "tie"

        return ExperimentCompareResponse(
            run_a=ExperimentRunResponse.model_validate(run_a),
            run_b=ExperimentRunResponse.model_validate(run_b),
            metric_comparisons=comparisons,
            overall_winner=overall_winner,
        )
