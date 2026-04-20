"""
Evaluate the analysis pipeline.

Compares rule-only vs ML-enhanced performance on labeled samples.
Reports precision, recall, F1, false positive rate, and latency.

Usage:
    python scripts/evaluate.py
"""

import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score

from src.predict import review_code

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS = [
    os.path.join(_ROOT, "datasets", "python_seed.jsonl"),
    os.path.join(_ROOT, "datasets", "python_train.jsonl"),
]
MODEL_PATH = os.path.join(_ROOT, "bug_risk_model.pkl")
MAX_SAMPLES = 500


def load_labeled_samples(paths, max_samples=MAX_SAMPLES):
    samples = []
    for path in paths:
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
                    label = obj.get("bug_risk", obj.get("label"))
                    if code and label is not None:
                        samples.append((code, int(label)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
                if len(samples) >= max_samples:
                    return samples
    return samples


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        loaded = pickle.load(f)
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded
    return {"model": loaded, "meta": {}}


def evaluate(samples, model, use_ml: bool) -> dict:
    y_true, y_pred, latencies = [], [], []
    fp = fn = 0

    for code, label in samples:
        t0 = time.perf_counter()
        result = review_code(
            code,
            model=model if use_ml else None,
            language="python",
        )
        latencies.append((time.perf_counter() - t0) * 1000)

        issues = result.get("issues", [])
        confidence = result.get("confidence", 0.0)
        predicted = 1 if (issues or confidence > 40) else 0

        y_true.append(label)
        y_pred.append(predicted)
        if predicted == 1 and label == 0:
            fp += 1
        elif predicted == 0 and label == 1:
            fn += 1

    yt = np.array(y_true)
    yp = np.array(y_pred)
    n_neg = max(1, int((yt == 0).sum()))

    return {
        "precision":          precision_score(yt, yp, zero_division=0),
        "recall":             recall_score(yt, yp, zero_division=0),
        "f1":                 f1_score(yt, yp, zero_division=0),
        "false_positive_rate": fp / n_neg,
        "avg_latency_ms":     float(np.mean(latencies)),
        "p95_latency_ms":     float(np.percentile(latencies, 95)),
        "n_samples":          len(samples),
    }


def print_table(rule: dict, ml: dict):
    metrics = [
        ("Precision",           "precision",           ".3f"),
        ("Recall",              "recall",              ".3f"),
        ("F1 Score",            "f1",                  ".3f"),
        ("False Positive Rate", "false_positive_rate", ".3f"),
        ("Avg Latency (ms)",    "avg_latency_ms",      ".1f"),
        ("P95 Latency (ms)",    "p95_latency_ms",      ".1f"),
    ]
    print("\n" + "=" * 65)
    print(f"{'Metric':<30} {'Rule-only':>15} {'ML-enhanced':>15}")
    print("=" * 65)
    for label, key, fmt in metrics:
        r = rule.get(key, 0)
        m = ml.get(key, 0)
        print(f"{label:<30} {r:>15{fmt}} {m:>15{fmt}}")
    print("=" * 65)
    print(f"Samples: {rule['n_samples']}")
    print()


def main():
    model = load_model()
    if model is None:
        print(f"No model found at {MODEL_PATH} — evaluating rule-only.")

    samples = load_labeled_samples(DATASETS)
    if not samples:
        print("No labeled samples (need 'bug_risk' or 'label' field in JSONL).")
        print("Generating synthetic labels from the rule engine instead...")
        # Fallback: label by whether the engine finds any issue
        raw = load_labeled_samples.__wrapped__ if hasattr(load_labeled_samples, '__wrapped__') else None
        all_codes = []
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
                            all_codes.append(code)
                    except json.JSONDecodeError:
                        continue
                    if len(all_codes) >= MAX_SAMPLES:
                        break

        from src.predict import review_code as _rc
        samples = []
        for code in all_codes[:MAX_SAMPLES]:
            r = _rc(code, model=None, language="python")
            label = 1 if r.get("issues") else 0
            samples.append((code, label))

    if not samples:
        print("Could not load any samples.")
        return

    print(f"Evaluating {len(samples)} samples...")
    rule_metrics = evaluate(samples, model=None,  use_ml=False)
    ml_metrics   = evaluate(samples, model=model, use_ml=True)
    print_table(rule_metrics, ml_metrics)


if __name__ == "__main__":
    main()
