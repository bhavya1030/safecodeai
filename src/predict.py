import ast
import os
import re
import shutil
import subprocess
import tempfile

import numpy as np

# ── Optional ranking (loaded lazily to avoid circular imports) ─────────────────
try:
    from src.models.ranker import rank_issues as _rank_issues
except ImportError:
    _rank_issues = None

# ── Feature cache (avoids re-computing for repeated requests) ─────────────────
_FEATURE_CACHE: dict = {}
_FEATURE_CACHE_MAX = 256


SUPPORTED_REVIEW_LANGUAGES = {"python", "cpp", "java"}

LANGUAGE_ALIASES = {
    "py": "python",
    "c++": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "hxx": "cpp",
}

EXTENSION_LANGUAGE_MAP = {
    "py": "python",
    "c": "cpp",
    "h": "cpp",
    "cpp": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "hpp": "cpp",
    "java": "java",
}

CPP_CODE_HINT_PATTERN = re.compile(
    r"#include\s*<|std::|using\s+namespace\s+std\b|\b(?:cout|cin)\s*<<|\bint\s+main\s*\(",
    flags=re.I,
)
JAVA_CODE_HINT_PATTERN = re.compile(
    r"\bpublic\s+class\b|\bimport\s+java\.|\bSystem\.out\.println\s*\(|\bnew\s+Scanner\s*\(",
    flags=re.I,
)

FUNCTION_SIGNATURE_PATTERN = re.compile(
    r"^\s*"
    r"(?:(?:public|private|protected|static|final|virtual|inline|constexpr|friend|"
    r"synchronized|native|abstract)\s+)*"
    r"(?P<return_type>[\w:<>\[\],*&]+)"
    r"\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\s*\([^;{}]*\)"
    r"\s*(?P<brace>\{)?\s*$"
)

LOOP_PATTERN = re.compile(r"\b(?:for|while)\s*\(")
IF_PATTERN = re.compile(r"\bif\s*\(")
TRY_PATTERN = re.compile(r"\btry\s*\{")
DIVISION_BY_ZERO_PATTERN = re.compile(r"/\s*0(?:[^\d.]|$)")
INFINITE_LOOP_PATTERN = re.compile(r"\bwhile\s*\(\s*true\s*\)|\bfor\s*\(\s*;\s*;\s*\)")
MISSING_SEMICOLON_PATTERN = re.compile(r"^\s*return\b[^;{}]*$")
# Matches C++/Java statement lines ending with ) that are likely missing a semicolon.
# Excludes: control-flow keywords, function/method definitions (followed by {).
CPP_STMT_MISSING_SEMICOLON_PATTERN = re.compile(
    r"^(?!\s*(?:if|else\s+if|for|while|do|switch|catch)\s*\()"
    r"(?!\s*(?:public|private|protected)\s*:)"
    r".*\)\s*$"
)
# Matches a line (after string normalization) that ends with a string/char literal
# but has no semicolon — excludes preprocessor directives.
CPP_LITERAL_MISSING_SEMICOLON_PATTERN = re.compile(r"""["']\s*$""")

INPUT_PATTERNS = {
    "cpp": re.compile(r"\bcin\s*>>|\bgetline\s*\("),
    "java": re.compile(
        r"\.next(?:Int|Line|Double|Long|Float|Boolean|Short|Byte)\s*\(|\breadLine\s*\("
    ),
}

SORT_PATTERNS = {
    "cpp": re.compile(r"\bsort\s*\("),
    "java": re.compile(r"\b(?:Arrays|Collections)\.sort\s*\("),
}

MEMORY_ALLOC_PATTERNS = {
    "cpp": re.compile(r"\b(?:malloc|calloc|realloc)\s*\(|\bnew\b"),
}

MEMORY_RELEASE_PATTERNS = {
    "cpp": re.compile(r"\bfree\s*\(|\bdelete\b"),
}

JAVA_RESOURCE_PATTERN = re.compile(
    r"\bnew\s+(?:Scanner|BufferedReader|FileInputStream|FileReader|InputStreamReader)\b"
)
JAVA_CLOSE_PATTERN = re.compile(r"\.close\s*\(")
JAVA_BROAD_EXCEPTION_PATTERN = re.compile(r"\bcatch\s*\(\s*Exception\b")
CPP_RISKY_API_PATTERN = re.compile(r"\b(?:gets|strcpy)\s*\(")
PY_INPUT_PATTERN = re.compile(r"\binput\s*\(")
PY_SORT_PATTERN = re.compile(r"\.sort\s*\(")
PY_ALLOC_PATTERN = re.compile(r"\bopen\s*\(")
PY_RELEASE_PATTERN = re.compile(r"\.close\s*\(")
PY_RISKY_API_PATTERN = re.compile(r"\b(?:eval|exec)\s*\(")

# --- C++ / Java DSA checks ---
# Assignment inside if condition: if (x = 5) instead of if (x == 5)
CPP_ASSIGN_IN_COND_PATTERN = re.compile(r"\bif\s*\(\s*[A-Za-z_]\w*\s*=[^=<>!&|]")
# endl flushes the buffer — slow in loops
CPP_ENDL_PATTERN = re.compile(r"<<\s*(?:std::)?endl\b")
# pow() result stored in int/long — loses precision and wrong for large exponents
CPP_POW_TO_INT_PATTERN = re.compile(r"\b(?:int|long)\b[^;()\n]*=\s*[^;()\n]*\bpow\s*\(")
# Large constant that overflows 32-bit int
CPP_INT_OVERFLOW_PATTERN = re.compile(r"\bint\b[^;\n]*=\s*[^;\n]*\b(?:[2-9]\d{9,}|1\d{10,}|\d+\s*\*\s*\d+[eE]\d+)\b")
# printf/scanf mixed with cout/cin (sync issue unless sync_off called)
CPP_PRINTF_PATTERN = re.compile(r"\b(?:printf|scanf|puts|fputs|fprintf)\s*\(")
CPP_COUT_PATTERN = re.compile(r"\b(?:cout|cin)\s*(?:<<|>>)")
# Null pointer dereference risk after malloc without null check
CPP_MALLOC_NO_NULL_CHECK = re.compile(r"\b(?:malloc|calloc|realloc)\s*\([^;]+\)\s*;")
# Java: comparing strings with == instead of .equals()
JAVA_STRING_EQ_PATTERN = re.compile(r'(?:==|!=)\s*"[^"]*"')
# Java: string concatenation inside loop (should use StringBuilder)
JAVA_STRING_CONCAT_PATTERN = re.compile(r"\b(\w+)\s*\+=\s*[^\d]|\b(\w+)\s*=\s*\2\s*\+")
# Java: catching broad Exception
JAVA_BROAD_CATCH_PATTERN = re.compile(r"\bcatch\s*\(\s*Exception\b")
# Java: integer overflow — int used for product that needs long
JAVA_INT_OVERFLOW_PATTERN = re.compile(r"\bint\b[^;\n]*=\s*[^;\n]*\*[^;\n]*\b(?:\d{5,}|[a-zA-Z]\w*\s*\*\s*[a-zA-Z]\w*)\b")
# Switch case without break (heuristic: 'case X:' not followed by break/return/throw before next case)
SWITCH_CASE_PATTERN = re.compile(r"^\s*(?:case\b.+|default\s*):\s*$|^\s*(?:case\b.+|default\s*):\s*\S")
SWITCH_BREAK_PATTERN = re.compile(r"\b(?:break|return|throw|continue|goto)\b")
SWITCH_OPEN_PATTERN = re.compile(r"\bswitch\s*\(")


def normalize_language(language):
    if not language:
        return None
    normalized = language.strip().lower()
    return LANGUAGE_ALIASES.get(normalized, normalized)


def detect_language_from_filename(filename):
    if not filename or "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    return EXTENSION_LANGUAGE_MAP.get(ext)


def infer_language_from_code(code):
    if not code:
        return None
    if CPP_CODE_HINT_PATTERN.search(code):
        return "cpp"
    if JAVA_CODE_HINT_PATTERN.search(code):
        return "java"
    return None


def resolve_review_language(language=None, filename=None, code=None):
    detected = detect_language_from_filename(filename)
    if detected in SUPPORTED_REVIEW_LANGUAGES:
        return detected

    normalized = normalize_language(language)
    if normalized in SUPPORTED_REVIEW_LANGUAGES:
        return normalized

    inferred = infer_language_from_code(code)
    if inferred in SUPPORTED_REVIEW_LANGUAGES:
        return inferred

    return "python"


def _normalize_strings_in_line(line):
    """Replace string/char literal content with empty, keeping the delimiters."""
    result = []
    in_str = None
    i = 0
    while i < len(line):
        c = line[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                result.append(c)
                in_str = None
            i += 1
        else:
            result.append(c)
            if c in ('"', "'"):
                in_str = c
            i += 1
    return ''.join(result)


def strip_c_like_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"//.*", "", code)


def basic_c_like_syntax_error(code):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    state = "normal"
    string_start_line = 1
    line = 1
    escape = False
    i = 0

    while i < len(code):
        ch = code[i]
        nxt = code[i + 1] if i + 1 < len(code) else ""

        if state == "line_comment":
            if ch == "\n":
                state = "normal"
                line += 1
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "normal"
                i += 2
                continue
            if ch == "\n":
                line += 1
            i += 1
            continue

        if state in {"single_quote", "double_quote"}:
            if ch == "\n":
                line += 1
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif state == "single_quote" and ch == "'":
                state = "normal"
            elif state == "double_quote" and ch == '"':
                state = "normal"
            i += 1
            continue

        if ch == "/" and nxt == "/":
            state = "line_comment"
            i += 2
            continue

        if ch == "/" and nxt == "*":
            state = "block_comment"
            i += 2
            continue

        if ch == "'":
            state = "single_quote"
            string_start_line = line
            i += 1
            continue

        if ch == '"':
            state = "double_quote"
            string_start_line = line
            i += 1
            continue

        if ch in "([{":
            stack.append((ch, line))
        elif ch in ")]}":
            if not stack or stack[-1][0] != pairs[ch]:
                return {
                    "line": line,
                    "message": f"Unmatched '{ch}' in code block",
                }
            stack.pop()

        if ch == "\n":
            line += 1

        i += 1

    if state == "double_quote":
        return {
            "line": string_start_line,
            "message": "Unclosed string literal",
        }
    if state == "single_quote":
        return {
            "line": string_start_line,
            "message": "Unclosed character literal",
        }

    if stack:
        opener, opener_line = stack[-1]
        return {
            "line": opener_line,
            "message": f"Unclosed '{opener}' in code block",
        }

    return None


def extract_features(code, language="python"):
    language = resolve_review_language(language)
    num_lines = max(1, len(code.splitlines()))
    div_zero_hits = len(DIVISION_BY_ZERO_PATTERN.findall(code))
    infinite_loop_hits = len(INFINITE_LOOP_PATTERN.findall(code))
    input_ops = 0
    sort_ops = 0
    alloc_ops = 0
    release_ops = 0
    risky_api_ops = 0

    if language == "python":
        try:
            tree = ast.parse(code)
            num_funcs = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
            num_loops = sum(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
            num_ifs = sum(isinstance(node, ast.If) for node in ast.walk(tree))
            num_try = sum(isinstance(node, ast.Try) for node in ast.walk(tree))
        except SyntaxError:
            num_funcs = num_loops = num_ifs = num_try = 0

        input_ops = len(PY_INPUT_PATTERN.findall(code))
        sort_ops = len(PY_SORT_PATTERN.findall(code))
        alloc_ops = len(PY_ALLOC_PATTERN.findall(code))
        release_ops = len(PY_RELEASE_PATTERN.findall(code))
        risky_api_ops = len(PY_RISKY_API_PATTERN.findall(code))
    else:
        stripped = strip_c_like_comments(code)
        num_funcs = len(FUNCTION_SIGNATURE_PATTERN.findall(stripped))
        num_loops = len(LOOP_PATTERN.findall(stripped))
        num_ifs = len(IF_PATTERN.findall(stripped))
        num_try = len(TRY_PATTERN.findall(stripped))
        div_zero_hits = len(DIVISION_BY_ZERO_PATTERN.findall(stripped))
        infinite_loop_hits = len(INFINITE_LOOP_PATTERN.findall(stripped))

        input_pattern = INPUT_PATTERNS.get(language)
        sort_pattern = SORT_PATTERNS.get(language)
        alloc_pattern = MEMORY_ALLOC_PATTERNS.get(language)
        release_pattern = MEMORY_RELEASE_PATTERNS.get(language)
        input_ops = len(input_pattern.findall(stripped)) if input_pattern else 0
        sort_ops = len(sort_pattern.findall(stripped)) if sort_pattern else 0
        alloc_ops = len(alloc_pattern.findall(stripped)) if alloc_pattern else 0
        release_ops = len(release_pattern.findall(stripped)) if release_pattern else 0

        if language == "cpp":
            risky_api_ops = len(CPP_RISKY_API_PATTERN.findall(stripped))
        elif language == "java":
            risky_api_ops = len(JAVA_BROAD_EXCEPTION_PATTERN.findall(stripped))
            alloc_ops += len(JAVA_RESOURCE_PATTERN.findall(stripped))
            release_ops += len(JAVA_CLOSE_PATTERN.findall(stripped))

    return np.array(
        [[
            num_lines,
            num_funcs,
            num_loops,
            num_ifs,
            num_try,
            div_zero_hits,
            infinite_loop_hits,
            input_ops,
            sort_ops,
            alloc_ops,
            release_ops,
            risky_api_ops,
        ]]
    )


def estimate_confidence(features, issues_count, language, model):
    language = resolve_review_language(language)
    loops = int(features[0][2])
    conditionals = int(features[0][3])

    # Fast-path 1: rules already found multiple issues — no need for ML.
    if issues_count >= 2:
        return round(min(95.0, float(issues_count * 18 + loops * 10 + conditionals * 4)), 2)

    # Fast-path 2: simple, clean-looking code — ML adds little value here.
    # ML is most useful for complex code with no rule violations.
    if issues_count == 0 and loops <= 1 and conditionals <= 2:
        return round(float(loops * 8 + conditionals * 3), 2)

    estimator = None
    if isinstance(model, dict):
        model_map = model.get("models") if isinstance(model.get("models"), dict) else None
        if model_map:
            estimator = model_map.get(language) or model_map.get("python")
        if estimator is None:
            estimator = model.get("model")
    else:
        estimator = model

    if estimator is not None:
        try:
            probability = float(estimator.predict_proba(features)[0][1])
            threshold = 0.5
            if isinstance(model, dict):
                thresholds = model.get("meta", {}).get("decision_thresholds", {})
                threshold = float(
                    thresholds.get(language, thresholds.get("python", 0.5))
                )
            threshold = min(max(threshold, 0.05), 0.95)

            if probability >= threshold:
                scaled = 50.0 + 50.0 * (probability - threshold) / (1.0 - threshold)
            else:
                scaled = 50.0 * (probability / threshold)

            # Each detected issue adds penalty on top of ML score
            scaled = min(100.0, scaled + issues_count * 15.0)
            return round(float(min(100.0, max(0.0, scaled))), 2)
        except Exception:
            pass

    heuristic_confidence = min(
        95.0,
        float(issues_count * 16 + loops * 10 + conditionals * 4),
    )
    return round(heuristic_confidence, 2)


def _extract_java_classname(code):
    """Return the public class name from Java source, or 'Main' as fallback."""
    m = re.search(r'\bpublic\s+class\s+([A-Za-z_]\w*)', code)
    return m.group(1) if m else "Main"


def _compiler_issues(code, language):
    """
    Compile code with the system compiler and return a list of (name, line, fix) tuples.
    Returns an empty list if no compiler is found or compilation succeeds cleanly.
    """
    issues = []

    if language == "cpp":
        compiler = shutil.which("g++") or shutil.which("g++.exe")
        if not compiler:
            return []
        suffix = ".cpp"
    elif language == "java":
        compiler = shutil.which("javac") or shutil.which("javac.exe")
        if not compiler and os.name == "nt":
            for base in [
                r"C:\Program Files\Microsoft",
                r"C:\Program Files\Eclipse Adoptium",
                r"C:\Program Files\Java",
                r"C:\Program Files\OpenJDK",
            ]:
                if os.path.isdir(base):
                    for entry in sorted(os.listdir(base), reverse=True):
                        candidate = os.path.join(base, entry, "bin", "javac.exe")
                        if os.path.isfile(candidate):
                            compiler = candidate
                            break
                if compiler:
                    break
        if not compiler:
            return []
        suffix = ".java"
    else:
        return []

    tmpdir = tempfile.mkdtemp()
    try:
        if language == "java":
            classname = _extract_java_classname(code)
            src_path = os.path.join(tmpdir, f"{classname}.java")
        else:
            src_path = os.path.join(tmpdir, f"code{suffix}")

        with open(src_path, "w", encoding="utf-8") as f:
            f.write(code)

        if language == "cpp":
            cmd = [compiler, "-fsyntax-only", "-Wall", "-Wextra",
                   "-Wno-unused-parameter", "-std=c++17", src_path]
        else:
            cmd = [compiler, "-nowarn", src_path]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = proc.stderr + proc.stdout

        if language == "cpp":
            # g++ format: file:line:col: error/warning: message
            pattern = re.compile(
                r"(?:error|warning):\s*(.+)",
            )
            line_pattern = re.compile(r":(\d+):\d+:\s*(error|warning):\s*(.+)")
            for m in line_pattern.finditer(output):
                lineno = int(m.group(1))
                kind = m.group(2)
                msg = m.group(3).strip()
                # Skip noisy notes and trivial warnings
                if any(skip in msg for skip in [
                    "note:", "In function", "At global scope",
                    "[-Wmain]", "unused variable",
                ]):
                    continue
                name = "Compiler Error" if kind == "error" else "Compiler Warning"
                fix = msg
                issues.append((name, lineno, fix))

        elif language == "java":
            # javac format: file:line: error: message
            line_pattern = re.compile(r":(\d+):\s*(error|warning):\s*(.+)")
            for m in line_pattern.finditer(output):
                lineno = int(m.group(1))
                kind = m.group(2)
                msg = m.group(3).strip()
                name = "Compiler Error" if kind == "error" else "Compiler Warning"
                issues.append((name, lineno, msg))

    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    finally:
        import shutil as _sh
        _sh.rmtree(tmpdir, ignore_errors=True)

    return issues


def _check_array_oob(code, language):
    """
    Statically detect array accesses at literal indices that exceed the declared size.
    Handles initializer-list and new-expression declarations in Java and C++.
    Returns a list of (name, line, fix) tuples.
    """
    issues = []
    clean = strip_c_like_comments(code)
    lines = clean.splitlines()

    # Map: array variable name -> declared size
    array_sizes = {}

    if language == "java":
        init_re = re.compile(
            r'\b\w+\s*\[\s*\]\s+(\w+)\s*=\s*\{([^}]*)\}'
        )
        new_re = re.compile(
            r'\b\w+\s*\[\s*\]\s+(\w+)\s*=\s*new\s+\w+\s*\[\s*(\d+)\s*\]'
        )
    else:  # cpp
        init_re = re.compile(
            r'\b\w+\s+(\w+)\s*\[\s*\]\s*=\s*\{([^}]*)\}'
        )
        new_re = re.compile(
            r'\b\w+\s+(\w+)\s*\[\s*(\d+)\s*\]'
        )

    for line in lines:
        m = init_re.search(line)
        if m:
            name = m.group(1)
            elems = [e.strip() for e in m.group(2).split(',') if e.strip()]
            array_sizes[name] = len(elems)
        m = new_re.search(line)
        if m:
            name = m.group(1)
            array_sizes[name] = int(m.group(2))

    if not array_sizes:
        return issues

    for lineno, line in enumerate(lines, 1):
        for name, size in array_sizes.items():
            for m in re.finditer(r'\b' + re.escape(name) + r'\s*\[\s*(\d+)\s*\]', line):
                idx = int(m.group(1))
                if idx >= size:
                    issues.append((
                        "Array index out of bounds",
                        lineno,
                        f"'{name}' has {size} element(s) (valid indices 0\u2013{size - 1}), "
                        f"but index {idx} is accessed. This will throw an "
                        f"{'ArrayIndexOutOfBoundsException' if language == 'java' else 'out-of-bounds error'} at runtime. "
                        f"Check the array size before accessing.",
                    ))

    return issues


def review_code(code, model, language="python", filename=None):
    language = resolve_review_language(language=language, filename=filename, code=code)
    result = {
        "confidence": 0,
        "syntax_error": False,
        "error_line": None,
        "error_msg": "",
        "issues": [],
        "complexity": 1,
    }
    seen_issues = set()

    def add_issue(name, line, fix):
        issue = (name, int(line or 0), fix)
        if issue not in seen_issues:
            seen_issues.add(issue)
            result["issues"].append(issue)

    tree = None
    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            result["syntax_error"] = True
            result["error_line"] = exc.lineno
            result["error_msg"] = str(exc)
            result["confidence"] = 95
            return result
    else:
        syntax_error = basic_c_like_syntax_error(code)
        if syntax_error:
            result["syntax_error"] = True
            result["error_line"] = syntax_error["line"]
            result["error_msg"] = syntax_error["message"]
            result["confidence"] = 92
            return result

    # Run compiler for C++/Java to catch semantic errors the regex pass misses
    if language in ("cpp", "java"):
        for name, line, fix in _compiler_issues(code, language):
            add_issue(name, line, fix)
        for name, line, fix in _check_array_oob(code, language):
            add_issue(name, line, fix)

    # Cached feature extraction
    _cache_key = (hash(code), language)
    if _cache_key in _FEATURE_CACHE:
        features = _FEATURE_CACHE[_cache_key]
    else:
        features = extract_features(code, language)
        if len(_FEATURE_CACHE) >= _FEATURE_CACHE_MAX:
            _FEATURE_CACHE.pop(next(iter(_FEATURE_CACHE)))
        _FEATURE_CACHE[_cache_key] = features
    loops = int(features[0][2])
    result["complexity"] = max(1, loops)

    if language == "python" and tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    add_issue(
                        "Possible Infinite Loop",
                        node.lineno,
                        "Add a break condition or update the loop predicate.",
                    )

            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    add_issue(
                        "Division by zero",
                        node.lineno,
                        "Check the denominator before dividing.",
                    )

            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "input":
                for parent in ast.walk(tree):
                    if isinstance(parent, (ast.For, ast.While)) and any(
                        child is node for child in ast.walk(parent)
                    ):
                        add_issue(
                            "Input inside loop",
                            node.lineno,
                            "Move input collection outside the loop when possible.",
                        )
                        break

            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "sort":
                for parent in ast.walk(tree):
                    if isinstance(parent, (ast.For, ast.While)) and any(
                        child is node for child in ast.walk(parent)
                    ):
                        add_issue(
                            "Sorting inside loop",
                            node.lineno,
                            "Sort once before the loop or use a better data structure.",
                        )
                        break

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, (ast.For, ast.While)) and child is not node:
                        add_issue(
                            "Nested loop (possible O(n^2))",
                            child.lineno,
                            "Reduce nested iteration or add indexing/cache-based lookups.",
                        )

            if isinstance(node, ast.FunctionDef):
                has_return = any(isinstance(child, ast.Return) for child in ast.walk(node))
                if not has_return:
                    add_issue(
                        "Function has no return",
                        node.lineno,
                        "Return a value explicitly or make the function's side effects clear.",
                    )

                calls_self = any(
                    isinstance(child, ast.Call) and getattr(child.func, "id", None) == node.name
                    for child in ast.walk(node)
                )
                has_guard = any(isinstance(child, ast.If) for child in ast.walk(node))
                if calls_self and not has_guard:
                    add_issue(
                        "Recursion without base case",
                        node.lineno,
                        "Add a terminating condition before making the recursive call.",
                    )

        # Detect accumulator variables overwritten instead of accumulated inside loops.
        # e.g. result = "" before loop, then result = char inside loop (missing result + char).
        _ACCUM_SEEDS = (0, 0.0, "", [], {})
        accumulator_vars = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            val = node.value
            is_seed = (
                (isinstance(val, ast.Constant) and val.value in _ACCUM_SEEDS)
                or (isinstance(val, ast.List) and not val.elts)
                or (isinstance(val, ast.Dict) and not val.keys)
                or (isinstance(val, ast.Set) and not val.elts)
            )
            if is_seed:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        accumulator_vars[target.id] = node.lineno

        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            loop_vars = set()
            if isinstance(node.target, ast.Name):
                loop_vars.add(node.target.id)
            elif isinstance(node.target, ast.Tuple):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        loop_vars.add(elt.id)
            for stmt in ast.walk(node):
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    lhs = target.id
                    if lhs not in accumulator_vars or lhs in loop_vars:
                        continue
                    rhs_names = {n.id for n in ast.walk(stmt.value) if isinstance(n, ast.Name)}
                    if lhs not in rhs_names and loop_vars & rhs_names:
                        add_issue(
                            "Loop variable overwrite",
                            stmt.lineno,
                            f"'{lhs}' is overwritten each iteration instead of accumulated. "
                            f"Did you mean '{lhs} += ...' or include '{lhs}' on the right-hand side?",
                        )

        # Detect calls to locally-defined functions with wrong number of arguments.
        func_defs = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = node.args
                n_args = len(args.args)
                n_defaults = len(args.defaults)
                n_required = n_args - n_defaults
                func_defs[node.name] = {
                    "n_args": n_args,
                    "n_required": n_required,
                    "has_varargs": args.vararg is not None,
                    "has_kwargs": args.kwarg is not None,
                    "lineno": node.lineno,
                }

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            fname = node.func.id
            if fname not in func_defs:
                continue
            fdef = func_defs[fname]
            if fdef["has_varargs"] or fdef["has_kwargs"]:
                continue
            n_passed = len(node.args) + len(node.keywords)
            if n_passed < fdef["n_required"]:
                add_issue(
                    "Wrong argument count",
                    node.lineno,
                    f"'{fname}' expects {fdef['n_required']} argument(s) but {n_passed} were given. "
                    f"See function definition at line {fdef['lineno']}.",
                )
            elif n_passed > fdef["n_args"]:
                add_issue(
                    "Wrong argument count",
                    node.lineno,
                    f"'{fname}' expects at most {fdef['n_args']} argument(s) but {n_passed} were given. "
                    f"See function definition at line {fdef['lineno']}.",
                )

        # Mutable default argument (classic Python gotcha in DSA memoization)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    add_issue(
                        "Mutable default argument",
                        node.lineno,
                        f"'{node.name}' uses a mutable default (list/dict/set). The same object is shared "
                        "across all calls — use None as default and initialize inside the function.",
                    )
                    break

        # Shadowing built-in names
        _BUILTINS = {
            "list", "dict", "set", "tuple", "str", "int", "float", "bool",
            "len", "range", "sum", "min", "max", "sorted", "reversed",
            "print", "input", "type", "map", "filter", "zip", "enumerate",
            "abs", "round", "any", "all", "next", "iter", "hash",
        }
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id in _BUILTINS:
                        add_issue(
                            "Shadowing built-in name",
                            node.lineno,
                            f"'{target.id}' shadows a Python built-in. Rename this variable to avoid subtle bugs.",
                        )
            elif isinstance(node, ast.FunctionDef) and node.name in _BUILTINS:
                add_issue(
                    "Shadowing built-in name",
                    node.lineno,
                    f"Function '{node.name}' shadows a Python built-in. Use a different name.",
                )

        # Comparing None with == (should use `is`)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comp, ast.Constant) and comp.value is None:
                    add_issue(
                        "None comparison with ==",
                        node.lineno,
                        "Use 'is None' / 'is not None' instead of '== None' / '!= None'.",
                    )

        # `is` / `is not` used with non-singleton literals
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(comp, ast.Constant):
                    if comp.value not in (None, True, False):
                        add_issue(
                            "Identity check on literal",
                            node.lineno,
                            f"'is {comp.value!r}' tests object identity, not value equality. Use '== {comp.value!r}'.",
                        )

        # Float equality comparison
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    if (isinstance(node.left, ast.Constant) and isinstance(node.left.value, float)) or \
                       (isinstance(comp, ast.Constant) and isinstance(comp.value, float)):
                        add_issue(
                            "Float equality comparison",
                            node.lineno,
                            "Comparing floats with == is unreliable due to floating-point precision. "
                            "Use abs(a - b) < epsilon instead.",
                        )

        # Nested loops with the same iteration variable (variable shadowing)
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            outer_vars = set()
            if isinstance(node.target, ast.Name):
                outer_vars.add(node.target.id)
            elif isinstance(node.target, ast.Tuple):
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        outer_vars.add(elt.id)
            for child in ast.walk(node):
                if child is node or not isinstance(child, ast.For):
                    continue
                inner_vars = set()
                if isinstance(child.target, ast.Name):
                    inner_vars.add(child.target.id)
                elif isinstance(child.target, ast.Tuple):
                    for elt in child.target.elts:
                        if isinstance(elt, ast.Name):
                            inner_vars.add(elt.id)
                for v in outer_vars & inner_vars:
                    add_issue(
                        "Nested loop variable shadowing",
                        child.lineno,
                        f"Inner loop reuses loop variable '{v}' from the outer loop — "
                        "this shadows the outer variable and will cause incorrect behavior.",
                    )

        # Unreachable code after return inside a function body
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for i, stmt in enumerate(node.body[:-1]):
                if isinstance(stmt, ast.Return):
                    add_issue(
                        "Unreachable code after return",
                        node.body[i + 1].lineno,
                        f"Statements after 'return' on line {stmt.lineno} will never execute.",
                    )
                    break

        # Missing return in one branch of if/else
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            has_valued_return = any(
                isinstance(c, ast.Return) and c.value is not None for c in ast.walk(node)
            )
            if not has_valued_return:
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.If) or not stmt.orelse:
                    continue
                if_returns = any(isinstance(s, ast.Return) for s in ast.walk(ast.Module(body=stmt.body, type_ignores=[])))
                else_returns = any(isinstance(s, ast.Return) for s in ast.walk(ast.Module(body=stmt.orelse, type_ignores=[])))
                if if_returns != else_returns:
                    add_issue(
                        "Missing return in branch",
                        stmt.lineno,
                        "One branch of this if/else returns a value but the other doesn't — "
                        "the function may silently return None.",
                    )

        # Modifying a collection while iterating over it
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            iter_names = set()
            if isinstance(node.iter, ast.Name):
                iter_names.add(node.iter.id)
            _MUTATING_METHODS = {"append", "remove", "pop", "insert", "extend", "clear", "discard"}
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                if not isinstance(child.func, ast.Attribute):
                    continue
                if not isinstance(child.func.value, ast.Name):
                    continue
                obj = child.func.value.id
                method = child.func.attr
                if obj in iter_names and method in _MUTATING_METHODS:
                    add_issue(
                        "Modifying collection while iterating",
                        child.lineno,
                        f"Calling '.{method}()' on '{obj}' while iterating over it can skip elements "
                        f"or cause errors. Iterate over a copy: 'for x in {obj}[:]:'.",
                    )

        # Bare except clause (catches everything including KeyboardInterrupt)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if handler.type is None:
                    add_issue(
                        "Bare except clause",
                        handler.lineno,
                        "A bare 'except:' catches all exceptions including SystemExit and KeyboardInterrupt. "
                        "Catch specific exceptions or use 'except Exception:'.",
                    )

        # Return inside finally block (masks the original exception)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            if not node.finalbody:
                continue
            for stmt in ast.walk(ast.Module(body=node.finalbody, type_ignores=[])):
                if isinstance(stmt, ast.Return):
                    add_issue(
                        "Return inside finally",
                        stmt.lineno,
                        "'return' inside a 'finally' block suppresses any exception being propagated. "
                        "Move the return outside the try/finally.",
                    )
                    break

        # Boolean compared with == True / == False (use `if x:` directly)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for op, comp in zip(node.ops, node.comparators):
                if (isinstance(op, (ast.Eq, ast.NotEq))
                        and isinstance(comp, ast.Constant)
                        and isinstance(comp.value, bool)):
                    suggestion = "if x:" if comp.value else "if not x:"
                    add_issue(
                        "Boolean compared with == True/False",
                        node.lineno,
                        f"Use '{suggestion}' directly instead of '== {comp.value}' — "
                        "it is cleaner and avoids subtle type-coercion bugs.",
                    )

        # Missing `self` as first parameter in __init__ / instance methods
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name in ("__init__", "__new__", "__str__", "__repr__",
                              "__len__", "__eq__", "__lt__", "__hash__"):
                if not node.args.args or node.args.args[0].arg != "self":
                    add_issue(
                        "Missing self in method",
                        node.lineno,
                        f"'{node.name}' should have 'self' as its first parameter. "
                        "Without it, calling the method will raise TypeError.",
                    )

        # Global variable modified inside a function without `global` declaration
        _module_names: set = set()
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        _module_names.add(t.id)
            elif isinstance(stmt, (ast.FunctionDef, ast.ClassDef)):
                _module_names.add(stmt.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            _declared_global: set = set()
            for stmt in node.body:
                if isinstance(stmt, ast.Global):
                    _declared_global.update(stmt.names)
            for child in ast.walk(node):
                if not isinstance(child, ast.Assign):
                    continue
                for target in child.targets:
                    if (isinstance(target, ast.Name)
                            and target.id in _module_names
                            and target.id not in _declared_global
                            and target.id != node.name):
                        add_issue(
                            "Missing global declaration",
                            child.lineno,
                            f"'{target.id}' is a module-level variable. "
                            f"Add 'global {target.id}' at the top of '{node.name}' to modify it; "
                            "otherwise a new local variable is created instead.",
                        )
                        _declared_global.add(target.id)  # report once per var per function

        # ── DEEPER ANALYSIS (Python) ──────────────────────────────────────────

        # Dead code after break/continue inside loops
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            for i, stmt in enumerate(node.body[:-1]):
                if isinstance(stmt, (ast.Break, ast.Continue)):
                    keyword = "break" if isinstance(stmt, ast.Break) else "continue"
                    add_issue(
                        "Unreachable code after break/continue",
                        node.body[i + 1].lineno,
                        f"Statements after '{keyword}' on line {stmt.lineno} will never execute. "
                        "Remove the dead code or restructure the loop.",
                    )
                    break

        # Unused variable detection (shallow: assigned but never read)
        _assigned: dict = {}
        _used: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        _assigned.setdefault(target.id, node.lineno)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                t = node.target
                if isinstance(t, ast.Name) and not t.id.startswith("_"):
                    _assigned.setdefault(t.id, t.lineno)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                _used.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    _used.add(arg.arg)
        for _var, _lineno in _assigned.items():
            if _var not in _used:
                add_issue(
                    "Unused variable",
                    _lineno,
                    f"'{_var}' is assigned but never used. Remove it or use it. "
                    "Prefix with '_' if intentionally unused.",
                )

        # None propagation: variable assigned None then attribute/method accessed
        _none_vars: dict = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Constant) and node.value.value is None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            _none_vars[target.id] = node.lineno
                elif isinstance(node.value, ast.Name):
                    # Re-assignment to non-None removes it from tracking
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in _none_vars:
                            del _none_vars[target.id]
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in _none_vars):
                add_issue(
                    "Possible None dereference",
                    node.lineno,
                    f"'{node.value.id}' was assigned None but '.{node.attr}' is accessed on it "
                    "without a None check. Add: if {node.value.id} is not None: ...",
                )

    else:
        clean_code = strip_c_like_comments(code)
        lines = clean_code.splitlines()
        recent_loop_lines = []

        for lineno, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            recent_loop_lines = [loop_line for loop_line in recent_loop_lines if lineno - loop_line <= 6]
            has_loop = bool(LOOP_PATTERN.search(line))

            if has_loop and recent_loop_lines:
                add_issue(
                    "Nested loop (possible O(n^2))",
                    lineno,
                    "Consider flattening the loops or using a faster lookup structure.",
                )

            if INFINITE_LOOP_PATTERN.search(line):
                add_issue(
                    "Possible Infinite Loop",
                    lineno,
                    "Add a termination condition or break path inside the loop.",
                )

            if DIVISION_BY_ZERO_PATTERN.search(line):
                add_issue(
                    "Division by zero",
                    lineno,
                    "Guard the denominator before dividing.",
                )

            if has_loop:
                recent_loop_lines.append(lineno)

            input_pattern = INPUT_PATTERNS.get(language)
            if input_pattern and input_pattern.search(line) and recent_loop_lines:
                add_issue(
                    "Input inside loop",
                    lineno,
                    "Read input before the loop or buffer it to reduce repeated I/O.",
                )

            sort_pattern = SORT_PATTERNS.get(language)
            if sort_pattern and sort_pattern.search(line) and recent_loop_lines:
                add_issue(
                    "Sorting inside loop",
                    lineno,
                    "Move sorting outside the loop or keep the data structure ordered.",
                )

            if MISSING_SEMICOLON_PATTERN.match(line):
                add_issue(
                    "Possible missing semicolon",
                    lineno,
                    "Terminate the return statement with a semicolon.",
                )

            if language in ("cpp", "java") and CPP_STMT_MISSING_SEMICOLON_PATTERN.match(line):
                add_issue(
                    "Possible missing semicolon",
                    lineno,
                    "Add a semicolon at the end of the statement.",
                )

            if language in ("cpp", "java"):
                normalized = _normalize_strings_in_line(line)
                if (
                    CPP_LITERAL_MISSING_SEMICOLON_PATTERN.search(normalized)
                    and not normalized.strip().startswith("#")
                ):
                    add_issue(
                        "Possible missing semicolon",
                        lineno,
                        "Add a semicolon at the end of the statement.",
                    )

            # Assignment inside if condition: if (x = 5) — likely meant ==
            if language in ("cpp", "java") and CPP_ASSIGN_IN_COND_PATTERN.search(line):
                add_issue(
                    "Assignment in condition",
                    lineno,
                    "Found '=' inside an if condition — did you mean '==' for comparison?",
                )

            # endl inside a loop flushes buffer every iteration — causes TLE
            if language == "cpp" and CPP_ENDL_PATTERN.search(line) and recent_loop_lines:
                add_issue(
                    "endl inside loop (slow flush)",
                    lineno,
                    "std::endl flushes the output buffer on every call. Use '\"\\n\"' inside loops to avoid TLE.",
                )

            # pow() result stored directly in int — truncation and precision bugs
            if language == "cpp" and CPP_POW_TO_INT_PATTERN.search(line):
                add_issue(
                    "pow() result stored in integer",
                    lineno,
                    "pow() returns a double. Storing it in int/long can cause wrong answers due to floating-point truncation. "
                    "Use a custom integer power function instead.",
                )

            # Unsafe C functions
            if language == "cpp" and CPP_RISKY_API_PATTERN.search(line):
                add_issue(
                    "Unsafe C function",
                    lineno,
                    "gets() and strcpy() are unsafe — they do not check buffer bounds. "
                    "Use fgets() and strncpy() / std::string instead.",
                )

            # Java: String compared with == instead of .equals()
            if language == "java" and JAVA_STRING_EQ_PATTERN.search(_normalize_strings_in_line(line)):
                add_issue(
                    "String compared with ==",
                    lineno,
                    "In Java, == checks object identity, not string content. Use .equals() or .equalsIgnoreCase() to compare strings.",
                )

            # Java: String concatenation in loop (O(n^2) allocation — use StringBuilder)
            if language == "java" and recent_loop_lines and re.search(r'\bString\b', clean_code):
                if re.search(r'\b\w+\s*\+=\s*(?:"[^"]*"|\w)', line) or re.search(r'\b\w+\s*=\s*\w+\s*\+\s*(?:"|\w)', line):
                    add_issue(
                        "String concatenation in loop",
                        lineno,
                        "String concatenation with '+=' inside a loop creates a new object each iteration (O(n²)). "
                        "Use StringBuilder.append() and call .toString() at the end.",
                    )

            # Java: catching broad Exception hides real errors
            if language == "java" and JAVA_BROAD_CATCH_PATTERN.search(line):
                add_issue(
                    "Catching broad Exception",
                    lineno,
                    "Catching Exception is too broad and may hide bugs. Catch specific exceptions like IOException, ArithmeticException, etc.",
                )

            # Integer overflow risk — int used where long is needed
            if language == "cpp" and CPP_INT_OVERFLOW_PATTERN.search(line):
                add_issue(
                    "Integer overflow risk",
                    lineno,
                    "This value may overflow a 32-bit int. Use 'long long' for values that can exceed ~2.1 billion.",
                )
            if language == "java" and JAVA_INT_OVERFLOW_PATTERN.search(line):
                add_issue(
                    "Integer overflow risk",
                    lineno,
                    "Multiplying two ints may overflow before being stored. Cast to long first: (long) a * b.",
                )

        # Switch-case missing break (scan after line loop)
        if language in ("cpp", "java"):
            in_switch_depth = 0
            brace_d = 0
            last_case_line = None
            case_has_break = True
            for lineno, raw_line in enumerate(lines, start=1):
                line = raw_line.strip()
                brace_d += line.count("{") - line.count("}")
                if SWITCH_OPEN_PATTERN.search(line):
                    in_switch_depth = brace_d  # depth after the switch's opening brace
                if in_switch_depth and brace_d < in_switch_depth:
                    # closed the switch block
                    if last_case_line and not case_has_break:
                        add_issue(
                            "Missing break in switch case",
                            last_case_line,
                            "This case falls through to the next case. Add 'break;' to prevent unintended fall-through.",
                        )
                    in_switch_depth = 0
                    last_case_line = None
                    case_has_break = True
                if in_switch_depth and SWITCH_CASE_PATTERN.search(line):
                    if last_case_line and not case_has_break:
                        add_issue(
                            "Missing break in switch case",
                            last_case_line,
                            "This case falls through to the next case. Add 'break;' to prevent unintended fall-through.",
                        )
                    last_case_line = lineno
                    case_has_break = False
                if in_switch_depth and SWITCH_BREAK_PATTERN.search(line):
                    case_has_break = True

        # Mixed printf/cout without sync disabled (C++)
        if language == "cpp":
            has_printf = CPP_PRINTF_PATTERN.search(clean_code)
            has_cout = CPP_COUT_PATTERN.search(clean_code)
            sync_off = re.search(r"sync_with_stdio\s*\(\s*false\s*\)", clean_code)
            if has_printf and has_cout and not sync_off:
                add_issue(
                    "Mixed printf and cout",
                    0,
                    "Mixing printf/scanf with cout/cin without 'ios::sync_with_stdio(false)' can cause garbled output. "
                    "Use one I/O style consistently.",
                )

        # C++: int overflow from large literal assignment
        if language == "cpp" and re.search(r"\bint\b[^;\n]*=\s*[^;\n]*\b(?:1000000000|1e9|2e9|1e10)\b", clean_code):
            add_issue(
                "Integer overflow risk",
                0,
                "Assigning 1e9 or larger to 'int' may overflow (max ~2.1B). Use 'long long' for large values.",
            )

        # C++: empty catch block
        if language == "cpp" and re.search(r"\bcatch\s*\([^)]*\)\s*\{\s*\}", clean_code):
            add_issue(
                "Empty catch block",
                0,
                "Swallowing exceptions silently makes debugging impossible. Log the error or re-throw.",
            )

        # Java: empty catch block
        if language == "java" and re.search(r"\bcatch\s*\([^)]*\)\s*\{\s*\}", clean_code):
            add_issue(
                "Empty catch block",
                0,
                "Swallowing exceptions silently makes debugging impossible. Log the error or re-throw.",
            )

        # Java: using == null check is fine but missing null check before dereference (basic heuristic)
        if language == "java" and re.search(r"\.length\(\)|\.size\(\)|\.get\(", clean_code):
            if not re.search(r"(?:==|!=)\s*null|null\s*(?:==|!=)", clean_code) and re.search(r"\bnull\b", clean_code):
                add_issue(
                    "Possible NullPointerException",
                    0,
                    "Objects are used without a null check. Verify that references are non-null before calling methods on them.",
                )

        allocation_pattern = MEMORY_ALLOC_PATTERNS.get(language)
        release_pattern = MEMORY_RELEASE_PATTERNS.get(language)
        if allocation_pattern and allocation_pattern.search(clean_code):
            if not release_pattern or not release_pattern.search(clean_code):
                add_issue(
                    "Possible memory leak",
                    0,
                    "Release allocated memory with the matching cleanup call on every path.",
                )

        if language == "java" and JAVA_RESOURCE_PATTERN.search(clean_code) and not JAVA_CLOSE_PATTERN.search(clean_code):
            add_issue(
                "Resource may not be closed",
                0,
                "Close scanners/readers in a finally block or use try-with-resources.",
            )

        analyze_c_like_functions(lines, add_issue)

    if loops >= 3:
        add_issue(
            "High Time Complexity (TLE risk)",
            0,
            "Reduce loop nesting or use a more efficient algorithm/data structure.",
        )

    result["confidence"] = estimate_confidence(features, len(result["issues"]), language, model)

    # Skip ML inference when rule confidence already very high (speed optimisation)
    # (confidence was already computed above; this is just a fast-path guard for
    #  any downstream callers that check the flag)
    if result["confidence"] >= 95 and len(result["issues"]) >= 5:
        result["confidence"] = min(99.0, result["confidence"])

    # Rank issues: most critical first
    if result["issues"]:
        if _rank_issues is not None:
            result["issues"] = _rank_issues(result["issues"])
        else:
            # Fallback inline sort by simple severity mapping
            _SEV = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            _CRITICAL_NAMES = {"Possible Infinite Loop", "Division by zero",
                                "Recursion without base case", "Compiler Error",
                                "Unsafe C function", "Possible missing semicolon",
                                "Array index out of bounds"}
            _HIGH_NAMES = {"Wrong argument count", "Nested loop (possible O(n^2))",
                           "High Time Complexity (TLE risk)", "Modifying collection while iterating",
                           "Return inside finally", "Assignment in condition",
                           "String compared with ==", "Integer overflow risk",
                           "Missing break in switch case", "Possible NullPointerException",
                           "Possible memory leak", "Possible None dereference"}

            def _fallback_rank(issue):
                name = issue[0]
                if name in _CRITICAL_NAMES:
                    return (0, issue[1] or 0)
                if name in _HIGH_NAMES:
                    return (1, issue[1] or 0)
                return (2, issue[1] or 0)

            result["issues"] = sorted(result["issues"], key=_fallback_rank)

    return result


def analyze_c_like_functions(lines, add_issue):
    brace_depth = 0
    pending_function = None
    active_functions = []

    def close_completed_functions(current_depth):
        while active_functions and current_depth < active_functions[-1]["body_depth"]:
            function = active_functions.pop()
            finalize_function(function, add_issue)

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        leading_closes = len(line) - len(line.lstrip("}"))
        current_depth = max(0, brace_depth - leading_closes)
        close_completed_functions(current_depth)

        for function in active_functions:
            if re.search(r"\breturn\b", line):
                function["has_return"] = True
            if re.search(r"\b(?:if|switch)\b", line):
                function["has_guard"] = True
            if re.search(rf"\b{re.escape(function['name'])}\s*\(", line):
                function["calls_self"] = True

        if pending_function and "{" in line:
            pending_function["body_depth"] = current_depth + 1
            active_functions.append(pending_function)
            pending_function = None

        match = FUNCTION_SIGNATURE_PATTERN.match(line)
        if match and match.group("return_type") != "void":
            function = {
                "name": match.group("name"),
                "line": lineno,
                "has_return": False,
                "calls_self": False,
                "has_guard": False,
                "body_depth": current_depth + 1,
            }
            if match.group("brace"):
                active_functions.append(function)
            else:
                pending_function = function

        brace_depth += line.count("{") - line.count("}")
        close_completed_functions(brace_depth)

    while active_functions:
        finalize_function(active_functions.pop(), add_issue)


def finalize_function(function, add_issue):
    if not function["has_return"]:
        add_issue(
            "Function may exit without returning a value",
            function["line"],
            "Return a value on every control path for non-void functions.",
        )

    if function["calls_self"] and not function["has_guard"]:
        add_issue(
            "Recursion without base case",
            function["line"],
            "Add a guard condition before the recursive call.",
        )
