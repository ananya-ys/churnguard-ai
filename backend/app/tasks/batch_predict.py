"""
Batch prediction Celery task.

Idempotency pattern: check job status before processing.
If status != QUEUED, the task was already picked up — skip.
Chunked processing: constant memory regardless of CSV size.
"""

import uuid
from pathlib import Path

import pandas as pd
import structlog
from celery import Task

from app.core.config import settings
from app.ml.pipeline import pipeline_manager
from app.tasks.worker import celery_app

logger = structlog.get_logger(__name__)


def _get_sync_session():
    """Synchronous SQLAlchemy session for use inside Celery (no async event loop)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(
    name="app.tasks.batch_predict.process_batch_job",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_batch_job(self: Task, job_id_str: str) -> dict:
    from datetime import UTC, datetime

    from app.models.prediction_job import JobStatus, PredictionJob

    job_id = uuid.UUID(job_id_str)
    db = _get_sync_session()

    try:
        # ── Idempotency check (pattern 8) ─────────────────────────────────────
        job = db.query(PredictionJob).filter(PredictionJob.id == job_id).first()
        if job is None:
            logger.error("batch_job_not_found", job_id=job_id_str)
            return {"status": "not_found"}

        if job.status != JobStatus.QUEUED:
            logger.warning(
                "batch_job_already_processed",
                job_id=job_id_str,
                status=job.status,
            )
            return {"status": "already_processed", "job_status": job.status}

        # ── Set PROCESSING ────────────────────────────────────────────────────
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        db.commit()

        logger.info("batch_job_started", job_id=job_id_str)

        # ── Chunked CSV processing ────────────────────────────────────────────
        result_dir = Path(job.file_path).parent / "results"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = str(result_dir / f"{job_id}.results.csv")

        total_processed = 0
        first_chunk = True

        for chunk in pd.read_csv(job.file_path, chunksize=settings.chunk_size):
            record_dicts = chunk.to_dict(orient="records")
            probabilities = pipeline_manager.predict(record_dicts)

            result_rows = []
            for record, prob in zip(record_dicts, probabilities):
                result_rows.append({
                    **record,
                    "churn_probability": round(prob, 6),
                    "churn": prob >= 0.5,
                    "confidence_band": (
                        "low" if prob < 0.3 else "mid" if prob < 0.7 else "high"
                    ),
                })

            result_df = pd.DataFrame(result_rows)
            result_df.to_csv(
                result_path,
                mode="w" if first_chunk else "a",
                header=first_chunk,
                index=False,
            )
            first_chunk = False
            total_processed += len(chunk)

            # Persist progress after each chunk
            job.processed_count = total_processed
            db.commit()

            logger.debug(
                "batch_chunk_processed",
                job_id=job_id_str,
                chunk_size=len(chunk),
                total_processed=total_processed,
            )

        # ── Complete ──────────────────────────────────────────────────────────
        job.status = JobStatus.COMPLETED
        job.result_path = result_path
        job.completed_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "batch_job_completed",
            job_id=job_id_str,
            total_processed=total_processed,
            result_path=result_path,
        )
        return {"status": "completed", "processed": total_processed}

    except Exception as exc:
        from datetime import UTC, datetime

        from app.models.prediction_job import JobStatus, PredictionJob

        logger.exception("batch_job_failed", job_id=job_id_str)
        try:
            job = db.query(PredictionJob).filter(PredictionJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(UTC)
                db.commit()
        except Exception:
            logger.exception("batch_job_status_update_failed", job_id=job_id_str)

        raise self.retry(exc=exc)

    finally:
        db.close()
