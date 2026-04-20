import ast
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


SUPPORTED_LANGUAGES = {"python", "cpp", "java"}
LANGUAGE_ALIASES = {
    "py": "python",
    "c++": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "hxx": "cpp",
}
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".c": "cpp",
    ".h": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".java": "java",
}


def normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    normalized = str(language).strip().lower()
    return LANGUAGE_ALIASES.get(normalized, normalized)


def infer_language_from_path(path: str | None) -> str | None:
    if not path:
        return None
    ext = Path(path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext)


def is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False


def _resolve_row_language(row: pd.Series) -> str | None:
    row_lang = normalize_language(row.get("language"))
    if row_lang in SUPPORTED_LANGUAGES:
        return row_lang
    return infer_language_from_path(row.get("path"))


def clean_dataset(df: pd.DataFrame, allowed_languages: Iterable[str] | None = None) -> pd.DataFrame:
    allowed = {normalize_language(lang) for lang in (allowed_languages or SUPPORTED_LANGUAGES)}
    allowed.discard(None)

    cleaned = df.copy()
    cleaned["code"] = cleaned["code"].fillna("").astype(str)
    cleaned = cleaned[cleaned["code"].str.strip().str.len() >= 8]

    cleaned["review_language"] = cleaned.apply(_resolve_row_language, axis=1)
    cleaned = cleaned[cleaned["review_language"].isin(allowed)]

    # Parse validation where we have a reliable parser.
    python_mask = cleaned["review_language"] == "python"
    if python_mask.any():
        cleaned = cleaned[~python_mask | cleaned["code"].apply(is_valid_python)]

    cleaned = cleaned.reset_index(drop=True)
    print("After cleaning:", len(cleaned))
    print("Language distribution after cleaning:")
    print(cleaned["review_language"].value_counts(dropna=False))
    return cleaned


def bug_risk_label(code: str, language: str = "python") -> int:
    language = normalize_language(language) or "python"
    score = 0

    normalized = code.replace(" ", "")

    # Generic risk hints.
    if "TODO" in code or "FIXME" in code:
        score += 1
    if "while(true)" in normalized or "for(;;)" in normalized:
        score += 2
    if re.search(r"/\s*0(?:[^\d.]|$)", code):
        score += 2

    if language == "python":
        if "try:" not in code or "except" not in code:
            score += 1
        if re.search(r"==\s*None", code):
            score += 1
        if "eval(" in code or "exec(" in code:
            score += 2
    elif language == "cpp":
        if re.search(r"\b(?:malloc|calloc|realloc)\s*\(", code) and "free(" not in code:
            score += 2
        if "new " in code and "delete " not in code:
            score += 2
        if re.search(r"\bgets\s*\(", code) or re.search(r"\bstrcpy\s*\(", code):
            score += 2
    elif language == "java":
        if re.search(r"\bnew\s+(?:Scanner|BufferedReader)\b", code) and ".close(" not in code:
            score += 2
        if re.search(r"\bcatch\s*\(\s*Exception", code):
            score += 1

    return 1 if score >= 2 else 0
