"""
Enhanced feature extraction for the ML analysis pipeline.

extract_features(code, language) → dict of numeric features:
  lines_of_code, num_functions, nesting_depth, cyclomatic_complexity,
  num_loops, num_conditions, function_length_avg, recursion_detected,
  unused_variables_count

Python uses AST for precise analysis; C++/Java use regex.
tree-sitter is not required.
"""

import ast
import re
from typing import Dict, List

# ── C++/Java regex patterns ───────────────────────────────────────────────────

_LOOP_RE = re.compile(r"\b(?:for|while)\s*\(")
_IF_RE = re.compile(r"\bif\s*\(")
_FUNC_DECL_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|virtual|inline|"
    r"constexpr|synchronized|native|abstract)\s+)*"
    r"(?:[\w:<>\[\],*&]+)\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{?\s*$",
    re.MULTILINE,
)
_BRANCH_RE = re.compile(r"\b(?:if|else\s+if|for|while|case|catch)\b|&&|\|\|")


# ── Python AST helpers ────────────────────────────────────────────────────────

def _cyclomatic_py(tree: ast.AST) -> int:
    count = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                              ast.With, ast.Assert)):
            count += 1
        elif isinstance(node, ast.BoolOp):
            count += len(node.values) - 1
    return count


def _nesting_depth_py(tree: ast.AST) -> int:
    _NESTING = (ast.If, ast.For, ast.While, ast.With, ast.Try)

    def _depth(node: ast.AST, d: int) -> int:
        if isinstance(node, _NESTING):
            d += 1
        child_depths = [_depth(c, d) for c in ast.iter_child_nodes(node)]
        return max(child_depths) if child_depths else d

    return _depth(tree, 0)


def _function_lengths_py(tree: ast.AST) -> List[int]:
    lengths = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body:
                last = node.body[-1]
                end = getattr(last, "end_lineno", node.lineno)
                lengths.append(max(1, end - node.lineno + 1))
    return lengths


def _unused_variables_py(tree: ast.AST) -> int:
    assigned: Dict[str, int] = {}
    used: set = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    assigned.setdefault(target.id, node.lineno)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            t = node.target
            if isinstance(t, ast.Name) and not t.id.startswith("_"):
                assigned.setdefault(t.id, t.lineno)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.FunctionDef):
            for arg in (node.args.args + node.args.posonlyargs +
                        node.args.kwonlyargs):
                used.add(arg.arg)

    return sum(1 for v in assigned if v not in used)


def _recursion_py(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        fname = node.name
        for child in ast.walk(node):
            if (child is not node
                    and isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == fname):
                return True
    return False


# ── C++/Java helpers ──────────────────────────────────────────────────────────

def _nesting_depth_clike(code: str) -> int:
    max_d = depth = 0
    for ch in code:
        if ch == "{":
            depth += 1
            max_d = max(max_d, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    return max_d


def _function_lengths_clike(code: str) -> List[int]:
    lengths = []
    lines = code.splitlines()
    i = 0
    while i < len(lines):
        if _FUNC_DECL_RE.match(lines[i]):
            start = i
            depth = found_open = 0
            j = i
            while j < len(lines):
                opens = lines[j].count("{")
                closes = lines[j].count("}")
                depth += opens - closes
                if opens:
                    found_open = 1
                if found_open and depth <= 0:
                    lengths.append(j - start + 1)
                    i = j
                    break
                j += 1
        i += 1
    return lengths


def _cyclomatic_clike(code: str) -> int:
    return len(_BRANCH_RE.findall(code)) + 1


def _recursion_clike(code: str) -> bool:
    func_names = [m.group(1) for m in _FUNC_DECL_RE.finditer(code)]
    for fname in func_names:
        if len(re.findall(rf"\b{re.escape(fname)}\s*\(", code)) > 1:
            return True
    return False


def _strip_comments_clike(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"//.*", "", code)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_features(code: str, language: str = "python") -> dict:
    """
    Extract rich numeric features from source code.

    Returns:
        dict with keys: lines_of_code, num_functions, nesting_depth,
        cyclomatic_complexity, num_loops, num_conditions,
        function_length_avg, recursion_detected, unused_variables_count
    """
    lang = (language or "python").strip().lower()
    loc = max(1, sum(1 for l in code.splitlines() if l.strip()))

    if lang == "python":
        try:
            tree = ast.parse(code)
            num_funcs = sum(
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                for n in ast.walk(tree)
            )
            num_loops = sum(
                isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)
            )
            num_conds = sum(isinstance(n, ast.If) for n in ast.walk(tree))
            cc = _cyclomatic_py(tree)
            nd = _nesting_depth_py(tree)
            fl = _function_lengths_py(tree)
            fl_avg = sum(fl) / len(fl) if fl else 0.0
            recur = int(_recursion_py(tree))
            unused = _unused_variables_py(tree)
        except SyntaxError:
            num_funcs = num_loops = num_conds = cc = nd = unused = recur = 0
            fl_avg = 0.0
    else:
        clean = _strip_comments_clike(code)
        num_funcs = len(_FUNC_DECL_RE.findall(clean))
        num_loops = len(_LOOP_RE.findall(clean))
        num_conds = len(_IF_RE.findall(clean))
        cc = _cyclomatic_clike(clean)
        nd = _nesting_depth_clike(clean)
        fl = _function_lengths_clike(clean)
        fl_avg = sum(fl) / len(fl) if fl else 0.0
        recur = int(_recursion_clike(clean))
        unused = 0  # requires full type info for C++/Java

    return {
        "lines_of_code": loc,
        "num_functions": num_funcs,
        "nesting_depth": nd,
        "cyclomatic_complexity": cc,
        "num_loops": num_loops,
        "num_conditions": num_conds,
        "function_length_avg": round(fl_avg, 1),
        "recursion_detected": recur,
        "unused_variables_count": unused,
    }
