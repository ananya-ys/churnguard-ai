#!/usr/bin/env python3
"""
ChurnGuard AI — Production Training Pipeline  (Phase 1 + 2)

Phase 1 — Automation:
  - Auto version tagging: v1, v2, v3... (no manual naming)
  - Auto metrics extraction
  - Auto registration via internal API
  - Auto promotion if new model beats current best AUC
  - One command: docker compose exec trainer python train.py

Phase 2 — ML Lifecycle:
  - Dataset hash for reproducibility
  - Git commit + branch tracking
  - Feature importance extraction
  - Full experiment metadata persisted to DB
  - Model lineage: who trained, when, from which data

Usage:
    # Inside Docker:
    docker compose exec app python app/ml/train.py \\
        --data-path data/train.csv \\
        --estimator rf \\
        --min-auc 0.75

    # Via pipeline.sh (one command):
    ./pipeline.sh
"""

import argparse
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
import requests

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ── Feature schema ─────────────────────────────────────────────────────────────

TARGET_COLUMN = "churn"

CATEGORICAL_FEATURES = ["state", "international_plan", "voice_mail_plan"]

NUMERIC_FEATURES = [
    "account_length", "area_code", "number_vmail_messages",
    "total_day_minutes", "total_day_calls", "total_day_charge",
    "total_eve_minutes", "total_eve_calls", "total_eve_charge",
    "total_night_minutes", "total_night_calls", "total_night_charge",
    "total_intl_minutes", "total_intl_calls", "total_intl_charge",
    "customer_service_calls",
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

ESTIMATORS = {
    "lr": LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
    "rf": RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced"),
    "gbm": GradientBoostingClassifier(n_estimators=200, random_state=42),
}

API_BASE = "http://app:8000/api/v1"


# ── Pipeline factory ────────────────────────────────────────────────────────────

def build_pipeline(estimator_key: str) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", ESTIMATORS[estimator_key]),
    ])


# ── Auto-versioning ─────────────────────────────────────────────────────────────

def get_next_version_tag(api_base: str) -> str:
    """
    Query existing model versions and return the next sequential tag: v1, v2, v3...
    Falls back to 'v1' if API is unreachable or no models exist.
    """
    try:
        resp = requests.get(f"{api_base}/models", timeout=10)
        if resp.status_code != 200:
            return "v1"
        models = resp.json()
        if not models:
            return "v1"

        # Extract numeric suffix from existing version tags (v1 → 1, v2 → 2, ...)
        max_num = 0
        for m in models:
            tag = m.get("version_tag", "")
            if tag.startswith("v") and tag[1:].isdigit():
                max_num = max(max_num, int(tag[1:]))
        return f"v{max_num + 1}"
    except Exception as e:
        print(f"[WARN] Could not determine next version tag: {e}")
        return "v1"


def get_best_auc(api_base: str) -> float:
    """Fetch the highest AUC-ROC from all registered models."""
    try:
        resp = requests.get(f"{api_base}/models", timeout=10)
        if resp.status_code != 200 or not resp.json():
            return 0.0
        models = resp.json()
        return max((m.get("auc_roc", 0.0) for m in models), default=0.0)
    except Exception:
        return 0.0


# ── HTTP helpers ────────────────────────────────────────────────────────────────

def retry_request(method, url: str, max_retries: int = 3, **kwargs) -> requests.Response | None:
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [HTTP] Attempt {attempt} → {url}")
            resp = method(url, timeout=15, **kwargs)
            print(f"  [HTTP] {resp.status_code}")
            return resp
        except Exception as e:
            print(f"  [RETRY {attempt}] {e}")
            time.sleep(2 ** attempt)  # exponential back-off
    print("  [FATAL] All retries exhausted")
    return None


# ── Dataset utilities ───────────────────────────────────────────────────────────

def compute_dataset_hash(data_path: str) -> str:
    """SHA-256 fingerprint of the training CSV for reproducibility."""
    import hashlib
    content = Path(data_path).read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def extract_training_feature_stats(df: pd.DataFrame) -> dict:
    """Extract summary statistics used for drift baseline."""
    stats: dict = {}
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            s = df[col].dropna()
            stats[col] = {
                "mean": float(s.mean()),
                "std": float(s.std()),
                "min": float(s.min()),
                "max": float(s.max()),
                "p25": float(s.quantile(0.25)),
                "p50": float(s.quantile(0.50)),
                "p75": float(s.quantile(0.75)),
                "count": int(len(s)),
                "values_sample": s.sample(min(500, len(s)), random_state=42).tolist(),
            }
    return stats


# ── Core training function ──────────────────────────────────────────────────────

def train(
    data_path: str,
    output_tag: str | None = None,  # None = auto-version
    estimator_key: str = "rf",
    min_auc: float = 0.75,
    output_dir: str = "app/ml/artifacts",
    triggered_by: str = "system",
    api_base: str = API_BASE,
) -> dict:
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"ChurnGuard AI — Training Pipeline")
    print(f"{'='*60}")
    print(f"Data:      {data_path}")
    print(f"Estimator: {estimator_key}")
    print(f"Min AUC:   {min_auc}")

    # ── Phase 1: Auto version tagging ─────────────────────────────────────────
    if output_tag is None:
        output_tag = get_next_version_tag(api_base)
    print(f"Version:   {output_tag}  (auto-tagged)")

    # ── Load and validate data ────────────────────────────────────────────────
    print(f"\n[1/6] Loading data...")
    df = pd.read_csv(data_path)
    print(f"  Rows: {len(df):,} | Columns: {list(df.columns)}")

    if TARGET_COLUMN not in df.columns:
        print("[ERROR] Target column 'churn' missing from dataset")
        sys.exit(1)

    if df[TARGET_COLUMN].dtype == object:
        df[TARGET_COLUMN] = df[TARGET_COLUMN].map({"yes": 1, "no": 0})

    # ── Phase 2: Dataset fingerprinting ───────────────────────────────────────
    print(f"\n[2/6] Fingerprinting dataset...")
    dataset_hash = compute_dataset_hash(data_path)
    feature_stats = extract_training_feature_stats(df)
    print(f"  Dataset hash: {dataset_hash}")
    print(f"  Churn rate:   {df[TARGET_COLUMN].mean():.1%}")

    # ── Train/test split ──────────────────────────────────────────────────────
    X = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"  Train: {len(X_train):,} | Test: {len(X_test):,}")

    # ── Train model ───────────────────────────────────────────────────────────
    print(f"\n[3/6] Training {estimator_key}...")
    pipeline = build_pipeline(estimator_key)
    pipeline.fit(X_train, y_train)
    print(f"  Training complete in {time.time() - start_time:.1f}s")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    print(f"\n[4/6] Evaluating...")
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "auc_roc": float(roc_auc_score(y_test, y_proba)),
        "f1_score": float(f1_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "row_count": int(len(df)),
    }

    print(f"\n  {'Metric':<20} {'Value':>10}")
    print(f"  {'-'*30}")
    for k, v in metrics.items():
        if k != "row_count":
            print(f"  {k:<20} {v:>10.4f}")
    print(f"  {'row_count':<20} {metrics['row_count']:>10,}")

    # ── AUC gate ──────────────────────────────────────────────────────────────
    auc_gate_passed = metrics["auc_roc"] >= min_auc
    if not auc_gate_passed:
        print(f"\n[GATE FAILED] AUC {metrics['auc_roc']:.4f} < threshold {min_auc}")
        sys.exit(1)
    print(f"\n[GATE PASSED] AUC {metrics['auc_roc']:.4f} >= {min_auc}")

    # ── Save artifact ─────────────────────────────────────────────────────────
    print(f"\n[5/6] Saving artifact...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    artifact_path = str(Path(output_dir) / f"{output_tag}.pkl")
    joblib.dump(pipeline, artifact_path)
    print(f"  Saved: {artifact_path}")

    # ── Register model ────────────────────────────────────────────────────────
    print(f"\n[6/6] Registering model (Phase 1: auto-registration)...")

    register_payload = {
        "version_tag": output_tag,
        "artifact_path": artifact_path,
        "auc_roc": metrics["auc_roc"],
        "f1_score": metrics["f1_score"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "training_data_path": data_path,
        "row_count": metrics["row_count"],
        "dataset_hash": dataset_hash,
        "estimator_key": estimator_key,
        "training_feature_stats": feature_stats,
    }

    reg_resp = retry_request(requests.post, f"{api_base}/models", json=register_payload)

    if not reg_resp or reg_resp.status_code != 201:
        print(f"[ERROR] Registration failed: {reg_resp.text if reg_resp else 'no response'}")
        sys.exit(1)

    model_id = reg_resp.json().get("id")
    print(f"  Registered: ID={model_id} | tag={output_tag}")

    # ── Auto-promotion (Phase 1: promote if better) ────────────────────────────
    print(f"\n[AUTO-PROMOTE] Comparing against current best...")
    best_auc = get_best_auc(api_base)
    print(f"  New AUC:  {metrics['auc_roc']:.4f}")
    print(f"  Best AUC: {best_auc:.4f}")

    promoted = False
    if metrics["auc_roc"] >= best_auc and model_id:
        print(f"  → Promoting {output_tag}...")
        promote_resp = retry_request(requests.post, f"{api_base}/models/{model_id}/promote")
        if promote_resp and promote_resp.status_code == 200:
            promoted = True
            print(f"  [PROMOTED] {output_tag} is now active!")
        else:
            print(f"  [PROMOTE FAILED] {promote_resp.text if promote_resp else ''}")
    else:
        print(f"  [SKIPPED] Not better than existing model — keeping current active")

    # ── Phase 2: Persist experiment run ───────────────────────────────────────
    print(f"\n[EXPERIMENT] Recording training run metadata...")
    try:
        from app.ml.experiment_tracker import create_experiment_run, persist_experiment_run
        from app.core.config import settings

        run = create_experiment_run(
            version_tag=output_tag,
            estimator_key=estimator_key,
            data_path=data_path,
            row_count=metrics["row_count"],
            feature_names=ALL_FEATURES,
            pipeline=pipeline,
            metrics=metrics,
            artifact_path=artifact_path,
            auc_gate_passed=auc_gate_passed,
            promoted=promoted,
            triggered_by=triggered_by,
            start_time=start_time,
        )

        persist_experiment_run(run, settings.sync_database_url)
        print(f"  Run ID: {run.run_id} | Git: {run.git_commit}@{run.git_branch}")
    except Exception as e:
        print(f"  [WARN] Experiment tracking failed (non-fatal): {e}")

    duration = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"DONE in {duration:.1f}s")
    print(f"Version: {output_tag} | AUC: {metrics['auc_roc']:.4f} | Promoted: {promoted}")
    print(f"{'='*60}\n")

    return {
        "version_tag": output_tag,
        "model_id": model_id,
        "artifact_path": artifact_path,
        "promoted": promoted,
        "dataset_hash": dataset_hash,
        **metrics,
    }


# ── CLI entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChurnGuard AI — Training Pipeline (Phase 1+2)"
    )
    parser.add_argument("--data-path", default="data/train.csv", help="CSV training data")
    parser.add_argument("--output", default=None, help="Version tag (default: auto v1, v2, ...)")
    parser.add_argument("--estimator", choices=["lr", "rf", "gbm"], default="rf")
    parser.add_argument("--min-auc", type=float, default=0.75)
    parser.add_argument("--triggered-by", default="system")
    parser.add_argument("--api-base", default=API_BASE)

    args = parser.parse_args()

    result = train(
        data_path=args.data_path,
        output_tag=args.output,
        estimator_key=args.estimator,
        min_auc=args.min_auc,
        triggered_by=args.triggered_by,
        api_base=args.api_base,
    )

    print("FINAL RESULT:", result)


if __name__ == "__main__":
    main()
