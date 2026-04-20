"""
Deterministic template-driven explanations for known issue types.
No LLM usage — all output is static and fully predictable.
"""

SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

TEMPLATES = {
    # ── CRITICAL ──────────────────────────────────────────────────────────────
    "Possible Infinite Loop": {
        "explanation": "A loop with no termination condition will run forever, hanging the program.",
        "fix": "Add a break condition inside the loop body, or make the loop predicate eventually False.",
        "severity_hint": "CRITICAL",
    },
    "Division by zero": {
        "explanation": "Dividing by zero causes ZeroDivisionError (Python) or undefined behavior (C++) at runtime.",
        "fix": "Guard the denominator: if divisor != 0: ... or use a conditional expression.",
        "severity_hint": "CRITICAL",
    },
    "Recursion without base case": {
        "explanation": "A recursive function without a base case will recurse infinitely until the stack overflows.",
        "fix": "Add a terminating condition at the start of the function before the recursive call.",
        "severity_hint": "CRITICAL",
    },
    "Compiler Error": {
        "explanation": "The code contains a syntax or semantic error that prevents compilation.",
        "fix": "Fix the reported compiler error before running the program.",
        "severity_hint": "CRITICAL",
    },
    "Unsafe C function": {
        "explanation": "gets() and strcpy() do not check buffer bounds, making them vulnerable to buffer overflow.",
        "fix": "Replace gets() with fgets() and strcpy() with strncpy() or std::string.",
        "severity_hint": "CRITICAL",
    },
    "Possible missing semicolon": {
        "explanation": "A statement appears to be missing its terminating semicolon, causing a compile error.",
        "fix": "Add a semicolon at the end of the statement.",
        "severity_hint": "CRITICAL",
    },
    "Array index out of bounds": {
        "explanation": "An array is accessed at a literal index that exceeds its declared size, causing a runtime crash (ArrayIndexOutOfBoundsException in Java, undefined behaviour in C++).",
        "fix": "Use a valid index within the array bounds (0 to length-1), or check the index before accessing.",
        "severity_hint": "CRITICAL",
    },

    # ── HIGH ──────────────────────────────────────────────────────────────────
    "Wrong argument count": {
        "explanation": "Calling a function with the wrong number of arguments causes a TypeError at runtime.",
        "fix": "Match the argument count to the function definition, or add default parameters.",
        "severity_hint": "HIGH",
    },
    "Nested loop (possible O(n^2))": {
        "explanation": "Nested loops over the same data are often O(n²), causing TLE on large inputs.",
        "fix": "Use a hash map for O(1) lookups, sorting + two pointers, or prefix sums to remove nesting.",
        "severity_hint": "HIGH",
    },
    "High Time Complexity (TLE risk)": {
        "explanation": "Three or more nested loops create O(n³) or worse complexity — will TLE on large inputs.",
        "fix": "Reduce loop nesting using efficient data structures (segment trees, Fenwick trees) or math.",
        "severity_hint": "HIGH",
    },
    "Modifying collection while iterating": {
        "explanation": "Mutating a list or dict while iterating can skip elements, raise RuntimeError, or give wrong results.",
        "fix": "Iterate over a copy: 'for x in lst[:]:', or collect changes and apply after the loop.",
        "severity_hint": "HIGH",
    },
    "Return inside finally": {
        "explanation": "A return in a finally block silently discards any propagating exception, masking real errors.",
        "fix": "Move the return outside the try/finally block and use finally only for cleanup.",
        "severity_hint": "HIGH",
    },
    "Assignment in condition": {
        "explanation": "Using '=' instead of '==' in a condition assigns a value rather than comparing — likely wrong.",
        "fix": "Replace '=' with '==' for comparison. Wrap in extra parentheses if the assignment is intentional.",
        "severity_hint": "HIGH",
    },
    "String compared with ==": {
        "explanation": "In Java, '==' checks object identity (memory address), not string content equality.",
        "fix": "Use .equals() for value comparison: if (s1.equals(s2)). Use .equalsIgnoreCase() for case-insensitive.",
        "severity_hint": "HIGH",
    },
    "Integer overflow risk": {
        "explanation": "A 32-bit int overflows at ~2.1 billion. Arithmetic on large values silently wraps to a wrong result.",
        "fix": "Use 'long long' in C++ or cast to long in Java before multiplication: (long) a * b.",
        "severity_hint": "HIGH",
    },
    "Missing break in switch case": {
        "explanation": "Without a break, a switch case falls through to the next case, executing unintended code.",
        "fix": "Add 'break;' at the end of each case block, or use 'return'/'throw' to exit.",
        "severity_hint": "HIGH",
    },
    "Possible NullPointerException": {
        "explanation": "Calling a method on a null reference throws NullPointerException at runtime.",
        "fix": "Add a null check before accessing the object: if (obj != null) { ... }",
        "severity_hint": "HIGH",
    },
    "Possible memory leak": {
        "explanation": "Memory allocated with new/malloc is not freed, causing the process to grow in memory over time.",
        "fix": "Free every allocation on all code paths, or use smart pointers (unique_ptr, shared_ptr).",
        "severity_hint": "HIGH",
    },
    "Possible None dereference": {
        "explanation": "A variable known to be None is used without a None check, raising AttributeError at runtime.",
        "fix": "Check before calling methods: if var is not None: var.method()",
        "severity_hint": "HIGH",
    },

    # ── MEDIUM ────────────────────────────────────────────────────────────────
    "Input inside loop": {
        "explanation": "Reading user input inside a loop blocks every iteration, increasing latency and risking TLE.",
        "fix": "Read all input before the loop or use buffered input (sys.stdin.read()) for competitive programming.",
        "severity_hint": "MEDIUM",
    },
    "Sorting inside loop": {
        "explanation": "Sorting is O(n log n) per call. Inside a loop it becomes O(n² log n) overall.",
        "fix": "Sort once before the loop, or maintain a sorted data structure (heapq, SortedList).",
        "severity_hint": "MEDIUM",
    },
    "Loop variable overwrite": {
        "explanation": "The accumulator is overwritten every iteration instead of accumulated, keeping only the last value.",
        "fix": "Use '+=' for numbers/strings or '.append()' for lists instead of plain '=' assignment.",
        "severity_hint": "MEDIUM",
    },
    "Mutable default argument": {
        "explanation": "Python creates the default value once. A mutable default (list/dict/set) is shared across all calls.",
        "fix": "Use None as default and initialize inside: def f(x=None): if x is None: x = []",
        "severity_hint": "MEDIUM",
    },
    "Float equality comparison": {
        "explanation": "Floating-point numbers have limited precision. Direct '==' comparison is almost always unreliable.",
        "fix": "Use abs(a - b) < 1e-9 for equality, or math.isclose(a, b).",
        "severity_hint": "MEDIUM",
    },
    "Nested loop variable shadowing": {
        "explanation": "The inner loop reuses the outer loop's variable name, overwriting it and corrupting outer iteration.",
        "fix": "Use distinct variable names for each loop level (i, j, k or descriptive names).",
        "severity_hint": "MEDIUM",
    },
    "Missing return in branch": {
        "explanation": "One branch of an if/else returns a value while the other does not, silently returning None.",
        "fix": "Ensure every branch either returns a value or explicitly returns None.",
        "severity_hint": "MEDIUM",
    },
    "Bare except clause": {
        "explanation": "A bare 'except:' catches all exceptions including SystemExit and KeyboardInterrupt, masking errors.",
        "fix": "Catch specific exceptions or use 'except Exception:'. Log the exception for debugging.",
        "severity_hint": "MEDIUM",
    },
    "Compiler Warning": {
        "explanation": "The compiler detected a potential issue that may cause unexpected behavior at runtime.",
        "fix": "Address the compiler warning — warnings often point to real bugs.",
        "severity_hint": "MEDIUM",
    },
    "endl inside loop (slow flush)": {
        "explanation": "std::endl flushes the output buffer on every call, which is significantly slower than '\\n'.",
        "fix": "Replace std::endl with '\"\\n\"' inside loops. Flush only when necessary.",
        "severity_hint": "MEDIUM",
    },
    "pow() result stored in integer": {
        "explanation": "pow() returns a double. Storing in int/long truncates the value and causes wrong answers for large exponents.",
        "fix": "Use a custom integer power function: long long ipow(long long base, int exp) { ... }",
        "severity_hint": "MEDIUM",
    },
    "String concatenation in loop": {
        "explanation": "String '+=' in Java creates a new String object each iteration — O(n²) in memory allocation.",
        "fix": "Use StringBuilder.append() in the loop and call .toString() once at the end.",
        "severity_hint": "MEDIUM",
    },
    "Catching broad Exception": {
        "explanation": "Catching the generic Exception class hides bugs and makes error handling imprecise.",
        "fix": "Catch specific exception types like IOException, ArithmeticException, or NumberFormatException.",
        "severity_hint": "MEDIUM",
    },
    "Mixed printf and cout": {
        "explanation": "Mixing printf/scanf with cout/cin without disabling sync can produce garbled output.",
        "fix": "Use one I/O style consistently, or add 'ios::sync_with_stdio(false)' at the start of main().",
        "severity_hint": "MEDIUM",
    },
    "Empty catch block": {
        "explanation": "Silently swallowing exceptions makes debugging impossible — errors fail with no visible cause.",
        "fix": "Log the exception at minimum. Re-throw if the calling code should handle it.",
        "severity_hint": "MEDIUM",
    },
    "Resource may not be closed": {
        "explanation": "Unclosed file handles and streams leak OS resources and can prevent other processes from accessing the file.",
        "fix": "Close resources in a finally block or use try-with-resources: try (Scanner sc = ...) { }",
        "severity_hint": "MEDIUM",
    },
    "Function may exit without returning a value": {
        "explanation": "A non-void function that exits without a return causes undefined behavior in C++ or returns garbage.",
        "fix": "Add an explicit return statement covering all code paths.",
        "severity_hint": "MEDIUM",
    },

    # ── LOW ───────────────────────────────────────────────────────────────────
    "Shadowing built-in name": {
        "explanation": "Reusing Python built-in names (list, dict, len) breaks those built-ins in the current scope.",
        "fix": "Rename the variable to something descriptive that doesn't conflict with Python built-ins.",
        "severity_hint": "LOW",
    },
    "None comparison with ==": {
        "explanation": "Using '== None' works but can fail with custom __eq__ and is considered bad Python style.",
        "fix": "Use 'is None' or 'is not None' for identity comparison with None.",
        "severity_hint": "LOW",
    },
    "Identity check on literal": {
        "explanation": "'is' checks object identity (memory address), not value — 'is 42' is unreliable.",
        "fix": "Use '==' for value equality. Reserve 'is' for None, True, and False.",
        "severity_hint": "LOW",
    },
    "Unreachable code after return": {
        "explanation": "Code placed after a return statement inside a function will never execute.",
        "fix": "Remove the dead code or restructure the logic so the return is at the end.",
        "severity_hint": "LOW",
    },
    "Unreachable code after break/continue": {
        "explanation": "Statements after break or continue inside a loop body will never execute.",
        "fix": "Remove the unreachable statements or restructure the loop logic.",
        "severity_hint": "LOW",
    },
    "Function has no return": {
        "explanation": "A function with no return implicitly returns None. If a value is expected, this is a bug.",
        "fix": "Add an explicit return statement, or verify the function is intentionally side-effect-only.",
        "severity_hint": "LOW",
    },
    "Unused variable": {
        "explanation": "A variable is assigned but never read — wastes memory and may indicate a logic error or typo.",
        "fix": "Remove the assignment or use the variable where intended. Prefix with '_' if intentionally unused.",
        "severity_hint": "LOW",
    },
    "Boolean compared with == True/False": {
        "explanation": "Comparing a boolean with '== True' or '== False' is redundant and can produce unexpected results with truthy/falsy values.",
        "fix": "Use 'if x:' instead of 'if x == True:' and 'if not x:' instead of 'if x == False:'.",
        "severity_hint": "LOW",
    },
    "Missing self in method": {
        "explanation": "Instance methods must have 'self' as their first parameter. Without it, Python passes the instance as the first argument causing a TypeError.",
        "fix": "Add 'self' as the first parameter: def __init__(self, ...):",
        "severity_hint": "HIGH",
    },
    "Missing global declaration": {
        "explanation": "Assigning to a module-level variable inside a function without 'global' creates a new local variable instead of modifying the global one.",
        "fix": "Add 'global variable_name' at the top of the function before the assignment.",
        "severity_hint": "MEDIUM",
    },
}

_DEFAULT_TEMPLATE = {
    "explanation": "A potential issue was detected in the code.",
    "fix": "Review the flagged line and apply the suggested correction.",
    "severity_hint": "MEDIUM",
}


def get_template(issue_name: str) -> dict:
    """Return the template for a given issue name, with fuzzy fallback."""
    if issue_name in TEMPLATES:
        return TEMPLATES[issue_name]
    lower = issue_name.lower()
    for key, tmpl in TEMPLATES.items():
        if lower.startswith(key.lower()[:20]):
            return tmpl
    return _DEFAULT_TEMPLATE


def generate_explanation(issue_type: str) -> dict:
    """Return {explanation, fix, severity_hint} for the given issue type."""
    return get_template(issue_type)
