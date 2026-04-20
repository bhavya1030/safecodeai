"""
Train a severity classifier (LOW / MEDIUM / HIGH / CRITICAL).

Labels are derived from the rule-based engine + template severity hints.
High rule confidence boosts the severity label.
Saves artifact to models/severity_model.pkl.

Usage:
    python scripts/train_severity_model.py
"""

import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from src.predict import extract_features, review_code
from src.templates.templates import TEMPLATES, _DEFAULT_TEMPLATE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = [
    os.path.join(_ROOT, "datasets", "python_seed.jsonl"),
    os.path.join(_ROOT, "datasets", "python_train.jsonl"),
]
OUTPUT_PATH = os.path.join(_ROOT, "models", "severity_model.pkl")

_SEVERITY_RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
_BOOST_THRESHOLD = 80.0  # confidence level that triggers severity boost


def _issue_severity(issue_name: str, confidence: float) -> str:
    tmpl = TEMPLATES.get(issue_name, _DEFAULT_TEMPLATE)
    sev = tmpl.get("severity_hint", "MEDIUM")

    # Boost severity when rule confidence is high
    if confidence >= _BOOST_THRESHOLD:
        if sev == "MEDIUM":
            sev = "HIGH"
        elif sev == "LOW":
            sev = "MEDIUM"

    # Compiler errors always at least HIGH
    if "Compiler Error" in issue_name:
        sev = "CRITICAL"

    return sev


def _worst_severity(issues, confidence: float) -> str:
    if not issues:
        return "LOW"
    severities = [_issue_severity(name, confidence) for name, _, _ in issues]
    return max(severities, key=lambda s: _SEVERITY_RANK.get(s, 0))


def load_samples():
    samples = []
    for path in DATASETS:
        if not os.path.exists(path):
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


def build_dataset(samples):
    X, y = [], []
    print(f"Processing {len(samples)} samples...")
    for i, code in enumerate(samples):
        if i % 250 == 0:
            print(f"  {i}/{len(samples)}")
        try:
            feats = extract_features(code, "python")[0].tolist()
            result = review_code(code, model=None, language="python")
            label = _worst_severity(
                result.get("issues", []),
                result.get("confidence", 0.0),
            )
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
    print(f"\nBuilt dataset: {X.shape[0]} samples")
    from collections import Counter
    print("Label distribution:", Counter(y))

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )
    weights = compute_sample_weight("balanced", y_train)

    print("\nTraining RandomForestClassifier + isotonic calibration...")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    clf = CalibratedClassifierCV(rf, method="isotonic", cv=3)
    clf.fit(X_train, y_train, sample_weight=weights)

    y_pred = clf.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    artifact = {"model": clf, "label_encoder": le}
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"Saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
