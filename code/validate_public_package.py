"""Fail-closed checks for the curated aggregate public package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


FORBIDDEN_TEXT = [
    "canay" + "xps15",
    "PA-" + "1410",
    "PAN-OS " + "11.1.10",
    "active-" + "passive",
    "session_id_" + "hash",
    "0.071" + "801",
    "0.071" + "054",
    "54-" + "fold",
]
FORBIDDEN_JSON_KEYS = {"host", "created_at", "started_at", "cutoff_time"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from flatten_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_keys(child)


def key(row: dict) -> tuple:
    return (
        row["evaluation"],
        row["model"],
        row["feature_set"],
        int(row["seed"]),
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors: list[str] = []
    results = root / "results"

    required = [
        root / "README.md",
        root / "CORRECTION_NOTICE.md",
        root / "TRACEABILITY.md",
        root / "CITATION.cff",
        root / "requirements.txt",
        root / "code" / "corrected_label_group_disjoint_pipeline.py",
        root / "code" / "make_corrected_figures.py",
        results / "corrected_linkage_results.json",
        results / "corrected_linkage_metrics.csv",
        results / "corrected_linkage_topk.csv",
        results / "PUBLIC_MANIFEST.json",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(root)}")

    if errors:
        print("\n".join(f"FAIL: {item}" for item in errors))
        return 1

    public_json = json.loads((results / "corrected_linkage_results.json").read_text(encoding="utf-8"))
    leaked_keys = sorted(FORBIDDEN_JSON_KEYS.intersection(flatten_keys(public_json)))
    if leaked_keys:
        errors.append(f"forbidden JSON keys: {', '.join(leaked_keys)}")

    with (results / "corrected_linkage_metrics.csv").open(encoding="utf-8", newline="") as handle:
        metric_csv = list(csv.DictReader(handle))
    metric_json = public_json["results"]
    if len(metric_csv) != len(metric_json):
        errors.append(f"metric row count mismatch: CSV={len(metric_csv)} JSON={len(metric_json)}")
    else:
        lookup = {key(row): row for row in metric_json}
        for row in metric_csv:
            candidate = lookup.get(key(row))
            if candidate is None:
                errors.append(f"metric key missing in JSON: {key(row)}")
                continue
            for field in ("macro_f1", "average_precision", "roc_auc", "positive_precision", "positive_recall"):
                if abs(float(row[field]) - float(candidate[field])) > 1e-12:
                    errors.append(f"metric mismatch {key(row)} {field}")

    with (results / "corrected_linkage_topk.csv").open(encoding="utf-8", newline="") as handle:
        topk_csv = list(csv.DictReader(handle))
    topk_json = public_json["topk"]
    if len(topk_csv) != len(topk_json):
        errors.append(f"top-k row count mismatch: CSV={len(topk_csv)} JSON={len(topk_json)}")
    else:
        lookup = {
            (row["evaluation"], row["model"], row["feature_set"], int(row["seed"]), int(row["k"])): row
            for row in topk_json
        }
        for row in topk_csv:
            row_key = (
                row["evaluation"],
                row["model"],
                row["feature_set"],
                int(row["seed"]),
                int(row["k"]),
            )
            candidate = lookup.get(row_key)
            if candidate is None:
                errors.append(f"top-k key missing in JSON: {row_key}")
                continue
            for field in ("precision", "recall"):
                if abs(float(row[field]) - float(candidate[field])) > 1e-12:
                    errors.append(f"top-k mismatch {row_key} {field}")

    timestamp_pattern = re.compile(
        r'"(?:cutoff_time|receive_time|generate_time|start_time|timestamp)"\s*:\s*"\d{4}'
    )
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f"file exceeds 5 MiB: {path.relative_to(root)}")
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.suffix.lower() in {".md", ".txt", ".json", ".cff", ".py", ".csv", ".tex"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in FORBIDDEN_TEXT:
                if needle.lower() in text.lower():
                    errors.append(f"forbidden text {needle!r} in {path.relative_to(root)}")
            if timestamp_pattern.search(text):
                errors.append(f"absolute timestamp field in {path.relative_to(root)}")

    data_csv = [path for path in (root / "data").rglob("*.csv")]
    if data_csv:
        errors.extend(f"row-like data file present: {path.relative_to(root)}" for path in data_csv)

    manifest = json.loads((results / "PUBLIC_MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = root / entry["path"]
        if not path.is_file():
            errors.append(f"manifest file missing: {entry['path']}")
            continue
        if digest(path) != entry["sha256"]:
            errors.append(f"manifest hash mismatch: {entry['path']}")
        if path.stat().st_size != entry["bytes"]:
            errors.append(f"manifest size mismatch: {entry['path']}")

    if errors:
        for item in errors:
            print(f"FAIL: {item}")
        return 1
    print(
        "PASS: corrected aggregate package; "
        f"metrics={len(metric_json)} topk={len(topk_json)} "
        f"manifest_files={len(manifest['files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
