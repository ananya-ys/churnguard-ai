"""
app/ml/explainer.py — SHAP-based model explainability engine.

Phase 6 differentiator: feature importance + per-prediction SHAP explanation.

Uses TreeExplainer for RandomForest/GBM (fast, exact) and
LinearExplainer fallback for LogisticRegression.

SHAP values tell you: "This feature pushed the prediction up/down by X."
Recruiter-visible value: most candidates cannot explain WHY a model predicts.
"""

from typing import Any

import numpy as np
import pandas as pd
import structlog

from app.ml.pipeline import FEATURE_COLUMNS

logger = structlog.get_logger(__name__)


class ExplainerService:
    """
    Wraps a trained sklearn Pipeline and produces SHAP explanations.
    Instantiated lazily — only when /explain endpoint is called.
    Not part of hot prediction path.
    """

    def __init__(self, pipeline: Any) -> None:
        self._pipeline = pipeline
        self._explainer: Any = None
        self._feature_names: list[str] = []
        self._preprocessor_fitted = False

    def _build_explainer(self) -> None:
        """Lazy-build the SHAP explainer from the loaded pipeline."""
        import shap

        preprocessor = self._pipeline.named_steps.get("preprocessor")
        classifier = self._pipeline.named_steps.get("classifier")

        if preprocessor is None or classifier is None:
            raise ValueError("Pipeline must have 'preprocessor' and 'classifier' steps")

        # Get transformed feature names
        transformed_names: list[str] = []
        for _name, transformer, cols in preprocessor.transformers_:
            if hasattr(transformer, "get_feature_names_out"):
                transformed_names.extend(
                    transformer.get_feature_names_out(cols).tolist()
                )
            else:
                transformed_names.extend(list(cols))

        self._feature_names = transformed_names

        # Choose explainer based on classifier type
        classifier_type = type(classifier).__name__

        if classifier_type in ("RandomForestClassifier", "GradientBoostingClassifier",
                               "ExtraTreesClassifier", "XGBClassifier", "LGBMClassifier"):
            self._explainer = shap.TreeExplainer(classifier)
            logger.info("shap_tree_explainer_built", classifier=classifier_type)
        elif classifier_type == "LogisticRegression":
            # LinearExplainer needs a background dataset — use a zero matrix
            n_features = len(transformed_names)
            background = np.zeros((1, n_features))
            self._explainer = shap.LinearExplainer(classifier, background)
            logger.info("shap_linear_explainer_built", classifier=classifier_type)
        else:
            # Generic KernelExplainer — slow but universal
            n_features = len(transformed_names)
            background = np.zeros((1, n_features))
            predict_fn = lambda x: classifier.predict_proba(x)[:, 1]  # noqa: E731
            self._explainer = shap.KernelExplainer(predict_fn, background)
            logger.info("shap_kernel_explainer_built", classifier=classifier_type)

    def _ensure_explainer(self) -> None:
        if self._explainer is None:
            self._build_explainer()

    def explain_records(
        self,
        records: list[dict[str, Any]],
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Explain a list of customer records.

        Returns:
            List of dicts, one per record:
            {
                "churn_probability": float,
                "top_features": [{"feature": str, "shap_value": float, "direction": str}],
                "expected_value": float,
            }
        """
        self._ensure_explainer()

        df = pd.DataFrame(records, columns=FEATURE_COLUMNS)
        preprocessor = self._pipeline.named_steps["preprocessor"]
        classifier = self._pipeline.named_steps["classifier"]

        # Transform features
        X_transformed = preprocessor.transform(df)

        # Get SHAP values
        raw_shap = self._explainer.shap_values(X_transformed)

        # For binary classifiers, shap_values returns [class0_vals, class1_vals]
        # We want class 1 (churn probability)
        if isinstance(raw_shap, list) and len(raw_shap) == 2:
            shap_values = raw_shap[1]
        else:
            shap_values = raw_shap

        # Get base (expected) value
        expected_value = float(
            self._explainer.expected_value[1]
            if hasattr(self._explainer.expected_value, "__len__")
            else self._explainer.expected_value
        )

        # Predicted probabilities
        probabilities = classifier.predict_proba(X_transformed)[:, 1]

        results: list[dict[str, Any]] = []
        for i, (record_shap, prob) in enumerate(zip(shap_values, probabilities)):
            # Flatten to 1D if SHAP returns nested lists (RandomForest multi-output)
            flat_shap = []
            for val in record_shap.tolist():
                if isinstance(val, list):
                    flat_shap.append(float(val[1]) if len(val) > 1 else float(val[0]))
                else:
                    flat_shap.append(float(val))

            feature_shap_pairs = sorted(
                zip(self._feature_names, flat_shap),
                key=lambda x: abs(x[1]),
                reverse=True,
            )
            top_features = [
                {
                    "feature": fname,
                    "shap_value": round(float(sv), 6),
                    "direction": "increases_churn" if sv > 0 else "decreases_churn",
                    "magnitude": round(abs(float(sv)), 6),
                }
                for fname, sv in feature_shap_pairs[:top_n]
            ]

            results.append({
                "record_index": i,
                "churn_probability": round(float(prob), 6),
                "expected_value": round(expected_value, 6),
                "top_features": top_features,
                "shap_sum": round(float(sum(sv for _, sv in feature_shap_pairs)), 6),
            })

        logger.info("shap_explanation_complete", n_records=len(records))
        return results

    def global_feature_importance(
        self,
        records: list[dict[str, Any]],
        top_n: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Compute mean absolute SHAP values across a batch of records.
        Use this for the "global importance" UI panel.
        """
        self._ensure_explainer()

        df = pd.DataFrame(records, columns=FEATURE_COLUMNS)
        preprocessor = self._pipeline.named_steps["preprocessor"]

        X_transformed = preprocessor.transform(df)
        raw_shap = self._explainer.shap_values(X_transformed)

        if isinstance(raw_shap, list) and len(raw_shap) == 2:
            shap_values = raw_shap[1]
        else:
            shap_values = raw_shap

        # Mean absolute SHAP per feature
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        ranked = sorted(
            zip(self._feature_names, mean_abs_shap.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            {
                "feature": fname,
                "mean_abs_shap": round(float(val), 6),
                "rank": rank + 1,
            }
            for rank, (fname, val) in enumerate(ranked[:top_n])
        ]


# ── Module-level cache ─────────────────────────────────────────────────────────
# One explainer per loaded pipeline. Reset on model swap.

_explainer_cache: dict[str, ExplainerService] = {}


def get_explainer(pipeline: Any, version_tag: str) -> ExplainerService:
    """Return cached ExplainerService or build a new one."""
    if version_tag not in _explainer_cache:
        _explainer_cache.clear()  # Only keep one version in memory
        _explainer_cache[version_tag] = ExplainerService(pipeline)
    return _explainer_cache[version_tag]


def invalidate_explainer_cache() -> None:
    """Call this when a new model is promoted."""
    _explainer_cache.clear()
    logger.info("explainer_cache_invalidated")
