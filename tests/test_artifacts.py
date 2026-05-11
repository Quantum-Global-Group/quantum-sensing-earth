import json

from src.data.artifacts import build_month_alignment, normalize_month_key, write_artifact_manifest, write_coverage_artifacts


def test_normalize_month_key_accepts_common_formats():
    assert normalize_month_key("2025-01-17") == "2025-01"
    assert normalize_month_key("202501") == "2025-01"
    assert normalize_month_key("2025-02") == "2025-02"


def test_build_month_alignment_marks_missing_targets():
    rows = build_month_alignment(
        {"2025-01", "2025-02"},
        {"gldas": {"2025-01": "ok"}, "groundwater": {"2025-02": "ok"}},
    )

    assert rows == [
        {"month": "2025-01", "grace": "ok", "usdm": "ok", "gldas": "ok", "groundwater": "missing"},
        {"month": "2025-02", "grace": "ok", "usdm": "ok", "gldas": "missing", "groundwater": "ok"},
    ]


def test_write_coverage_and_artifact_manifests(tmp_path):
    (tmp_path / "timeline_metrics.csv").write_text("month,status\n2025-01,ok\n", encoding="utf-8")

    coverage = write_coverage_artifacts(tmp_path, {"2025-01", "2025-02"}, {"gldas": {"2025-01": "ok"}})
    manifest = write_artifact_manifest(tmp_path, producer_command="demo", required_for_dashboard={"timeline_metrics.csv"})

    assert coverage["targets"]["gldas"]["coverage"] == "1/2"
    assert (tmp_path / "coverage_summary.json").exists()
    assert (tmp_path / "month_alignment.csv").exists()
    payload = json.loads((tmp_path / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "artifact-manifest-v1"
    assert any(item["path"] == "timeline_metrics.csv" and item["required_for_dashboard_review"] for item in manifest["artifacts"])
