"""
app/tasks/drift_check.py — Scheduled drift detection Celery task.

Phase 4: Runs daily (03:00 UTC). Compares training distribution vs
24h of live prediction inputs. Logs alerts if drift detected.

If severe drift is found, logs a critical alert (Grafana can alert on this log).
"""

import structlog

from app.core.config import settings
from app.tasks.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.drift_check.run_daily_drift_check",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_daily_drift_check(self, lookback_hours: int = 24) -> dict:
    """
    Daily drift check: compare training distribution vs recent live inputs.
    Writes a DriftReport to DB and updates Prometheus gauges.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db_sync = Session()

    try:
        # We need to run async code synchronously — use a fresh event loop
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

        async def _run() -> dict:
            async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            AsyncSessionLocal = async_sessionmaker(
                bind=async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with AsyncSessionLocal() as db:
                from app.services.drift_service import DriftService
                svc = DriftService(db)
                result = await svc.run_drift_check(lookback_hours=lookback_hours)

            await async_engine.dispose()
            return {
                "drift_detected": result.drift_detected,
                "severity": result.severity,
                "score": result.overall_drift_score,
                "n_drifted": result.drifted_feature_count,
                "report_id": str(result.report_id),
            }

        result = asyncio.run(_run())

        if result["drift_detected"]:
            if result["severity"] == "severe":
                logger.critical(
                    "DRIFT_ALERT_SEVERE",
                    severity=result["severity"],
                    score=result["score"],
                    n_drifted=result["n_drifted"],
                    action_required="RETRAIN MODEL IMMEDIATELY",
                )
            else:
                logger.warning(
                    "DRIFT_ALERT_MODERATE",
                    severity=result["severity"],
                    score=result["score"],
                    n_drifted=result["n_drifted"],
                )
        else:
            logger.info("drift_check_clean", score=result["score"])

        return result

    except Exception as exc:
        logger.exception("drift_check_task_failed")
        raise self.retry(exc=exc)

    finally:
        db_sync.close()
        engine.dispose()
