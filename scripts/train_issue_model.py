"""
Train an issue-type classifier (XGBoost or GradientBoosting fallback).

Loads existing datasets, runs the rule-based engine to generate synthetic
labels, extracts features, trains a multi-class classifier, and saves the
artifact to models/issue_model.pkl.

Usage:
    python scripts/train_issue_model.py
"""

import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from src.predict import extract_features, review_code

try:
    from xgboost import XGBClassifier
    _USE_XGB = True
except ImportError:
    _USE_XGB = False
    print("xgboost not found — using GradientBoostingClassifier instead.")
    print("Install with: pip install xgboost")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = [
    os.path.join(_ROOT, "datasets", "python_seed.jsonl"),
    os.path.join(_ROOT, "datasets", "python_train.jsonl"),
]
OUTPUT_PATH = os.path.join(_ROOT, "models", "issue_model.pkl")


def load_samples():
    samples = []
    for path in DATASETS:
        if not os.path.exists(path):
            print(f"  skipping {path} (not found)")
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    code = (obj.get("code")
                            or obj.get("func_code_string")
                            or obj.get("whole_func_string", ""))
                    if code and len(code) > 20:
                        samples.append(code)
                except json.JSONDecodeError:
                    continue
    return samples


def get_primary_issue(code: str) -> str:
    """Return the name of the first detected issue, or 'clean'."""
    result = review_code(code, model=None, language="python")
    issues = result.get("issues", [])
    return issues[0][0] if issues else "clean"


def build_dataset(samples):
    X, y = [], []
    print(f"Processing {len(samples)} samples...")
    for i, code in enumerate(samples):
        if i % 250 == 0:
            print(f"  {i}/{len(samples)}")
        try:
            feats = extract_features(code, "python")[0].tolist()
            label = get_primary_issue(code)
            X.append(feats)
            y.append(label)
        except Exception:
            continue
    return np.array(X), np.array(y)


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    samples = load_samples()
    if not samples:
        print("No samples found. Check datasets/ directory.")
        return

    X, y = build_dataset(samples)
    print(f"\nBuilt dataset: {X.shape[0]} samples, {len(set(y))} unique labels")

    # Drop classes with < 2 samples (can't split)
    from collections import Counter
    counts = Counter(y)
    mask = np.array([counts[label] >= 2 for label in y])
    X, y = X[mask], y[mask]
    print(f"After filtering rare classes: {X.shape[0]} samples")

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )
    weights = compute_sample_weight("balanced", y_train)

    print(f"\nTraining {'XGBClassifier' if _USE_XGB else 'GradientBoostingClassifier'}...")
    if _USE_XGB:
        clf = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
            verbosity=0,
        )
    else:
        clf = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )

    clf.fit(X_train, y_train, sample_weight=weights)

    y_pred = clf.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    artifact = {"model": clf, "label_encoder": le, "feature_count": X.shape[1]}
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
