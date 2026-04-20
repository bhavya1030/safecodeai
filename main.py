import argparse
from pathlib import Path

import numpy as np

from src.load_data import load_codesearchnet_data
from src.predict import extract_features
from src.preprocess import (
    SUPPORTED_LANGUAGES,
    bug_risk_label,
    clean_dataset,
    normalize_language,
)


def parse_languages(raw_languages: str) -> list[str]:
    langs = [normalize_language(x.strip()) for x in raw_languages.split(",") if x.strip()]
    langs = [lang for lang in langs if lang]
    if not langs:
        raise ValueError("No valid languages provided in --languages.")
    unsupported = [lang for lang in langs if lang not in SUPPORTED_LANGUAGES]
    if unsupported:
        raise ValueError(
            f"Unsupported languages: {', '.join(sorted(set(unsupported)))}. "
            f"Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )
    return sorted(set(langs))


def build_dataset(
    data_path: str,
    x_out: str,
    y_out: str,
    langs_out: str,
    languages: list[str],
    max_files: int | None,
    max_rows: int | None,
) -> None:
    df = load_codesearchnet_data(data_path, max_files=max_files, max_rows=max_rows)
    df = clean_dataset(df, allowed_languages=languages)

    print("Rows after cleaning:", len(df))
    if len(df) == 0:
        raise ValueError(
            "No rows remain after cleaning. Verify data path and selected languages."
        )

    df["bug_risk"] = df.apply(
        lambda row: bug_risk_label(row["code"], row["review_language"]),
        axis=1,
    )
    print("Label distribution by language:")
    print(df.groupby("review_language")["bug_risk"].value_counts(dropna=False))

    X = np.array(
        [
            extract_features(code, language=language)[0]
            for code, language in zip(df["code"], df["review_language"])
        ],
        dtype=np.float32,
    )
    y = np.array(df["bug_risk"].tolist(), dtype=np.int32)
    langs = np.array(df["review_language"].tolist())

    np.save(x_out, X)
    np.save(y_out, y)
    np.save(langs_out, langs)

    print(f"Saved features -> {x_out}")
    print(f"Saved labels   -> {y_out}")
    print(f"Saved langs    -> {langs_out}")
    print("Next step: run `python src/model.py` to train language-specific classifiers.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build training arrays for SafeCodeAI multi-language models."
    )
    parser.add_argument(
        "--data-path",
        default=".",
        help="Root folder containing JSONL files, C++ source files, or Java CSV datasets.",
    )
    parser.add_argument("--x-out", default="X_features.npy", help="Output path for features array.")
    parser.add_argument("--y-out", default="y_labels.npy", help="Output path for labels array.")
    parser.add_argument(
        "--langs-out",
        default="language_labels.npy",
        help="Output path for per-row language labels.",
    )
    parser.add_argument(
        "--languages",
        default="python,cpp,java",
        help="Comma-separated language list to include.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional per-format cap on discovered input files.",
    )
    parser.add_argument("--max-rows", type=int, default=None, help="Optional cap on number of rows.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected_languages = parse_languages(args.languages)
    build_dataset(
        data_path=str(Path(args.data_path)),
        x_out=str(Path(args.x_out)),
        y_out=str(Path(args.y_out)),
        langs_out=str(Path(args.langs_out)),
        languages=selected_languages,
        max_files=args.max_files,
        max_rows=args.max_rows,
    )
