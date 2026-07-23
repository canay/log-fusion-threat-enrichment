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
TEXT_SUFFIXES = {".cff", ".csv", ".json", ".md", ".py", ".tex", ".txt"}
TEXT_FILENAMES = {".gitattributes", ".gitignore", "LICENSE"}


def manifest_identity(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_FILENAMES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest(), len(data)


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
        root / "code" / "strict_temporal_exposure_uncertainty_pipeline.py",
        root / "code" / "make_corrected_figures.py",
        root / "requirements-model.lock.txt",
        results / "corrected_linkage_results.json",
        results / "corrected_linkage_metrics.csv",
        results / "corrected_linkage_topk.csv",
        results / "exposure_strata.csv",
        results / "paired_seed_configuration_ap.csv",
        results / "uncertainty_summary.json",
        results / "PUBLIC_MANIFEST.json",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(root)}")

    if errors:
        print("\n".join(f"FAIL: {item}" for item in errors))
        return 1

    public_json = json.loads((results / "corrected_linkage_results.json").read_text(encoding="utf-8"))
    all_keys = set(flatten_keys(public_json))
    leaked_keys = sorted(
        key
        for key in all_keys
        if key in FORBIDDEN_JSON_KEYS or "time_restricted" in key
    )
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

    with (results / "exposure_strata.csv").open(encoding="utf-8", newline="") as handle:
        exposure_csv = list(csv.DictReader(handle))
    if len(exposure_csv) != len(public_json.get("exposure_strata", [])):
        errors.append("exposure-strata row count mismatch")

    with (results / "paired_seed_configuration_ap.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        paired_seed_csv = list(csv.DictReader(handle))
    if len(paired_seed_csv) != len(public_json.get("seed_paired_configuration_ap", [])):
        errors.append("paired-seed row count mismatch")

    uncertainty_file = json.loads(
        (results / "uncertainty_summary.json").read_text(encoding="utf-8")
    )
    if uncertainty_file != public_json.get("uncertainty"):
        errors.append("uncertainty summary mismatch")

    split = public_json.get("split", {})
    if split.get("group_overlap") != 0 or not split.get("strict_max_train_lt_min_test"):
        errors.append("strict primary split invariant failed")
    label_audit = public_json.get("label_audit", {})
    if label_audit.get("direct_rows_added_only_by_missing_missing_equality") != 0:
        errors.append("direct tuple missing-equals-missing invariant failed")
    if label_audit.get("nat_aware_rows_added_only_by_missing_missing_equality") != 0:
        errors.append("NAT-aware tuple missing-equals-missing invariant failed")

    timestamp_pattern = re.compile(r'"[^"]*time[^"]*"\s*:\s*"\d{4}-\d{2}-\d{2}[ T]')
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
    if manifest.get("text_identity") != (
        "SHA-256 and byte counts use LF-normalized bytes for text files"
    ):
        errors.append("manifest text-identity rule missing or unsupported")
    for entry in manifest["files"]:
        path = root / entry["path"]
        if not path.is_file():
            errors.append(f"manifest file missing: {entry['path']}")
            continue
        actual_sha256, actual_bytes = manifest_identity(path)
        if actual_sha256 != entry["sha256"]:
            errors.append(f"manifest hash mismatch: {entry['path']}")
        if actual_bytes != entry["bytes"]:
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
