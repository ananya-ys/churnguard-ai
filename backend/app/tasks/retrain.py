"""
Scheduled retraining Celery task.
Runs weekly (Sunday 02:00 UTC via Celery Beat).
AUC gate enforced — degraded model cannot silently replace production.
"""

import structlog

from app.core.config import settings
from app.ml.train import train
from app.tasks.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.retrain.scheduled_retrain",
    bind=True,
    max_retries=1,
)
def scheduled_retrain(self, data_path: str | None = None) -> dict:
    from datetime import UTC, datetime

    from app.models.audit_log import AuditAction

    effective_data_path = data_path or "data/train.csv"
    version_tag = f"auto-{datetime.now(UTC).strftime('%Y%m%d-%H%M')}"

    logger.info("retrain_started", version_tag=version_tag, data_path=effective_data_path)

    db = None
    try:
        # Run training with AUC gate (exits with sys.exit(1) on failure)
        # We wrap in subprocess-style to capture the gate result gracefully
        metrics = train(
            data_path=effective_data_path,
            output_tag=version_tag,
            estimator_key="rf",
            min_auc=settings.min_auc_threshold,
        )

        # Register and promote new version via service layer
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db = Session()

        from app.models.model_version import ModelVersion

        mv = ModelVersion(
            version_tag=version_tag,
            artifact_path=metrics["artifact_path"],
            auc_roc=metrics["auc_roc"],
            f1_score=metrics["f1_score"],
            precision=metrics["precision"],
            recall=metrics["recall"],
            training_data_path=effective_data_path,
            row_count=metrics["row_count"],
            is_active=False,
        )
        db.add(mv)
        db.flush()

        # Atomic promotion
        current = db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).first()
        if current:
            current.is_active = False
        mv.is_active = True

        from app.models.audit_log import AuditLog
        audit = AuditLog(
            action=AuditAction.RETRAIN_SUCCESS,
            entity_type="model_version",
            entity_id=str(mv.id),
            model_version_tag=version_tag,
        )
        db.add(audit)
        db.commit()

        # Swap in-memory model
        from app.ml.pipeline import pipeline_manager
        pipeline_manager.swap(metrics["artifact_path"], version_tag)

        logger.info(
            "retrain_success",
            version_tag=version_tag,
            auc=metrics["auc_roc"],
        )
        return {"status": "success", "version_tag": version_tag, **metrics}

    except SystemExit:
        # AUC gate failed — log and alert, do NOT promote
        logger.error("retrain_auc_gate_failed", version_tag=version_tag)

        if db:
            try:
                from app.models.audit_log import AuditLog
                audit = AuditLog(
                    action=AuditAction.RETRAIN_FAIL,
                    entity_type="model_version",
                    model_version_tag=version_tag,
                )
                db.add(audit)
                db.commit()
            except Exception:
                pass

        return {"status": "auc_gate_failed", "version_tag": version_tag}

    except Exception as exc:
        logger.exception("retrain_failed", version_tag=version_tag)
        raise self.retry(exc=exc)

    finally:
        if db:
            db.close()
