from __future__ import annotations

import csv
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def normalize_month_key(value: Any) -> str | None:
    """Return a canonical YYYY-MM month key from common date-like inputs."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 7 and text[4] == "-" and text[5:7].isdigit():
        return text[:7]
    if len(text) == 6 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}"
    parsed = pd.to_datetime(text, errors="coerce", utc=False)
    if pd.isna(parsed):
        return None
    return parsed.strftime("%Y-%m")


def command_text(argv: list[str] | None = None) -> str:
    argv = argv if argv is not None else sys.argv
    return " ".join(shlex.quote(str(part)) for part in argv)


def artifact_type(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower().lstrip(".")
    if name.endswith("_summary.json") or name in {"metadata.json", "coverage_summary.json"}:
        return "metadata"
    if name.endswith("_manifest.yaml") or name.endswith("_manifest.yml") or name == "artifact_manifest.json":
        return "manifest"
    if suffix in {"csv", "json", "yaml", "yml"}:
        return "data"
    if suffix in {"png", "jpg", "jpeg", "svg", "html", "md"}:
        return "review_artifact"
    if suffix in {"tif", "tiff", "nc"}:
        return "geospatial_data"
    return suffix or "artifact"


def write_artifact_manifest(
    output_dir: Path,
    producer_command: str | None = None,
    required_for_dashboard: set[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    required = required_for_dashboard or set()
    artifacts = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(output_dir).as_posix()
        artifacts.append(
            {
                "path": rel,
                "artifact_type": artifact_type(path),
                "producer_command": producer_command or command_text(),
                "generated_at_utc": generated_at,
                "required_for_dashboard_review": rel in required or path.name in required,
            }
        )

    if not any(item["path"] == "artifact_manifest.json" for item in artifacts):
        artifacts.append(
            {
                "path": "artifact_manifest.json",
                "artifact_type": "manifest",
                "producer_command": producer_command or command_text(),
                "generated_at_utc": generated_at,
                "required_for_dashboard_review": True,
            }
        )

    payload = {
        "schema_version": "artifact-manifest-v1",
        "generated_at_utc": generated_at,
        "producer_command": producer_command or command_text(),
        "output_dir": str(output_dir),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    if extra_metadata:
        payload.update(extra_metadata)
    (output_dir / "artifact_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def month_status_map(rows: list[dict[str, Any]] | pd.DataFrame, status_column: str = "status") -> dict[str, str]:
    if isinstance(rows, pd.DataFrame):
        iterable = rows.to_dict("records")
    else:
        iterable = rows
    status_by_month: dict[str, str] = {}
    for row in iterable:
        month = normalize_month_key(row.get("month") or row.get("date"))
        if not month:
            continue
        status = str(row.get(status_column, "ok") or "ok")
        if status_by_month.get(month) == "ok":
            continue
        status_by_month[month] = "ok" if status == "ok" else status
    return status_by_month


def build_month_alignment(
    detection_months: list[str] | set[str],
    target_status: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    months = sorted({month for month in (normalize_month_key(item) for item in detection_months) if month})
    rows = []
    for month in months:
        row: dict[str, Any] = {"month": month}
        row["grace"] = "ok"
        row["usdm"] = "ok"
        for target, statuses in target_status.items():
            row[target] = statuses.get(month, "missing")
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_coverage_artifacts(
    output_dir: Path,
    detection_months: list[str] | set[str],
    target_status: dict[str, dict[str, str]],
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    rows = build_month_alignment(detection_months, target_status)
    write_csv(output_dir / "month_alignment.csv", rows)
    total = len(rows)
    summary_targets = {
        "grace": {"ok_months": total, "requested_months": total, "coverage": f"{total}/{total}", "missing_months": []},
        "usdm": {"ok_months": total, "requested_months": total, "coverage": f"{total}/{total}", "missing_months": []},
    }
    for target, statuses in target_status.items():
        ok = [month for month in (row["month"] for row in rows) if statuses.get(month) == "ok"]
        missing = [month for month in (row["month"] for row in rows) if statuses.get(month) != "ok"]
        summary_targets[target] = {
            "ok_months": len(ok),
            "requested_months": total,
            "coverage": f"{len(ok)}/{total}",
            "missing_months": missing,
        }
    summary = {
        "schema_version": "coverage-summary-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "months": [row["month"] for row in rows],
        "targets": summary_targets,
        "month_alignment_csv": "month_alignment.csv",
    }
    (output_dir / "coverage_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
