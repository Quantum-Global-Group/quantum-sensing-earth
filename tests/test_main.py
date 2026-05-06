from pathlib import Path

from argparse import Namespace

from src.main import (
    best_parameter_rows,
    calibrate_detector_params,
    calibrated_z_threshold,
    doctor_manifest,
    export_results_csv,
    fold_aggregate_rows,
    make_grace_demo,
    metric_stats,
    parse_seed_spec,
    real_data_ingestion_checklist,
    region_masks,
    run,
    science_readiness_badges,
    summarize_rows,
)


def test_export_results_csv(tmp_path):
    results = {
        "experiment_id": "demo",
        "runs": [
            {
                "seed": 1,
                "sensor_profiles": {
                    "classical": {"z_score": {"metrics": {"precision": 1.0, "recall": 0.5}}},
                    "quantum": {"z_score": {"metrics": {"precision": 0.8, "recall": 1.0}}},
                },
            }
        ],
    }
    output = tmp_path / "results.csv"
    export_results_csv(results, output)

    text = output.read_text(encoding="utf-8")
    assert "experiment_id" in text
    assert "classical" in text
    assert "quantum" in text
    assert "z_score" in text


def test_parse_seed_spec_accepts_count_list_and_range():
    assert parse_seed_spec("3", [42]) == [0, 1, 2]
    assert parse_seed_spec("42,44", [1]) == [42, 44]
    assert parse_seed_spec("42-44", [1]) == [42, 43, 44]


def test_summarize_rows_averages_metrics():
    rows = [
        {"seed": 1, "sensor_profile": "classical", "algorithm": "z_score", "variant": "z_score", "f1": 0.2},
        {"seed": 2, "sensor_profile": "classical", "algorithm": "z_score", "variant": "z_score", "f1": 0.6},
    ]
    summary = summarize_rows(rows)
    assert summary[0]["f1"] == 0.4
    assert summary[0]["f1_min"] == 0.2
    assert summary[0]["f1_max"] == 0.6


def test_metric_stats_clamps_bounded_ci():
    stats = metric_stats([0.0, 1.0], bounded=True)
    assert stats["ci95_low"] == 0.0
    assert stats["ci95_high"] == 1.0


def test_best_parameter_rows_picks_best_f1_per_sensor_detector():
    summary = [
        {"sensor_profile": "classical", "algorithm": "z_score", "variant": "a", "f1": 0.4},
        {"sensor_profile": "classical", "algorithm": "z_score", "variant": "b", "f1": 0.7},
        {"sensor_profile": "classical", "algorithm": "dbscan", "variant": "c", "f1": 0.5},
    ]
    best = best_parameter_rows(summary)
    assert {row["variant"] for row in best} == {"b", "c"}


def test_calibrated_z_threshold_uses_mask():
    import numpy as np

    grid = np.zeros((4, 4))
    grid[2, 2] = 10
    mask = np.zeros((4, 4), dtype=bool)
    mask[2, 2] = True

    threshold = calibrated_z_threshold(grid, true_mask=mask)

    assert 1.0 <= threshold <= 4.0


def test_calibrate_detector_params_supports_dbscan_and_isolation_forest():
    import numpy as np

    grid = np.zeros((16, 16))
    grid[7:10, 7:10] = 5.0
    mask = np.zeros((16, 16), dtype=bool)
    mask[7:10, 7:10] = True
    calibration_region = np.ones_like(mask, dtype=bool)

    dbscan_params, dbscan_meta = calibrate_detector_params(
        "dbscan",
        grid,
        {"eps": 0.4, "min_samples": 5},
        seed=1,
        true_mask=mask,
        calibration_region=calibration_region,
    )
    iso_params, iso_meta = calibrate_detector_params(
        "isolation_forest",
        grid,
        {"contamination": 0.05},
        seed=1,
        true_mask=mask,
        calibration_region=calibration_region,
    )

    assert {"eps", "min_samples"}.issubset(dbscan_params)
    assert "contamination" in iso_params
    assert dbscan_meta["candidate_count"] > 1
    assert iso_meta["candidate_count"] > 1


def test_region_masks_split_train_and_evaluation_regions():
    train, evaluation, metadata = region_masks((4, 6), "left-right")

    assert train[:, :3].all()
    assert not train[:, 3:].any()
    assert not evaluation[:, :3].any()
    assert evaluation[:, 3:].all()
    assert metadata["mode"] == "left-right"


def test_science_readiness_badges_identify_ready_real_raster():
    results = {
        "validation_source": "grace.tif",
        "validation_metadata": {
            "raster": {"driver": "GTiff", "crs": "EPSG:4326", "nodata": -9999.0},
            "coordinates": {"crs": "EPSG:4326"},
            "manifest": {
                "dataset": {"name": "GRACE Tellus", "citation": "JPL citation"},
                "mask": {"independent": True},
            },
        },
        "metadata": {"cli_args": {"calibrate_thresholds": True, "spatial_folds": 4, "calibration_split": "none"}},
    }

    badges = {label: (value, ok) for label, value, ok in science_readiness_badges(results)}

    assert badges["Validation"] == ("real raster", True)
    assert badges["Has CRS"] == ("yes", True)
    assert badges["Independent Mask"] == ("yes", True)
    assert badges["Held-out Calibration"] == ("yes", True)
    assert badges["Citation"] == ("yes", True)
    assert badges["Nodata Handling"] == ("yes", True)


def test_real_data_ingestion_checklist_flags_weak_labels():
    results = {
        "validation_source": "demo.tif",
        "validation_metadata": {
            "raster": {"driver": "GTiff", "crs": "EPSG:4326", "nodata": -9999.0},
            "manifest": {"dataset": {"citation": "Demo"}, "mask": {"independent": False}},
        },
        "metadata": {"cli_args": {"calibrate_thresholds": True, "spatial_folds": 4, "calibration_split": "none"}},
    }

    checklist = real_data_ingestion_checklist(results)

    assert checklist["ready"] is False
    assert any("software validation only" in reason for reason in checklist["reasons"])


def test_doctor_manifest_reports_missing_and_weak_fields(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "dataset:\n  source: https://example.com\n  units: centimeters equivalent water thickness\nmask:\n  provenance: Threshold mask\n  independent: false\n",
        encoding="utf-8",
    )

    result = doctor_manifest(manifest)

    assert result["valid"] is False
    assert "Missing required field: dataset.date_range" in result["errors"]
    assert any("software validation" in warning for warning in result["warnings"])


def test_fold_aggregate_rows_summarizes_best_and_worst_folds():
    rows = [
        {"sensor_profile": "s", "algorithm": "z_score", "variant": "z_score_fold_1", "base_variant": "z_score", "fold": 1, "f1": 0.2, "iou": 0.1, "false_positive_rate": 0.3},
        {"sensor_profile": "s", "algorithm": "z_score", "variant": "z_score_fold_2", "base_variant": "z_score", "fold": 2, "f1": 0.6, "iou": 0.4, "false_positive_rate": 0.1},
    ]

    aggregate = fold_aggregate_rows(rows)[0]

    assert aggregate["folds"] == 2
    assert aggregate["heldout_f1_mean"] == 0.4
    assert aggregate["best_fold"] == 2
    assert aggregate["worst_fold"] == 1


def test_run_exports_json_and_csv(monkeypatch, tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)

    results = run(Namespace(seeds="2", detectors=["z_score"], output=str(tmp_path), sweep=False, validation_grid=None, validation_mask=None))

    assert "summary" in results
    assert results["detector_variants"] == ["z_score"]
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "summary.csv").exists()
    assert (tmp_path / "best_params.csv").exists()
    assert (tmp_path / "metadata.json").exists()
    assert (tmp_path / "detection_quality_comparison.png").exists()
    assert (tmp_path / "experiment_summary.md").exists()
    assert (tmp_path / "report.html").exists()
    assert "best_parameters" in results


def test_grace_like_geotiff_report_has_readiness_and_fold_summary(monkeypatch, tmp_path):
    import numpy as np
    import pytest

    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)
    grid_path = tmp_path / "grace_like_grid.tif"
    mask_path = tmp_path / "grace_like_mask.tif"
    manifest_path = tmp_path / "validation_manifest.yaml"
    data = np.zeros((12, 12), dtype=np.float32)
    data[2:5, 2:5] = -8.0
    data[7:10, 8:11] = -6.0
    data[0, 0] = -9999.0
    mask = np.zeros((12, 12), dtype=np.uint8)
    mask[2:5, 2:5] = 1
    mask[7:10, 8:11] = 1
    transform = from_origin(-125.0, 50.0, 1.0, 1.0)
    with rasterio.open(
        grid_path,
        "w",
        driver="GTiff",
        height=12,
        width=12,
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data, 1)
    with rasterio.open(
        mask_path,
        "w",
        driver="GTiff",
        height=12,
        width=12,
        count=1,
        dtype=mask.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=0,
    ) as dataset:
        dataset.write(mask, 1)
    manifest_path.write_text(
        "\n".join(
            [
                "dataset:",
                "  name: GRACE Tellus monthly land water-equivalent-thickness subset",
                "  source: https://grace.jpl.nasa.gov/data/get-data/monthly-mass-grids-land/",
                "  date_range: 2024-01",
                "  units: centimeters equivalent water thickness",
                "  citation: JPL Tellus GRACE Level-3 monthly land product citation",
                "mask:",
                "  method: Independent basin mask fixture",
                "  provenance: Independent mock basin mask for download-free importer testing.",
                "  independent: true",
                "limitations:",
                "  - Download-free GRACE-like fixture for importer workflow tests.",
            ]
        ),
        encoding="utf-8",
    )

    results = run(
        Namespace(
            seeds="1",
            detectors=["z_score"],
            output=str(tmp_path / "out"),
            sweep=False,
            validation_grid=str(grid_path),
            validation_mask=str(mask_path),
            validation_manifest=str(manifest_path),
            validation_anomalies=None,
            missing="median",
            preprocess_detrend=False,
            preprocess_normalize=None,
            preprocess_clip=None,
            calibrate_thresholds=True,
            target_fpr=None,
            calibration_split="none",
            spatial_folds=2,
        )
    )

    report = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    metadata = (tmp_path / "out" / "metadata.json").read_text(encoding="utf-8")

    assert results["summary"][0]["runs"] == 2
    assert "Science Readiness" in report
    assert "Real-Data Ingestion Checklist" in report
    assert "real raster" in report
    assert "Independent Mask" in report
    assert "K-Fold Calibration Summary" in report
    assert "Tuning F1" in report
    assert "Aggregate Across Folds" in report
    assert "EPSG:4326" in report
    assert "2024-01" in report
    assert '"driver": "GTiff"' in metadata


def test_make_grace_demo_command_creates_inputs_and_report(monkeypatch, tmp_path):
    import pytest

    pytest.importorskip("rasterio")
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)

    result = make_grace_demo(Namespace(output=str(tmp_path / "demo"), spatial_folds=2))

    assert Path(result["report_html"]).exists()
    assert (tmp_path / "demo" / "inputs" / "grace_like_grid.tif").exists()
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    assert "Real-Data Ingestion Checklist" in report
    assert "software validation only" in report


def test_sweep_creates_best_config_rerun(monkeypatch, tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)

    results = run(Namespace(seeds="1", detectors=["z_score"], output=str(tmp_path), sweep=True, no_best_config_rerun=False, validation_grid=None, validation_mask=None))

    assert "best_config_output_dir" in results
    assert Path(results["best_config_output_dir"]).exists()
    assert (Path(results["best_config_output_dir"]) / "report.html").exists()
