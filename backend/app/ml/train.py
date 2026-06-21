"""
Training pipeline for document classification.

Run as a module from the backend directory:
    python -m app.ml.train

Steps:
  1. Generate the labelled dataset.
  2. Stratified train/test split.
  3. Build a TF-IDF + classifier pipeline for each of:
        Logistic Regression, Random Forest, XGBoost.
  4. Evaluate every model (accuracy, precision, recall, F1, confusion matrix).
  5. Select the best by macro-F1 and persist it with joblib.
  6. Write a metrics report (metrics.json) for inspection.

Why one scikit-learn Pipeline per model? Because the fitted TF-IDF vocabulary is
bundled *with* the classifier — saving the pipeline saves the entire transform,
so inference applies the identical feature extraction with zero drift.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from app.core.logging_config import get_logger
from app.ml.dataset import CATEGORIES, generate_dataset
from app.ml.preprocess import preprocess

logger = get_logger(__name__)

# Where artifacts are written. Anchored to this file's directory.
_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = _ARTIFACT_DIR / "classifier.joblib"
METRICS_PATH = _ARTIFACT_DIR / "metrics.json"


def _build_vectorizer() -> TfidfVectorizer:
    """
    TF-IDF vectoriser shared by every model.

    `preprocessor=preprocess` bakes our exact cleaning into the pipeline.
    ngram_range=(1, 2) captures unigrams + bigrams ("blood pressure"), and
    sublinear_tf dampens the effect of very frequent terms.
    """
    return TfidfVectorizer(
        preprocessor=preprocess,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
        lowercase=False,  # preprocess already lowercases
    )


def _candidate_models() -> dict[str, Any]:
    """The three classifiers to train and compare."""
    return {
        "LogisticRegression": LogisticRegression(max_iter=1000, C=4.0),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, random_state=42, n_jobs=-1
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.2,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=len(CATEGORIES),
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        ),
    }


def _inject_label_noise(
    y: np.ndarray, num_classes: int, rate: float, seed: int
) -> np.ndarray:
    """
    Flip a fraction `rate` of labels to a different random class.

    Simulates annotation errors. Returns a copy; the input is unchanged.
    """
    rng = np.random.default_rng(seed)
    y_noisy = np.array(y, copy=True)
    n_flip = int(len(y_noisy) * rate)
    flip_idx = rng.choice(len(y_noisy), size=n_flip, replace=False)
    for i in flip_idx:
        # Pick any class other than the current one.
        choices = [c for c in range(num_classes) if c != y_noisy[i]]
        y_noisy[i] = rng.choice(choices)
    return y_noisy


def _evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Compute the standard multi-class metrics (macro-averaged)."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def train() -> dict[str, Any]:
    """Run the full training + comparison + save-best workflow."""
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Generating dataset…")
    texts, labels = generate_dataset()

    # Encode string labels to integers (XGBoost requires numeric targets; the
    # encoder is saved so we can map predictions back to category names).
    encoder = LabelEncoder().fit(labels)
    y = encoder.transform(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.25, random_state=42, stratify=y
    )

    # Inject label noise into the TRAINING set only (test stays clean). Real
    # labelled corpora always contain annotation errors; this makes the task
    # non-trivial, so the three models genuinely differ and the confusion matrix
    # is meaningful. Test labels are untouched, so metrics still measure true
    # generalisation.
    y_train = _inject_label_noise(y_train, num_classes=len(CATEGORIES), rate=0.15, seed=42)
    logger.info("Train/test sizes: %d / %d (15%% train-label noise)", len(X_train), len(X_test))

    results: dict[str, Any] = {}
    fitted: dict[str, Pipeline] = {}

    for name, model in _candidate_models().items():
        logger.info("Training %s…", name)
        pipeline = Pipeline([("tfidf", _build_vectorizer()), ("clf", model)])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        results[name] = _evaluate(y_test, y_pred)
        fitted[name] = pipeline
        logger.info(
            "%s -> acc=%.3f f1=%.3f",
            name, results[name]["accuracy"], results[name]["f1_macro"],
        )

    # Select the best model by macro-F1 (balances precision & recall per class).
    best_name = max(results, key=lambda n: results[n]["f1_macro"])
    best_pipeline = fitted[best_name]
    logger.info("Best model: %s (f1=%.3f)", best_name, results[best_name]["f1_macro"])

    # Plain python strings (encoder.classes_ are numpy str types).
    categories = [str(c) for c in encoder.classes_]

    # Persist the winning pipeline + label encoder + metadata.
    joblib.dump(
        {
            "pipeline": best_pipeline,
            "label_encoder": encoder,
            "categories": categories,
            "model_name": best_name,
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        MODEL_PATH,
    )

    report = {
        "best_model": best_name,
        "categories": categories,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_size": len(texts),
        "models": results,
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Saved model -> %s", MODEL_PATH)
    logger.info("Saved metrics -> %s", METRICS_PATH)

    # Hot-swap the served model (lazy import avoids a circular dependency).
    from app.ml import classifier

    classifier.reload_model()
    return report


def _print_comparison(report: dict[str, Any]) -> None:
    """Pretty-print a model comparison table to the console."""
    print("\n=== Model Comparison (macro-averaged) ===")
    print(f"{'Model':<20}{'Accuracy':>10}{'Precision':>11}{'Recall':>9}{'F1':>8}")
    for name, m in report["models"].items():
        marker = "  <-- best" if name == report["best_model"] else ""
        print(
            f"{name:<20}{m['accuracy']:>10.3f}{m['precision_macro']:>11.3f}"
            f"{m['recall_macro']:>9.3f}{m['f1_macro']:>8.3f}{marker}"
        )
    print(f"\nCategories: {report['categories']}")


if __name__ == "__main__":
    _print_comparison(train())
