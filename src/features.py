from typing import Optional

from src.predict import extract_features as extract_features_multi
from src.predict import resolve_review_language


def extract_features(
    code: str,
    language: Optional[str] = None,
    filename: Optional[str] = None,
    full: bool = False,
):
    review_language = resolve_review_language(language=language, filename=filename, code=code)
    values = extract_features_multi(code, language=review_language)[0].tolist()
    if full:
        return values
    # Backward-compatible legacy shape used by older scripts.
    return values[:5]
