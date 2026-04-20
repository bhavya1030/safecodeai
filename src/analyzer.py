import ast
from typing import Optional

from src.predict import resolve_review_language, review_code


def find_syntax_error(code: str, language: Optional[str] = None, filename: Optional[str] = None):
    review_language = resolve_review_language(language=language, filename=filename, code=code)

    if review_language == "python":
        try:
            tree = ast.parse(code)
            return None, tree
        except SyntaxError as exc:
            return {
                "type": "SyntaxError",
                "line": exc.lineno,
                "message": exc.msg,
            }, None

    result = review_code(code, model=None, language=review_language, filename=filename)
    if result.get("syntax_error"):
        return {
            "type": "SyntaxError",
            "line": result.get("error_line"),
            "message": result.get("error_msg", ""),
        }, None
    return None, None


def find_logical_issues(
    code: str,
    tree=None,
    language: Optional[str] = None,
    filename: Optional[str] = None,
):
    review_language = resolve_review_language(language=language, filename=filename, code=code)
    result = review_code(code, model=None, language=review_language, filename=filename)
    return [(name, line) for name, line, _ in result.get("issues", [])]
