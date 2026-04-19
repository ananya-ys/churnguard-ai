"""
app/ml/experiment_tracker.py — Lightweight in-DB experiment tracking.

Phase 2 deliverable: track every training run with full metadata.
No MLflow dependency — uses existing PostgreSQL via sync SQLAlchemy.

Captures:
  - Git commit hash (if available)
  - Dataset hash (SHA-256 of feature stats)
  - All hyperparameters
  - All evaluation metrics
  - Training duration
  - Feature importance scores
  - Who triggered the run (system vs user)
"""

import hashlib
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class ExperimentRun:
    """Immutable record of one training run. Written to DB after training."""
    run_id: str
    version_tag: str
    estimator_key: str
    dataset_path: str
    dataset_hash: str
    dataset_row_count: int
    feature_names: list[str]
    hyperparameters: dict[str, Any]
    metrics: dict[str, float]
    feature_importance: dict[str, float]
    artifact_path: str
    git_commit: str
    git_branch: str
    triggered_by: str  # "system" | "user:{id}"
    duration_seconds: float
    auc_gate_passed: bool
    promoted: bool
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── Git utilities ──────────────────────────────────────────────────────────────

def _get_git_info() -> tuple[str, str]:
    """Return (commit_hash, branch_name) or ("unknown", "unknown") if not in a repo."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
        return commit, branch
    except Exception:
        return "unknown", "unknown"


def _extract_hyperparameters(pipeline: Any) -> dict[str, Any]:
    """Extract hyperparameters from sklearn Pipeline."""
    params: dict[str, Any] = {}
    try:
        classifier = pipeline.named_steps.get("classifier")
        if classifier is not None:
            for k, v in classifier.get_params().items():
                if isinstance(v, (int, float, str, bool, type(None))):
                    params[k] = v
    except Exception:
        pass
    return params


def _extract_feature_importance(pipeline: Any, feature_names: list[str]) -> dict[str, float]:
    """Extract feature importance from tree-based classifiers."""
    importance: dict[str, float] = {}
    try:
        classifier = pipeline.named_steps.get("classifier")
        preprocessor = pipeline.named_steps.get("preprocessor")

        if classifier is None or not hasattr(classifier, "feature_importances_"):
            return {}

        # Get transformed feature names from preprocessor
        transformed_names: list[str] = []
        if preprocessor is not None:
            for name, transformer, cols in preprocessor.transformers_:
                if hasattr(transformer, "get_feature_names_out"):
                    transformed_names.extend(
                        transformer.get_feature_names_out(cols).tolist()
                    )
                else:
                    transformed_names.extend(cols)
        else:
            transformed_names = feature_names

        importances = classifier.feature_importances_
        for fname, imp in zip(transformed_names, importances):
            importance[fname] = round(float(imp), 6)

        # Sort descending
        importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)
        )
    except Exception:
        pass
    return importance


def _compute_dataset_hash(data_path: str) -> str:
    """SHA-256 hash of the CSV file bytes for reproducibility."""
    try:
        content = Path(data_path).read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except Exception:
        return "unknown"


def _generate_run_id() -> str:
    """Short unique ID for this training run."""
    import uuid
    return str(uuid.uuid4())[:8]


# ── Main tracking function ─────────────────────────────────────────────────────

def create_experiment_run(
    version_tag: str,
    estimator_key: str,
    data_path: str,
    row_count: int,
    feature_names: list[str],
    pipeline: Any,
    metrics: dict[str, float],
    artifact_path: str,
    auc_gate_passed: bool,
    promoted: bool,
    triggered_by: str = "system",
    notes: str = "",
    start_time: float | None = None,
) -> ExperimentRun:
    """
    Build a complete ExperimentRun record after training completes.
    Call this immediately after sklearn Pipeline.fit().
    """
    duration = time.time() - (start_time or time.time())
    git_commit, git_branch = _get_git_info()
    dataset_hash = _compute_dataset_hash(data_path)
    hyperparameters = _extract_hyperparameters(pipeline)
    feature_importance = _extract_feature_importance(pipeline, feature_names)

    return ExperimentRun(
        run_id=_generate_run_id(),
        version_tag=version_tag,
        estimator_key=estimator_key,
        dataset_path=data_path,
        dataset_hash=dataset_hash,
        dataset_row_count=row_count,
        feature_names=feature_names,
        hyperparameters=hyperparameters,
        metrics={k: round(float(v), 6) for k, v in metrics.items()},
        feature_importance=feature_importance,
        artifact_path=artifact_path,
        git_commit=git_commit,
        git_branch=git_branch,
        triggered_by=triggered_by,
        duration_seconds=round(duration, 2),
        auc_gate_passed=auc_gate_passed,
        promoted=promoted,
        notes=notes,
    )


def persist_experiment_run(run: ExperimentRun, sync_db_url: str) -> None:
    """
    Write ExperimentRun to PostgreSQL via sync SQLAlchemy.
    Called from train.py after registration completes.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(sync_db_url, pool_pre_ping=True)

    insert_sql = text("""
        INSERT INTO experiment_runs (
            run_id, version_tag, estimator_key, dataset_path, dataset_hash,
            dataset_row_count, feature_names, hyperparameters, metrics,
            feature_importance, artifact_path, git_commit, git_branch,
            triggered_by, duration_seconds, auc_gate_passed, promoted, notes, created_at
        ) VALUES (
            :run_id, :version_tag, :estimator_key, :dataset_path, :dataset_hash,
            :dataset_row_count, :feature_names, :hyperparameters,
            :metrics, :feature_importance, :artifact_path, :git_commit,
            :git_branch, :triggered_by, :duration_seconds, :auc_gate_passed, :promoted,
            :notes, :created_at
        )
        ON CONFLICT (run_id) DO NOTHING
    """)

    with engine.begin() as conn:
        conn.execute(insert_sql, {
            "run_id": run.run_id,
            "version_tag": run.version_tag,
            "estimator_key": run.estimator_key,
            "dataset_path": run.dataset_path,
            "dataset_hash": run.dataset_hash,
            "dataset_row_count": run.dataset_row_count,
            "feature_names": json.dumps(run.feature_names),
            "hyperparameters": json.dumps(run.hyperparameters),
            "metrics": json.dumps(run.metrics),
            "feature_importance": json.dumps(run.feature_importance),
            "artifact_path": run.artifact_path,
            "git_commit": run.git_commit,
            "git_branch": run.git_branch,
            "triggered_by": run.triggered_by,
            "duration_seconds": run.duration_seconds,
            "auc_gate_passed": run.auc_gate_passed,
            "promoted": run.promoted,
            "notes": run.notes,
            "created_at": run.created_at,
        })

    engine.dispose()