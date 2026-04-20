import csv
import glob
import json
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


SOURCE_EXTENSION_TO_LANGUAGE = {
    ".c": "cpp",
    ".h": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
}
JAVA_CODE_COLUMNS = ("snippet", "scode", "code", "source", "content")

# Java CSV rows can contain full source files in a single cell.
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)


def _trim_files(files: list[str], max_files: Optional[int]) -> list[str]:
    if max_files is None:
        return files
    return files[:max_files]


def _append_row(rows: list[dict], row: dict, max_rows: Optional[int]) -> bool:
    rows.append(row)
    return max_rows is not None and len(rows) >= max_rows


def _load_jsonl_rows(file_path: str, rows: list[dict], max_rows: Optional[int]) -> bool:
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            should_stop = _append_row(
                rows,
                {
                    "code": obj.get("code", ""),
                    "docstring": obj.get("docstring", ""),
                    "repo": obj.get("repo", ""),
                    "path": obj.get("path", ""),
                    "language": obj.get("language", ""),
                },
                max_rows=max_rows,
            )
            if should_stop:
                return True
    return False


def _load_source_file_rows(file_path: str, rows: list[dict], max_rows: Optional[int]) -> bool:
    ext = Path(file_path).suffix.lower()
    language = SOURCE_EXTENSION_TO_LANGUAGE.get(ext)
    if not language:
        return False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    return _append_row(
        rows,
        {
            "code": code,
            "docstring": "",
            "repo": "",
            "path": file_path,
            "language": language,
        },
        max_rows=max_rows,
    )


def _select_java_code_column(headers: list[str]) -> str | None:
    lookup = {h.strip().lower(): h for h in headers}
    for col in JAVA_CODE_COLUMNS:
        if col in lookup:
            return lookup[col]
    return None


def _load_java_csv_rows(file_path: str, rows: list[dict], max_rows: Optional[int]) -> bool:
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return False

        code_column = _select_java_code_column(reader.fieldnames)
        if not code_column:
            return False

        for index, record in enumerate(reader, start=1):
            code = str(record.get(code_column, "") or "")
            if not code.strip():
                continue

            should_stop = _append_row(
                rows,
                {
                    "code": code,
                    "docstring": "",
                    "repo": "",
                    "path": f"{file_path}#row{index}",
                    "language": "java",
                },
                max_rows=max_rows,
            )
            if should_stop:
                return True
    return False


def load_codesearchnet_data(
    folder_path: str,
    max_files: Optional[int] = None,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    jsonl_files = _trim_files(
        sorted(glob.glob(os.path.join(folder_path, "**", "*.jsonl"), recursive=True)),
        max_files=max_files,
    )
    source_files = _trim_files(
        sorted(
            path
            for ext in SOURCE_EXTENSION_TO_LANGUAGE
            for path in glob.glob(os.path.join(folder_path, "**", f"*{ext}"), recursive=True)
        ),
        max_files=max_files,
    )
    java_csv_files = _trim_files(
        sorted(glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)),
        max_files=max_files,
    )

    print("Discovered dataset files:")
    print(f"- JSONL files: {len(jsonl_files)}")
    print(f"- C++ source files: {len(source_files)}")
    print(f"- CSV files: {len(java_csv_files)}")

    rows: list[dict] = []

    for file_path in jsonl_files:
        if _load_jsonl_rows(file_path, rows, max_rows=max_rows):
            return pd.DataFrame(rows)

    for file_path in source_files:
        if _load_source_file_rows(file_path, rows, max_rows=max_rows):
            return pd.DataFrame(rows)

    for file_path in java_csv_files:
        if _load_java_csv_rows(file_path, rows, max_rows=max_rows):
            return pd.DataFrame(rows)

    return pd.DataFrame(rows)
