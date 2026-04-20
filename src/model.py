import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    fbeta_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.metrics import make_scorer
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split


FEATURE_NAMES = [
    "num_lines",
    "num_funcs",
    "num_loops",
    "num_ifs",
    "num_try",
    "div_zero_hits",
    "infinite_loop_hits",
    "input_ops",
    "sort_ops",
    "alloc_ops",
    "release_ops",
    "risky_api_ops",
]
SUPPORTED_LANGUAGES = ("python", "cpp", "java")
LANGUAGE_THRESHOLD_BETA = {
    "python": 1.0,
    "cpp": 1.0,
    "java": 2.0,  # used as fallback if recall-constrained selection cannot be met
}
LANGUAGE_SEARCH_BETA = {
    "python": 1.0,
    "cpp": 1.0,
    "java": 2.0,  # tune candidates with recall-weighted objective
}
LANGUAGE_MIN_RECALL = {
    "java": 0.70,  # prefer at least this recall, then maximize F1
}


def _min_class_count(y: np.ndarray) -> int:
    _, counts = np.unique(y, return_counts=True)
    return int(counts.min()) if len(counts) else 0


def _find_best_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    beta: float = 1.0,
    min_recall: float | None = None,
) -> dict:
    beta = max(0.1, float(beta))
    beta_sq = beta ** 2
    candidates = np.linspace(0.05, 0.95, 181)
    best = {
        "threshold": 0.5,
        "f1": -1.0,
        "fbeta": -1.0,
        "precision": 0.0,
        "recall": 0.0,
        "beta": beta,
        "min_recall": None if min_recall is None else float(min_recall),
    }
    qualifying: list[dict] = []

    for threshold in candidates:
        y_pred = (y_prob >= threshold).astype(int)
        if y_pred.sum() == 0:
            continue

        f1 = f1_score(y_true, y_pred, zero_division=0)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        fbeta = (1.0 + beta_sq) * precision * recall / max((beta_sq * precision + recall), 1e-12)
        row = {
            "threshold": float(threshold),
            "f1": float(f1),
            "fbeta": float(fbeta),
            "precision": float(precision),
            "recall": float(recall),
            "beta": beta,
            "min_recall": None if min_recall is None else float(min_recall),
        }
        if min_recall is not None and recall >= float(min_recall):
            qualifying.append(row)

        if (
            fbeta > best["fbeta"]
            or (fbeta == best["fbeta"] and recall > best["recall"])
            or (
                fbeta == best["fbeta"]
                and recall == best["recall"]
                and threshold < best["threshold"]
            )
        ):
            best = row

    if qualifying:
        # First satisfy recall target, then keep the strongest F1 operating point.
        best = max(
            qualifying,
            key=lambda item: (
                item["f1"],
                item["precision"],
                -item["threshold"],
            ),
        )

    if best["fbeta"] < 0:
        y_pred = (y_prob >= 0.5).astype(int)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        fbeta = (1.0 + beta_sq) * precision * recall / max((beta_sq * precision + recall), 1e-12)
        best = {
            "threshold": 0.5,
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "fbeta": float(fbeta),
            "precision": float(precision),
            "recall": float(recall),
            "beta": beta,
            "min_recall": None if min_recall is None else float(min_recall),
        }

    return best


def _train_one_language(
    X: np.ndarray,
    y: np.ndarray,
    language: str,
    random_state: int,
) -> tuple[object, dict]:
    if len(X) == 0 or len(y) == 0:
        raise ValueError(f"{language}: empty dataset.")
    if len(np.unique(y)) < 2:
        raise ValueError(f"{language}: requires at least 2 classes.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
        stratify=y,
    )

    min_train_class = _min_class_count(y_train)
    if min_train_class < 2:
        raise ValueError(
            f"{language}: not enough samples per class after split."
        )

    base_model = RandomForestClassifier(
        random_state=random_state,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    param_dist = {
        "n_estimators": [200, 300, 500, 700],
        "max_depth": [None, 8, 12, 20, 30],
        "min_samples_split": [2, 4, 8, 12],
        "min_samples_leaf": [1, 2, 4, 6],
        "max_features": ["sqrt", "log2", None],
    }
    search_beta = LANGUAGE_SEARCH_BETA.get(language, 1.0)
    if abs(search_beta - 1.0) < 1e-9:
        scoring = "f1"
    else:
        scoring = make_scorer(fbeta_score, beta=search_beta, zero_division=0)

    tuner_cv_splits = min(5, min_train_class)
    cv = StratifiedKFold(n_splits=tuner_cv_splits, shuffle=True, random_state=random_state)
    tuner = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_dist,
        n_iter=25,
        scoring=scoring,
        cv=cv,
        n_jobs=-1,
        random_state=random_state,
        verbose=1,
    )
    tuner.fit(X_train, y_train)

    calibrator_cv_splits = min(3, min_train_class)
    calibrated_model = CalibratedClassifierCV(
        estimator=tuner.best_estimator_,
        method="sigmoid",
        cv=calibrator_cv_splits,
    )
    calibrated_model.fit(X_train, y_train)

    y_train_prob = calibrated_model.predict_proba(X_train)[:, 1]
    threshold_beta = LANGUAGE_THRESHOLD_BETA.get(language, 1.0)
    min_recall = LANGUAGE_MIN_RECALL.get(language)
    threshold_meta = _find_best_threshold(
        y_train,
        y_train_prob,
        beta=threshold_beta,
        min_recall=min_recall,
    )
    decision_threshold = float(threshold_meta["threshold"])

    y_prob = calibrated_model.predict_proba(X_test)[:, 1]
    y_pred_default = (y_prob >= 0.5).astype(int)
    y_pred = (y_prob >= decision_threshold).astype(int)

    report_dict = classification_report(y_test, y_pred, output_dict=True)
    f1 = f1_score(y_test, y_pred)
    default_f1 = f1_score(y_test, y_pred_default, zero_division=0)
    auc = roc_auc_score(y_test, y_prob) if len(np.unique(y_test)) > 1 else 0.5

    print(f"\n=== {language.upper()} ===")
    print(classification_report(y_test, y_pred))
    print(f"Decision threshold: {decision_threshold:.3f}")
    print(f"Threshold beta  : {threshold_beta:.2f}")
    if min_recall is not None:
        print(f"Recall floor    : {min_recall:.2f}")
    print(f"Threshold F-beta: {threshold_meta['fbeta']:.4f}")
    print(f"F1 @ 0.50       : {default_f1:.4f}")
    print(f"ROC-AUC: {auc:.4f}")
    print(f"F1 @ tuned thr  : {f1:.4f}")

    meta = {
        "language": language,
        "n_samples": int(len(X)),
        "n_features": int(X.shape[1]),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "cv_splits_tuner": int(tuner_cv_splits),
        "cv_splits_calibrator": int(calibrator_cv_splits),
        "best_params": tuner.best_params_,
        "search_beta": float(search_beta),
        "best_cv_score_f1": float(tuner.best_score_),
        "decision_threshold": decision_threshold,
        "threshold_selection_train": threshold_meta,
        "metrics": {
            "f1": float(f1),
            "f1_default_threshold": float(default_f1),
            "roc_auc": float(auc),
            "classification_report": report_dict,
        },
    }
    return calibrated_model, meta


def train_model(
    x_path: str,
    y_path: str,
    langs_path: str | None,
    model_out: str,
    metrics_out: str | None = None,
    random_state: int = 42,
) -> None:
    X = np.load(x_path)
    y = np.load(y_path)
    langs = np.load(langs_path).astype(str) if langs_path else None

    if len(X) == 0 or len(y) == 0:
        raise ValueError("Empty dataset. Build features first using `python main.py`.")
    if len(X) != len(y):
        raise ValueError("Feature and label lengths do not match.")
    if langs is not None and len(langs) != len(y):
        raise ValueError("Language labels length does not match y.")

    models: dict[str, object] = {}
    language_meta: dict[str, dict] = {}
    skipped_languages: dict[str, str] = {}

    training_languages = sorted(set(langs.tolist())) if langs is not None else ["python"]

    for language in training_languages:
        if language not in SUPPORTED_LANGUAGES:
            skipped_languages[language] = "unsupported_language"
            continue

        if langs is None:
            lang_mask = np.ones(len(y), dtype=bool)
        else:
            lang_mask = langs == language

        X_lang = X[lang_mask]
        y_lang = y[lang_mask]

        try:
            model, meta = _train_one_language(
                X=X_lang,
                y=y_lang,
                language=language,
                random_state=random_state,
            )
            models[language] = model
            language_meta[language] = meta
        except ValueError as exc:
            skipped_languages[language] = str(exc)
            print(f"Skipping {language}: {exc}")

    if not models:
        raise ValueError("No language models were trained. Check dataset size/class balance.")

    default_language = "python" if "python" in models else next(iter(models.keys()))
    model_package = {
        "model": models[default_language],
        "models": models,
        "meta": {
            "artifact_version": "3.0",
            "model_family": "random_forest_calibrated_multi_language",
            "trained_at_utc": datetime.now(timezone.utc).isoformat(),
            "random_state": random_state,
            "feature_names": FEATURE_NAMES,
            "total_samples": int(len(X)),
            "default_language": default_language,
            "trained_languages": sorted(models.keys()),
            "skipped_languages": skipped_languages,
            "language_metrics": language_meta,
            "decision_thresholds": {
                lang: float(meta.get("decision_threshold", 0.5))
                for lang, meta in language_meta.items()
            },
        },
    }

    with open(model_out, "wb") as f:
        pickle.dump(model_package, f)
    print(f"Model package saved -> {model_out}")

    if metrics_out:
        with open(metrics_out, "w", encoding="utf-8") as f:
            json.dump(model_package["meta"], f, indent=2)
        print(f"Metrics/meta saved -> {metrics_out}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and calibrate SafeCodeAI multi-language bug-risk models."
    )
    parser.add_argument("--x-path", default="X_features.npy", help="Path to feature array.")
    parser.add_argument("--y-path", default="y_labels.npy", help="Path to labels array.")
    parser.add_argument(
        "--langs-path",
        default="language_labels.npy",
        help="Path to per-row language labels (npy).",
    )
    parser.add_argument("--model-out", default="bug_risk_model.pkl", help="Output path for model artifact.")
    parser.add_argument(
        "--metrics-out",
        default="model_metrics.json",
        help="Optional output JSON for training metrics/metadata.",
    )
    parser.add_argument("--random-state", type=int, default=42, help="Random seed.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_model(
        x_path=str(Path(args.x_path)),
        y_path=str(Path(args.y_path)),
        langs_path=str(Path(args.langs_path)) if args.langs_path else None,
        model_out=str(Path(args.model_out)),
        metrics_out=str(Path(args.metrics_out)) if args.metrics_out else None,
        random_state=args.random_state,
    )
