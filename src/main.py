import argparse
import csv
import html
import importlib.metadata
import json
import platform
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from src.data.generate_synthetic_gravity import generate_synthetic_gravity_field
from src.data.load_geospatial_data import load_validation_anomalies, load_validation_dataset
from src.data.preprocess import preprocess_grid
from src.models.anomaly_detector import detect_dbscan, detect_isolation_forest, detect_z_score
from src.models.evaluation import classification_metrics
from src.models.evaluation import evaluate
from src.sensors.classical_sensor import measure_with_classical_profile
from src.sensors.quantum_sensor_profile import measure_with_quantum_enhanced_profile
from src.visualization.maps import (
    save_detection_quality_comparison,
    save_grid_image,
    save_mask_overlay,
    save_region_split_map,
    save_uncertainty_plot,
)

CONFIG_DIR = Path("configs")
SUMMARY_METRICS = (
    "precision",
    "recall",
    "f1",
    "iou",
    "false_positive_rate",
    "false_negative_rate",
    "rmse",
    "snr",
    "localization_error",
    "mean_per_anomaly_localization_error",
    "anomaly_object_recall",
    "tuning_f1",
    "tuning_iou",
    "tuning_false_positive_rate",
)
BOUNDED_METRICS = {
    "precision",
    "recall",
    "f1",
    "iou",
    "false_positive_rate",
    "false_negative_rate",
    "anomaly_object_recall",
    "tuning_f1",
    "tuning_iou",
    "tuning_false_positive_rate",
}


def provenance_warnings(results):
    warnings = []
    validation_metadata = results.get("validation_metadata") or {}
    manifest = validation_metadata.get("manifest") or {}
    dataset = manifest.get("dataset") or {}
    limitations = manifest.get("limitations") or []
    raster = validation_metadata.get("raster") or {}
    coordinates = validation_metadata.get("coordinates") or {}
    source_text = " ".join(
        str(value).lower()
        for value in (
            dataset.get("name"),
            dataset.get("source"),
            dataset.get("citation"),
            " ".join(str(item) for item in limitations),
        )
        if value
    )
    if not results.get("validation_source"):
        warnings.append("Synthetic benchmark: results do not validate against external gravity observations.")
    if any(token in source_text for token in ("synthetic", "demo", "fixture", "pseudo-real", "pseudo real")):
        warnings.append("Validation source is generated or demonstrative; treat scientific conclusions as provisional.")
    if not (raster.get("crs") or coordinates.get("crs")):
        warnings.append("No CRS metadata recorded; coordinate-aware interpretation is unavailable.")
    if results.get("metadata", {}).get("cli_args", {}).get("calibrate_thresholds"):
        split = results.get("metadata", {}).get("cli_args", {}).get("calibration_split", "none")
        folds = results.get("metadata", {}).get("cli_args", {}).get("spatial_folds", 1)
        if folds and folds > 1:
            warnings.append(f"Detector calibration used {folds}-fold spatial validation with separate tuning and held-out metrics.")
        elif split == "none":
            warnings.append("Detector calibration used the same region reported in final metrics.")
        else:
            warnings.append(f"Detector calibration used a held-out protocol: tuned on {split}, evaluated outside the tuning region.")
    return warnings


def validation_status(results):
    validation_metadata = results.get("validation_metadata") or {}
    manifest = validation_metadata.get("manifest") or {}
    dataset = manifest.get("dataset") or {}
    raster = validation_metadata.get("raster") or {}
    if not results.get("validation_source"):
        return "synthetic"
    text = " ".join(str(value).lower() for value in (dataset.get("name"), dataset.get("source"), dataset.get("citation")) if value)
    if raster.get("driver"):
        return "real raster" if not any(token in text for token in ("synthetic", "pseudo", "fixture", "demo")) else "pseudo-real raster"
    if any(token in text for token in ("pseudo", "fixture", "demo", "synthetic")):
        return "pseudo-real"
    return "real validation"


def science_readiness_badges(results):
    validation_metadata = results.get("validation_metadata") or {}
    manifest = validation_metadata.get("manifest") or {}
    dataset = manifest.get("dataset") or {}
    mask = manifest.get("mask") or {}
    raster = validation_metadata.get("raster") or {}
    coordinates = validation_metadata.get("coordinates") or {}
    cli_args = results.get("metadata", {}).get("cli_args", {})
    held_out = bool(cli_args.get("calibrate_thresholds")) and (
        (cli_args.get("spatial_folds") or 1) > 1 or cli_args.get("calibration_split") not in {None, "none"}
    )
    provenance_text = str(mask.get("provenance", "")).lower()
    independent_mask = mask.get("independent") is True or (
        "independent" in provenance_text and "not independent" not in provenance_text
    )
    badges = [
        ("Validation", validation_status(results), True),
        ("Has CRS", "yes" if (raster.get("crs") or coordinates.get("crs")) else "no", bool(raster.get("crs") or coordinates.get("crs"))),
        ("Independent Mask", "yes" if independent_mask else "weak or unspecified", independent_mask),
        ("Held-out Calibration", "yes" if held_out else "no", held_out),
        ("Citation", "yes" if dataset.get("citation") else "missing", bool(dataset.get("citation"))),
        ("Nodata Handling", "yes" if raster.get("nodata") is not None else "not recorded", raster.get("nodata") is not None),
    ]
    return badges


def real_data_ingestion_checklist(results):
    badges = science_readiness_badges(results)
    badge_map = {label: (value, ok) for label, value, ok in badges}
    status = validation_status(results)
    ready = status in {"real raster", "real validation"}
    reasons = []
    if status not in {"real raster", "real validation"}:
        reasons.append("Validation data is synthetic, pseudo-real, or demonstrative.")
    for label in ("Has CRS", "Independent Mask", "Held-out Calibration", "Citation", "Nodata Handling"):
        value, ok = badge_map[label]
        if not ok:
            ready = False
            reasons.append(f"{label}: {value}.")
    if not badge_map["Independent Mask"][1]:
        reasons.append("Weak or threshold-derived masks mean this run is software validation only.")
    if ready:
        reasons.append("Required provenance, mask, geospatial, and held-out calibration checks are present.")
    return {"ready": ready, "reasons": reasons}


def doctor_manifest(path):
    manifest = load_yaml(path)
    dataset = manifest.get("dataset") or {}
    mask = manifest.get("mask") or {}
    required = {
        "dataset.source": dataset.get("source"),
        "dataset.date_range": dataset.get("date_range"),
        "dataset.units": dataset.get("units"),
        "dataset.citation": dataset.get("citation"),
        "mask.provenance": mask.get("provenance"),
    }
    warnings = []
    errors = [f"Missing required field: {name}" for name, value in required.items() if not value]
    if "independent" not in mask and "weak_label_warning" not in mask:
        warnings.append("Mask independence is not declared. Add mask.independent true/false or mask.weak_label_warning.")
    if not dataset.get("crs"):
        warnings.append("CRS is not declared in the manifest. GeoTIFF metadata may still provide it at run time.")
    if not dataset.get("citation"):
        warnings.append("Citation is missing. Real-data reports should cite the exact GRACE product.")
    if not mask.get("independent"):
        warnings.append("Mask is not marked independent; report should be treated as software validation only.")
    if not (dataset.get("nodata") or manifest.get("preprocessing", {}).get("nodata")):
        warnings.append("Nodata handling is not described in the manifest.")
    return {"manifest": str(path), "valid": not errors, "errors": errors, "warnings": warnings}


def load_yaml(path):
    with Path(path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def parse_seed_spec(seed_spec, default):
    if seed_spec is None:
        return list(default)
    if isinstance(seed_spec, int):
        return list(range(seed_spec))
    if isinstance(seed_spec, str):
        if seed_spec.isdigit():
            return list(range(int(seed_spec)))
        seeds = []
        for part in seed_spec.split(","):
            part = part.strip()
            if "-" in part:
                start, end = [int(value) for value in part.split("-", 1)]
                seeds.extend(range(start, end + 1))
            elif part:
                seeds.append(int(part))
        return seeds
    return list(seed_spec)


def metric_stats(values, bounded=False):
    numeric = np.array([value for value in values if value is not None and np.isfinite(value)], dtype=float)
    if numeric.size == 0:
        return {"mean": None, "std": None, "min": None, "max": None, "ci95_low": None, "ci95_high": None}
    mean = float(np.mean(numeric))
    std = float(np.std(numeric, ddof=1)) if numeric.size > 1 else 0.0
    margin = 1.96 * std / float(np.sqrt(numeric.size)) if numeric.size > 1 else 0.0
    ci95_low = mean - margin
    ci95_high = mean + margin
    if bounded:
        ci95_low = max(0.0, ci95_low)
        ci95_high = min(1.0, ci95_high)
    return {
        "mean": mean,
        "std": std,
        "min": float(np.min(numeric)),
        "max": float(np.max(numeric)),
        "ci95_low": ci95_low,
        "ci95_high": ci95_high,
    }


def detector_variants(detection_config, detectors=None, sweep=False):
    selected = detectors or list(detection_config.get("algorithms", {}))
    variants = []
    for algorithm in selected:
        params = deepcopy(detection_config["algorithms"][algorithm])
        params.pop("type", None)
        if not sweep:
            variants.append({"algorithm": algorithm, "variant": algorithm, "params": params})
            continue
        if algorithm == "z_score":
            for threshold in (2.0, 2.5, 3.0):
                next_params = {**params, "threshold": threshold}
                variants.append({"algorithm": algorithm, "variant": f"z_score_threshold_{threshold:g}", "params": next_params})
        elif algorithm == "dbscan":
            for eps in (0.25, 0.4, 0.6):
                next_params = {**params, "eps": eps}
                variants.append({"algorithm": algorithm, "variant": f"dbscan_eps_{eps:g}", "params": next_params})
        elif algorithm == "isolation_forest":
            for contamination in (0.03, 0.05, 0.08):
                next_params = {**params, "contamination": contamination}
                variants.append({"algorithm": algorithm, "variant": f"isolation_forest_contamination_{contamination:g}", "params": next_params})
        else:
            variants.append({"algorithm": algorithm, "variant": algorithm, "params": params})
    return variants


def calibrated_z_threshold(grid, true_mask=None, target_fpr=None):
    mean = float(np.mean(grid))
    std = float(np.std(grid)) or 1.0
    scores = np.abs((grid - mean) / std)
    if true_mask is not None:
        best_threshold = 2.5
        best_f1 = -1.0
        for threshold in np.linspace(1.0, 4.0, 25):
            metrics = classification_metrics(true_mask, scores >= threshold)
            if metrics["f1"] > best_f1:
                best_f1 = metrics["f1"]
                best_threshold = float(threshold)
        return best_threshold
    if target_fpr is not None:
        background_scores = scores.ravel()
        return float(np.quantile(background_scores, max(0.0, min(1.0, 1.0 - target_fpr))))
    return None


def spatial_fold_regions(shape, folds):
    if folds <= 1:
        train = np.ones(shape, dtype=bool)
        evaluation = np.ones(shape, dtype=bool)
        return [(train, evaluation, {"mode": "none", "fold": 0, "train_region": "all", "evaluation_region": "all"})]
    regions = []
    width = shape[1]
    edges = np.linspace(0, width, folds + 1, dtype=int)
    for fold in range(folds):
        evaluation = np.zeros(shape, dtype=bool)
        evaluation[:, edges[fold] : edges[fold + 1]] = True
        train = ~evaluation
        regions.append(
            (
                train,
                evaluation,
                {
                    "mode": "spatial-kfold",
                    "fold": fold + 1,
                    "folds": folds,
                    "train_region": f"all except x columns {edges[fold]}:{edges[fold + 1]}",
                    "evaluation_region": f"x columns {edges[fold]}:{edges[fold + 1]}",
                },
            )
        )
    return regions


def region_masks(shape, split="none"):
    train = np.ones(shape, dtype=bool)
    evaluation = np.ones(shape, dtype=bool)
    if split in {None, "none"}:
        return train, evaluation, {"mode": "none", "train_region": "all", "evaluation_region": "all"}
    h, w = shape
    if split == "left-right":
        train = np.zeros(shape, dtype=bool)
        evaluation = np.zeros(shape, dtype=bool)
        train[:, : w // 2] = True
        evaluation[:, w // 2 :] = True
        return train, evaluation, {"mode": split, "train_region": "left half", "evaluation_region": "right half"}
    if split == "top-bottom":
        train = np.zeros(shape, dtype=bool)
        evaluation = np.zeros(shape, dtype=bool)
        train[: h // 2, :] = True
        evaluation[h // 2 :, :] = True
        return train, evaluation, {"mode": split, "train_region": "top half", "evaluation_region": "bottom half"}
    raise ValueError(f"Unsupported calibration split: {split}")


def score_candidate(true_mask, pred_mask, calibration_region, target_fpr=None):
    region = calibration_region.astype(bool)
    metrics = classification_metrics(true_mask[region], pred_mask[region])
    if target_fpr is not None:
        return -abs(metrics["false_positive_rate"] - target_fpr)
    return 0.7 * metrics["f1"] + 0.3 * metrics["iou"]


def tuning_metrics(true_mask, pred_mask, calibration_region):
    region = calibration_region.astype(bool)
    return classification_metrics(true_mask[region], pred_mask[region])


def calibrate_detector_params(algorithm, grid, base_params, seed, true_mask=None, calibration_region=None, target_fpr=None):
    params = deepcopy(base_params)
    calibration_region = calibration_region if calibration_region is not None else np.ones_like(grid, dtype=bool)
    candidates = []
    if algorithm == "z_score":
        if target_fpr is not None and true_mask is None:
            mean = float(np.mean(grid[calibration_region]))
            std = float(np.std(grid[calibration_region])) or 1.0
            scores = np.abs((grid - mean) / std)
            threshold = float(np.quantile(scores[calibration_region], max(0.0, min(1.0, 1.0 - target_fpr))))
            return {**params, "threshold": threshold}, {"objective": "target_fpr", "score": None, "tuning_metrics": {}}
        candidates = [{**params, "threshold": float(value)} for value in np.linspace(1.0, 4.0, 25)]
    elif algorithm == "dbscan":
        for eps in (0.15, 0.25, 0.4, 0.6, 0.8, 1.0):
            for min_samples in (3, 5, 8, 12):
                candidates.append({**params, "eps": eps, "min_samples": min_samples})
    elif algorithm == "isolation_forest":
        for contamination in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
            candidates.append({**params, "contamination": contamination})
    else:
        return params, {"objective": "not_calibrated", "score": None}

    if true_mask is None:
        return params, {"objective": "no_mask_available", "score": None}

    best = None
    best_pred = None
    best_score = -float("inf")
    for candidate in candidates:
        pred = run_detector(grid, algorithm, candidate, seed)
        score = score_candidate(true_mask, pred, calibration_region, target_fpr=target_fpr)
        if score > best_score:
            best_score = score
            best = candidate
            best_pred = pred
    objective = "target_fpr" if target_fpr is not None else "f1_iou"
    return best or params, {
        "objective": objective,
        "score": best_score,
        "candidate_count": len(candidates),
        "tuning_metrics": tuning_metrics(true_mask, best_pred, calibration_region) if best_pred is not None else {},
    }


def run_detector(grid, algorithm, params, seed):
    if algorithm == "z_score":
        return detect_z_score(grid, threshold=params.get("threshold", 2.5))
    if algorithm == "isolation_forest":
        return detect_isolation_forest(grid, contamination=params.get("contamination", 0.05), seed=seed)
    if algorithm == "dbscan":
        return detect_dbscan(grid, eps=params.get("eps", 0.4), min_samples=params.get("min_samples", 5))
    raise ValueError(f"Unsupported anomaly detection algorithm: {algorithm}")


def detect_with_variant(grid, variant, seed, calibration_mask=None, calibration_region=None, target_fpr=None):
    algorithm = variant["algorithm"]
    params = deepcopy(variant["params"])
    if calibration_mask is not None or target_fpr is not None:
        params, calibration = calibrate_detector_params(
            algorithm,
            grid,
            params,
            seed,
            true_mask=calibration_mask,
            calibration_region=calibration_region,
            target_fpr=target_fpr,
        )
        variant["calibrated_params"] = params
        variant["calibration"] = calibration
    return run_detector(grid, algorithm, params, seed)


def generate_field(simulation, seed, validation_grid=None, validation_mask=None, validation_anomalies=None):
    if validation_grid is not None:
        return validation_grid, validation_mask, validation_anomalies or []
    return generate_synthetic_gravity_field(
        grid_size=tuple(simulation.get("grid_size", [128, 128])),
        anomaly_count=simulation.get("anomaly_count", 4),
        intensity_range=tuple(simulation.get("anomaly_intensity_range", [-1.0, -0.2])),
        sigma_range=tuple(simulation.get("anomaly_sigma_range", [4.0, 12.0])),
        seed=seed,
        background_std=simulation.get("background_std", 0.01),
        terrain_gradient=simulation.get("terrain_gradient", 0.0),
        correlated_noise_radius=simulation.get("correlated_noise_radius", 0),
        anomaly_depth_range=tuple(simulation.get("anomaly_depth_range", [1.0, 1.0])),
        anomaly_size_scale=simulation.get("anomaly_size_scale", 1.0),
        density_contrast_range=tuple(simulation.get("density_contrast_range", [-1.0, -1.0])),
        sensor_altitude=simulation.get("sensor_altitude", 1.0),
        return_metadata=True,
    )


def sensor_profiles(sensor_config):
    return {
        "classical_gravimeter": (measure_with_classical_profile, sensor_config["classical_gravimeter"], "Classical Sensor Profile"),
        "quantum_gravity_gradiometer": (measure_with_quantum_enhanced_profile, sensor_config["quantum_gravity_gradiometer"], "Quantum-Enhanced Sensor Profile"),
    }


def run_single_seed(
    seed,
    simulation,
    sensor_config,
    variants,
    output_dir,
    render_artifacts=False,
    validation_grid=None,
    validation_mask=None,
    validation_anomalies=None,
    calibrate_thresholds=False,
    target_fpr=None,
    calibration_split="none",
    spatial_folds=1,
):
    field, true_mask, anomalies = generate_field(simulation, seed, validation_grid, validation_mask, validation_anomalies)
    if calibrate_thresholds and spatial_folds > 1:
        split_regions = spatial_fold_regions(true_mask.shape, spatial_folds)
    else:
        calibration_region, evaluation_region, split_metadata = region_masks(true_mask.shape, calibration_split if calibrate_thresholds else "none")
        split_regions = [(calibration_region, evaluation_region, split_metadata)]
    result = {"seed": seed, "anomalies": anomalies, "calibration_splits": [item[2] for item in split_regions], "sensor_profiles": {}}
    if render_artifacts:
        save_grid_image(field, output_dir / "ground_truth.png", "Ground Truth Gravity Field")
        if calibrate_thresholds:
            for _, (calibration_region, evaluation_region, split_metadata) in enumerate(split_regions):
                suffix = f"_fold_{split_metadata.get('fold')}" if split_metadata.get("mode") == "spatial-kfold" else ""
                save_region_split_map(
                    calibration_region,
                    evaluation_region,
                    output_dir / f"calibration_evaluation_regions{suffix}.png",
                    f"Calibration and Evaluation Regions{suffix.replace('_', ' ')}",
                )
    for sensor_name, (measure_fn, params, title) in sensor_profiles(sensor_config).items():
        observed = measure_fn(
            field,
            seed=seed,
            noise_std=params["noise_std_mgal"],
            drift=params["drift_per_timestep_mgal"],
            resolution_blur_radius=params.get("resolution_blur_radius", 0),
            correlated_noise_radius=params.get("correlated_noise_radius", 0),
        )
        result["sensor_profiles"][sensor_name] = {}
        if render_artifacts:
            save_grid_image(observed, output_dir / f"{sensor_name}_measurement.png", title)
        for split_index, (calibration_region, evaluation_region, split_metadata) in enumerate(split_regions):
            for variant in variants:
                run_variant = deepcopy(variant)
                variant_key = variant["variant"]
                if split_metadata.get("mode") == "spatial-kfold":
                    variant_key = f"{variant_key}_fold_{split_metadata['fold']}"
                pred = detect_with_variant(
                    observed,
                    run_variant,
                    seed,
                    calibration_mask=true_mask if calibrate_thresholds else None,
                    calibration_region=calibration_region if calibrate_thresholds else None,
                    target_fpr=target_fpr if calibrate_thresholds else None,
                )
                result["sensor_profiles"][sensor_name][variant_key] = {
                    "algorithm": run_variant["algorithm"],
                    "base_variant": variant["variant"],
                    "fold": split_metadata.get("fold"),
                    "params": run_variant.get("calibrated_params", run_variant["params"]),
                    "calibrated": bool(run_variant.get("calibrated_params")),
                    "calibration": run_variant.get("calibration", {}),
                    "calibration_split": split_metadata,
                    "metrics": evaluate(
                        field,
                        true_mask,
                        observed,
                        pred,
                        anomalies=anomalies,
                        evaluation_region=evaluation_region if calibrate_thresholds and split_metadata.get("mode") != "none" else None,
                    ),
                }
                if render_artifacts and split_index == 0:
                    save_mask_overlay(
                        observed,
                        true_mask,
                        pred,
                        output_dir / f"{sensor_name}_{variant['variant']}_overlay.png",
                        f"{title}: {variant['variant']} anomaly overlay",
                    )
    return result


def flatten_result_rows(results):
    rows = []
    for run_result in results["runs"]:
        for sensor_name, detector_results in run_result["sensor_profiles"].items():
            for variant_name, sensor_result in detector_results.items():
                row = {
                    "experiment_id": results["experiment_id"],
                    "seed": run_result["seed"],
                    "sensor_profile": sensor_name,
                    "algorithm": sensor_result.get("algorithm", variant_name),
                    "variant": variant_name,
                    "base_variant": sensor_result.get("base_variant", variant_name),
                    "fold": sensor_result.get("fold"),
                    "params": json.dumps(sensor_result.get("params", {}), sort_keys=True),
                    "calibration": json.dumps(sensor_result.get("calibration", {}), sort_keys=True),
                    "tuning_f1": sensor_result.get("calibration", {}).get("tuning_metrics", {}).get("f1"),
                    "tuning_iou": sensor_result.get("calibration", {}).get("tuning_metrics", {}).get("iou"),
                    "tuning_false_positive_rate": sensor_result.get("calibration", {}).get("tuning_metrics", {}).get("false_positive_rate"),
                }
                row.update(sensor_result["metrics"])
                rows.append(row)
    return rows


def summarize_rows(rows):
    grouped = {}
    for row in rows:
        summary_variant = row.get("base_variant") or row["variant"]
        key = f"{row['sensor_profile']}::{summary_variant}"
        metrics = grouped.setdefault(
            key,
            {"sensor_profile": row["sensor_profile"], "algorithm": row["algorithm"], "variant": summary_variant, "params": row.get("params", "{}"), "runs": 0},
        )
        metrics["runs"] += 1
        for metric in SUMMARY_METRICS:
            if row.get(metric) is not None:
                metrics.setdefault(metric, []).append(row[metric])
    summary = []
    for metrics in grouped.values():
        row = {key: value for key, value in metrics.items() if not isinstance(value, list)}
        for metric in SUMMARY_METRICS:
            stats = metric_stats(metrics.get(metric, []), bounded=metric in BOUNDED_METRICS)
            for stat_name, value in stats.items():
                row[f"{metric}_{stat_name}"] = value
            row[metric] = stats["mean"]
        summary.append(row)
    return summary


def best_parameter_rows(summary):
    grouped = {}
    for row in summary:
        key = (row["sensor_profile"], row["algorithm"])
        current = grouped.get(key)
        if current is None or (row.get("f1") or 0.0) > (current.get("f1") or 0.0):
            grouped[key] = row
    return list(grouped.values())


def export_results_csv(results, path):
    rows = flatten_result_rows(results)
    fieldnames = sorted({key for row in rows for key in row})
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_summary_csv(summary, path):
    fieldnames = sorted({key for row in summary for key in row})
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def export_best_params_csv(best_rows, path):
    fieldnames = ("sensor_profile", "algorithm", "variant", "params", "runs", "f1", "iou", "rmse", "snr")
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in best_rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def fold_aggregate_rows(rows):
    grouped = {}
    for row in rows:
        if row.get("fold") in {None, ""}:
            continue
        key = (row["sensor_profile"], row["algorithm"], row.get("base_variant") or row["variant"])
        grouped.setdefault(key, []).append(row)
    aggregates = []
    for (sensor, algorithm, variant), fold_rows in grouped.items():
        f1_values = np.array([row.get("f1") for row in fold_rows if row.get("f1") is not None], dtype=float)
        iou_values = np.array([row.get("iou") for row in fold_rows if row.get("iou") is not None], dtype=float)
        fpr_values = np.array([row.get("false_positive_rate") for row in fold_rows if row.get("false_positive_rate") is not None], dtype=float)
        if f1_values.size == 0:
            continue
        best = max(fold_rows, key=lambda row: row.get("f1") if row.get("f1") is not None else -1.0)
        worst = min(fold_rows, key=lambda row: row.get("f1") if row.get("f1") is not None else float("inf"))
        aggregates.append(
            {
                "sensor_profile": sensor,
                "algorithm": algorithm,
                "variant": variant,
                "folds": len(fold_rows),
                "heldout_f1_mean": float(np.mean(f1_values)),
                "heldout_f1_std": float(np.std(f1_values, ddof=1)) if f1_values.size > 1 else 0.0,
                "heldout_iou_mean": float(np.mean(iou_values)) if iou_values.size else None,
                "heldout_fpr_mean": float(np.mean(fpr_values)) if fpr_values.size else None,
                "best_fold": best.get("fold"),
                "best_fold_f1": best.get("f1"),
                "worst_fold": worst.get("fold"),
                "worst_fold_f1": worst.get("f1"),
            }
        )
    return aggregates


def variants_from_best_rows(best_rows):
    return [
        {
            "algorithm": row["algorithm"],
            "variant": row["variant"],
            "params": json.loads(row.get("params") or "{}"),
        }
        for row in best_rows
    ]


def parse_clip(value):
    if value in {None, ""}:
        return None
    low, high = value.split(",", 1)
    return float(low), float(high)


def prepare_validation_data(args):
    validation_source = getattr(args, "validation_grid", None) if args else None
    if not validation_source:
        return None, None, None, []
    grid, mask, metadata = load_validation_dataset(
        validation_source,
        getattr(args, "validation_mask", None),
        getattr(args, "validation_manifest", None),
    )
    processed, preprocess_steps = preprocess_grid(
        grid,
        missing=getattr(args, "missing", "median"),
        detrend=getattr(args, "preprocess_detrend", False),
        normalize=getattr(args, "preprocess_normalize", None),
        clip=parse_clip(getattr(args, "preprocess_clip", None)),
    )
    metadata["preprocessing_steps"] = preprocess_steps
    anomalies = load_validation_anomalies(getattr(args, "validation_anomalies", None))
    if anomalies:
        metadata["anomaly_metadata_path"] = getattr(args, "validation_anomalies", None)
        metadata["anomaly_count"] = len(anomalies)
    return processed, mask, metadata, preprocess_steps, anomalies


def package_versions():
    packages = {}
    for name in ("numpy", "pandas", "scikit-learn", "pyyaml", "pytest", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return packages


def args_metadata(args):
    if args is None:
        return {}
    return {
        "seeds": getattr(args, "seeds", None),
        "detectors": getattr(args, "detectors", None),
        "output": getattr(args, "output", None),
        "sweep": getattr(args, "sweep", False),
        "validation_grid": getattr(args, "validation_grid", None),
        "validation_mask": getattr(args, "validation_mask", None),
        "validation_manifest": getattr(args, "validation_manifest", None),
        "validation_anomalies": getattr(args, "validation_anomalies", None),
        "preprocess_detrend": getattr(args, "preprocess_detrend", False),
        "preprocess_normalize": getattr(args, "preprocess_normalize", None),
        "preprocess_clip": getattr(args, "preprocess_clip", None),
        "missing": getattr(args, "missing", "median"),
        "calibrate_thresholds": getattr(args, "calibrate_thresholds", False),
        "target_fpr": getattr(args, "target_fpr", None),
        "calibration_split": getattr(args, "calibration_split", "none"),
        "spatial_folds": getattr(args, "spatial_folds", 1),
    }


def write_metadata(results, path):
    metadata = results["metadata"]
    Path(path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def write_experiment_summary(results, path):
    rows = results["summary"]
    best_rows = results["best_parameters"]
    best_f1 = max(rows, key=lambda row: row.get("f1") or 0.0)
    best_snr = max(rows, key=lambda row: row.get("snr") or 0.0)
    best_parameter_lines = [
        f"- `{row['sensor_profile']}` / `{row['algorithm']}`: `{row['variant']}` with mean F1 {row['f1']:.3f}."
        for row in sorted(best_rows, key=lambda row: (row["sensor_profile"], row["algorithm"]))
    ]
    lines = [
        "# Experiment Summary",
        "",
        f"Experiment: `{results['experiment_id']}`",
        f"Seeds: {', '.join(str(seed) for seed in results['batch_seeds'])}",
        f"Detector variants: {', '.join(results['detector_variants'])}",
        f"Validation source: `{results['validation_source'] or 'synthetic'}`",
        f"Validation manifest: `{results.get('validation_metadata', {}).get('manifest', {}).get('dataset', {}).get('name', 'n/a')}`",
        "",
        "## Best Aggregate Results",
        "",
        f"- Best mean F1: `{best_f1['sensor_profile']}` with `{best_f1['variant']}` at {best_f1['f1']:.3f}.",
        f"- Best mean SNR: `{best_snr['sensor_profile']}` with `{best_snr['variant']}` at {best_snr['snr']:.3f}.",
        "",
        "## Best Detector Settings",
        "",
        *best_parameter_lines,
        "",
        "## What This Proves",
        "",
        "This run demonstrates a repeatable benchmark harness for comparing sensor fidelity and anomaly detection quality across synthetic or externally supplied gravity grids.",
        "",
        "## What It Does Not Prove Yet",
        "",
        "Synthetic runs do not validate a physical quantum sensor model or real groundwater anomalies. Real validation depends on calibrated gravity grids and ground-truth masks.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html_report(results, output_dir):
    output_dir = Path(output_dir)
    flat_rows = flatten_result_rows(results)
    summary_rows = sorted(results["summary"], key=lambda row: row.get("f1") or 0.0, reverse=True)
    best_rows = sorted(results["best_parameters"], key=lambda row: row.get("f1") or 0.0, reverse=True)
    best_f1 = summary_rows[0]
    best_snr = max(summary_rows, key=lambda row: row.get("snr") or 0.0)
    run_count = len(results["batch_seeds"])
    validation_metadata = results.get("validation_metadata") or {}
    manifest = validation_metadata.get("manifest") or {}
    dataset_manifest = manifest.get("dataset") or {}
    raster_metadata = validation_metadata.get("raster") or {}
    coordinate_metadata = validation_metadata.get("coordinates") or {}
    preprocessing_steps = validation_metadata.get("preprocessing_steps") or []
    warnings = provenance_warnings(results)
    status = validation_status(results)
    readiness_badges = science_readiness_badges(results)
    ingestion_checklist = real_data_ingestion_checklist(results)

    def fmt(value, digits=3):
        return "n/a" if value is None else f"{value:.{digits}f}"

    def data_cell(value, digits=3):
        text = fmt(value, digits)
        sort_value = "" if value is None else f"{value:.12g}"
        return f'<td data-sort="{sort_value}">{text}</td>'

    def metadata_value(value):
        if value in (None, "", {}):
            return "n/a"
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    table_rows = []
    for row in summary_rows:
        overlay_name = f"{row['sensor_profile']}_{row['variant']}_overlay.png"
        overlay_link = f'<a href="{overlay_name}">{html.escape(row["variant"])}</a>' if (output_dir / overlay_name).exists() else html.escape(row["variant"])
        table_rows.append(
            f'<tr data-sensor="{html.escape(row["sensor_profile"])}" data-algorithm="{html.escape(row["algorithm"])}">'
            f"<td>{html.escape(row['sensor_profile'])}</td>"
            f"<td>{overlay_link}</td>"
            f"{data_cell(row.get('runs'), 0)}"
            f"{data_cell(row.get('f1'))}"
            f"{data_cell(row.get('iou'))}"
            f"{data_cell(row.get('rmse'), 4)}"
            f"{data_cell(row.get('snr'), 2)}"
            f"{data_cell(row.get('tuning_f1'))}"
            f"<td>{fmt(row.get('f1_ci95_low'))} - {fmt(row.get('f1_ci95_high'))}</td>"
            "</tr>"
        )
    fold_rows = []
    for row in sorted(flat_rows, key=lambda item: (item["sensor_profile"], item["algorithm"], item.get("fold") or 0)):
        if row.get("fold") in {None, ""}:
            continue
        fold_rows.append(
            f'<tr data-sensor="{html.escape(row["sensor_profile"])}" data-algorithm="{html.escape(row["algorithm"])}">'
            f"<td>{html.escape(row['sensor_profile'])}</td>"
            f"<td>{html.escape(row['algorithm'])}</td>"
            f"{data_cell(row.get('fold'), 0)}"
            f"<td><code>{html.escape(row.get('params', '{}'))}</code></td>"
            f"{data_cell(row.get('tuning_f1'))}"
            f"{data_cell(row.get('f1'))}"
            f"{data_cell(row.get('iou'))}"
            f"{data_cell(row.get('false_positive_rate'))}"
            "</tr>"
        )
    fold_table = "".join(fold_rows) or '<tr><td colspan="8">No k-fold calibration rows were generated for this run.</td></tr>'
    fold_aggregate_table_rows = []
    for row in sorted(fold_aggregate_rows(flat_rows), key=lambda item: (item["sensor_profile"], item["algorithm"])):
        fold_aggregate_table_rows.append(
            f'<tr data-sensor="{html.escape(row["sensor_profile"])}" data-algorithm="{html.escape(row["algorithm"])}">'
            f"<td>{html.escape(row['sensor_profile'])}</td>"
            f"<td>{html.escape(row['algorithm'])}</td>"
            f"<td>{html.escape(row['variant'])}</td>"
            f"{data_cell(row.get('folds'), 0)}"
            f"{data_cell(row.get('heldout_f1_mean'))}"
            f"{data_cell(row.get('heldout_f1_std'))}"
            f"{data_cell(row.get('heldout_iou_mean'))}"
            f"{data_cell(row.get('heldout_fpr_mean'))}"
            f"{data_cell(row.get('best_fold'), 0)}"
            f"{data_cell(row.get('best_fold_f1'))}"
            f"{data_cell(row.get('worst_fold'), 0)}"
            f"{data_cell(row.get('worst_fold_f1'))}"
            "</tr>"
        )
    fold_aggregate_table = "".join(fold_aggregate_table_rows) or '<tr><td colspan="12">No k-fold aggregate rows were generated for this run.</td></tr>'
    best_table_rows = []
    for row in best_rows:
        best_table_rows.append(
            f'<tr data-sensor="{html.escape(row["sensor_profile"])}" data-algorithm="{html.escape(row["algorithm"])}">'
            f"<td>{html.escape(row['sensor_profile'])}</td>"
            f"<td>{html.escape(row['algorithm'])}</td>"
            f"<td>{html.escape(row['variant'])}</td>"
            f"<td><code>{html.escape(row.get('params', '{}'))}</code></td>"
            f"{data_cell(row.get('f1'))}"
            f"{data_cell(row.get('iou'))}"
            "</tr>"
        )
    overlays = sorted(path.name for path in output_dir.glob("*_overlay.png"))[:12]
    overlay_cards = "\n".join(
        f'<figure><a href="{name}"><img src="{name}" alt="{html.escape(name)}"></a><figcaption>{html.escape(name)}</figcaption></figure>'
        for name in overlays
    )
    region_maps = sorted(path.name for path in output_dir.glob("calibration_evaluation_regions*.png"))
    region_cards = "\n".join(
        f'<figure><a href="{name}"><img src="{name}" alt="{html.escape(name)}"></a><figcaption>{html.escape(name)}</figcaption></figure>'
        for name in region_maps
    ) or "<p>No calibration/evaluation region maps were generated for this run.</p>"
    best_config_link = ""
    if results.get("best_config_output_dir"):
        best_config_path = Path(results["best_config_output_dir"])
        try:
            best_config_rel = best_config_path.relative_to(output_dir).as_posix()
        except ValueError:
            best_config_rel = best_config_path.as_posix()
        best_config_link = f' | <a href="{html.escape(best_config_rel)}/report.html">Best-config rerun report</a>'
    calibration_summary = "enabled" if results["metadata"]["cli_args"].get("calibrate_thresholds") else "disabled"
    held_out_summary = "spatial-kfold" if results["metadata"]["cli_args"].get("spatial_folds", 1) > 1 else results["metadata"]["cli_args"].get("calibration_split", "none")
    provenance_rows = [
        ("Dataset", dataset_manifest.get("name") or "synthetic/generated"),
        ("Source", dataset_manifest.get("source") or results.get("validation_source") or "synthetic"),
        ("Date range", dataset_manifest.get("date_range") or "n/a"),
        ("Units", dataset_manifest.get("units") or "grid units"),
        ("Citation", dataset_manifest.get("citation") or "n/a"),
        ("CRS", coordinate_metadata.get("crs") or raster_metadata.get("crs") or "n/a"),
        ("Resolution", metadata_value(coordinate_metadata.get("resolution") or raster_metadata.get("resolution"))),
        ("Bounds", metadata_value(coordinate_metadata.get("bounds") or raster_metadata.get("bounds"))),
        ("Transform", metadata_value(raster_metadata.get("transform"))),
        ("Nodata", metadata_value(raster_metadata.get("nodata"))),
        ("Pixel to coordinate", coordinate_metadata.get("pixel_to_coordinate") or raster_metadata.get("pixel_to_coordinate") or "n/a"),
        ("Mask method", (manifest.get("mask") or {}).get("method") or "n/a"),
        ("Preprocessing", "; ".join(step["operation"] for step in preprocessing_steps) or "none"),
        ("Detector calibration", calibration_summary),
        ("Calibration split", held_out_summary),
    ]
    provenance_table = "".join(f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value))}</td></tr>" for label, value in provenance_rows)
    limitations = manifest.get("limitations") or []
    limitation_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in limitations) or "<li>None recorded.</li>"
    warning_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings) or "<li>No provenance warnings recorded.</li>"
    badge_cards = "".join(
        f'<span class="badge {"ok" if ok else "warn"}"><strong>{html.escape(label)}:</strong> {html.escape(str(value))}</span>'
        for label, value, ok in readiness_badges
    )
    checklist_class = "ok" if ingestion_checklist["ready"] else "warning"
    checklist_status = "yes" if ingestion_checklist["ready"] else "no"
    checklist_items = "".join(f"<li>{html.escape(reason)}</li>" for reason in ingestion_checklist["reasons"])
    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Quantum Sensing Earth Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #17202a; background: #f7f9fb; }}
    main {{ max-width: 1240px; margin: 0 auto; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; background: white; }}
    th, td {{ border: 1px solid #ccd6dd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #e8eef4; cursor: pointer; user-select: none; }}
    img {{ max-width: 100%; border: 1px solid #ccd6dd; background: white; }}
    code {{ white-space: normal; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 20px 0; }}
    .card {{ background: white; border: 1px solid #d8e0e7; padding: 14px; }}
    .card .label {{ color: #506070; font-size: 12px; text-transform: uppercase; }}
    .card .value {{ font-size: 24px; font-weight: 700; margin-top: 6px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    figure {{ margin: 0; background: white; border: 1px solid #d8e0e7; padding: 8px; }}
    figcaption {{ font-size: 12px; margin-top: 6px; color: #506070; word-break: break-word; }}
    .meta {{ color: #506070; }}
    .warning {{ background: #fff8e5; border-color: #e1b84b; }}
    .badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 14px 0; }}
    .badge {{ display: inline-flex; gap: 4px; align-items: center; border: 1px solid #c8d2dc; padding: 6px 8px; background: white; font-size: 13px; }}
    .badge.ok {{ border-color: #6da875; background: #eef8f0; }}
    .badge.warn {{ border-color: #d4a441; background: #fff7df; }}
    .filters {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin: 18px 0; }}
    .filters label {{ display: grid; gap: 4px; font-size: 13px; color: #506070; }}
    select {{ padding: 7px; border: 1px solid #b9c6d1; background: white; }}
    details {{ background: white; border: 1px solid #d8e0e7; padding: 12px; margin: 18px 0; }}
    summary {{ cursor: pointer; font-weight: 700; }}
  </style>
</head>
<body>
<main>
  <h1>Quantum Sensing Earth Report</h1>
  <p class="meta"><strong>Experiment:</strong> {html.escape(results['experiment_id'])} | <strong>Sample size:</strong> {run_count} seed(s) | <strong>Validation source:</strong> {html.escape(results['validation_source'] or 'synthetic')}</p>
  <section class="cards">
    <div class="card"><div class="label">Best Mean F1</div><div class="value">{fmt(best_f1.get('f1'))}</div><div>{html.escape(best_f1['sensor_profile'])}<br>{html.escape(best_f1['variant'])}</div></div>
    <div class="card"><div class="label">Best Mean SNR</div><div class="value">{fmt(best_snr.get('snr'), 1)}</div><div>{html.escape(best_snr['sensor_profile'])}<br>{html.escape(best_snr['variant'])}</div></div>
    <div class="card"><div class="label">Detector Variants</div><div class="value">{len(results['detector_variants'])}</div><div>{html.escape(', '.join(results['detector_variants']))}</div></div>
    <div class="card"><div class="label">Validation Status</div><div class="value">{html.escape(status)}</div><div>{html.escape(held_out_summary)}</div></div>
    <div class="card"><div class="label">Generated</div><div class="value">{html.escape(results['metadata']['generated_at_utc'][:10])}</div><div>UTC</div></div>
  </section>
  <details open>
    <summary>Dataset Provenance</summary>
    <table>{provenance_table}</table>
    <h3>Limitations</h3>
    <ul>{limitation_items}</ul>
  </details>
  <details open class="warning">
    <summary>Provenance Warnings</summary>
    <ul>{warning_items}</ul>
  </details>
  <details open>
    <summary>Science Readiness</summary>
    <div class="badges">{badge_cards}</div>
  </details>
  <details open class="{checklist_class}">
    <summary>Real-Data Ingestion Checklist</summary>
    <p><strong>Ready for scientific interpretation?</strong> {checklist_status}</p>
    <ul>{checklist_items}</ul>
  </details>
  <details open>
    <summary>Calibration And Evaluation Regions</summary>
    <div class="grid">{region_cards}</div>
  </details>
  <h2>Detection Quality</h2>
  <img src="detection_quality_comparison.png" alt="Detection quality comparison">
  <h2>Uncertainty</h2>
  <img src="metric_uncertainty.png" alt="Metric uncertainty error bars">
  <div class="filters">
    <label>Sensor<select id="sensorFilter"><option value="">All sensors</option></select></label>
    <label>Detector<select id="algorithmFilter"><option value="">All detectors</option></select></label>
  </div>
  <details open>
    <summary>Parameter Sweep Winners</summary>
    <table class="sortable filterable">
      <thead><tr><th>Sensor</th><th>Detector</th><th>Winning Variant</th><th>Params</th><th>Mean F1</th><th>Mean IoU</th></tr></thead>
      <tbody>{''.join(best_table_rows)}</tbody>
    </table>
  </details>
  <details open>
    <summary>K-Fold Calibration Summary</summary>
    <h3>Aggregate Across Folds</h3>
    <table class="sortable filterable">
      <thead><tr><th>Sensor</th><th>Detector</th><th>Variant</th><th>Folds</th><th>Mean Held-out F1</th><th>F1 Std</th><th>Mean Held-out IoU</th><th>Mean Held-out FPR</th><th>Best Fold</th><th>Best F1</th><th>Worst Fold</th><th>Worst F1</th></tr></thead>
      <tbody>{fold_aggregate_table}</tbody>
    </table>
    <h3>Per-Fold Details</h3>
    <table class="sortable filterable">
      <thead><tr><th>Sensor</th><th>Detector</th><th>Fold</th><th>Tuned Params</th><th>Tuning F1</th><th>Held-out F1</th><th>Held-out IoU</th><th>Held-out FPR</th></tr></thead>
      <tbody>{fold_table}</tbody>
    </table>
  </details>
  <details open>
    <summary>Summary Statistics</summary>
    <table class="sortable filterable">
      <thead><tr><th>Sensor</th><th>Variant</th><th>n</th><th>Held-out F1</th><th>Held-out IoU</th><th>Mean RMSE</th><th>Mean SNR</th><th>Tuning F1</th><th>F1 95% CI</th></tr></thead>
      <tbody>{''.join(table_rows)}</tbody>
    </table>
  </details>
  <details open>
    <summary>Key Artifacts</summary>
    <div class="grid">
      <div><h3>Ground Truth</h3><img src="ground_truth.png" alt="Ground truth gravity field"></div>
      <div><h3>Classical Measurement</h3><img src="classical_gravimeter_measurement.png" alt="Classical measurement"></div>
      <div><h3>Quantum Measurement</h3><img src="quantum_gravity_gradiometer_measurement.png" alt="Quantum measurement"></div>
    </div>
  </details>
  <details>
    <summary>Anomaly Overlay Thumbnails</summary>
    <div class="grid">{overlay_cards}</div>
  </details>
  <h2>Data</h2>
  <p><a href="results.csv">Per-run CSV</a> | <a href="summary.csv">Summary CSV</a> | <a href="best_params.csv">Best params CSV</a> | <a href="metadata.json">Metadata</a> | <a href="results.json">JSON</a> | <a href="experiment_summary.md">Markdown summary</a>{best_config_link}</p>
  <script>
    const filterRows = () => {{
      const sensor = document.getElementById('sensorFilter').value;
      const algorithm = document.getElementById('algorithmFilter').value;
      document.querySelectorAll('tr[data-sensor]').forEach(row => {{
        const visible = (!sensor || row.dataset.sensor === sensor) && (!algorithm || row.dataset.algorithm === algorithm);
        row.style.display = visible ? '' : 'none';
      }});
    }};
    const sensors = new Set();
    const algorithms = new Set();
    document.querySelectorAll('tr[data-sensor]').forEach(row => {{
      sensors.add(row.dataset.sensor);
      algorithms.add(row.dataset.algorithm);
    }});
    for (const sensor of Array.from(sensors).sort()) {{
      document.getElementById('sensorFilter').insertAdjacentHTML('beforeend', `<option value="${{sensor}}">${{sensor}}</option>`);
    }}
    for (const algorithm of Array.from(algorithms).sort()) {{
      document.getElementById('algorithmFilter').insertAdjacentHTML('beforeend', `<option value="${{algorithm}}">${{algorithm}}</option>`);
    }}
    document.getElementById('sensorFilter').addEventListener('change', filterRows);
    document.getElementById('algorithmFilter').addEventListener('change', filterRows);
    document.querySelectorAll('table.sortable th').forEach((header, index) => {{
      header.addEventListener('click', () => {{
        const table = header.closest('table');
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        const ascending = header.dataset.sort !== 'asc';
        rows.sort((a, b) => {{
          const av = a.children[index].dataset.sort || a.children[index].innerText;
          const bv = b.children[index].dataset.sort || b.children[index].innerText;
          const an = parseFloat(av);
          const bn = parseFloat(bv);
          const result = Number.isFinite(an) && Number.isFinite(bn) ? an - bn : av.localeCompare(bv);
          return ascending ? result : -result;
        }});
        table.querySelector('tbody').append(...rows);
        table.querySelectorAll('th').forEach(th => th.dataset.sort = '');
        header.dataset.sort = ascending ? 'asc' : 'desc';
      }});
    }});
  </script>
</main>
</body>
</html>
"""
    (output_dir / "report.html").write_text(body, encoding="utf-8")


def write_output_bundle(results, output_dir):
    output_dir = Path(output_dir)
    rows = flatten_result_rows(results)
    results["summary"] = summarize_rows(rows)
    results["best_parameters"] = best_parameter_rows(results["summary"])
    results["sensor_profiles"] = results["runs"][0]["sensor_profiles"]

    (output_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    export_results_csv(results, output_dir / "results.csv")
    export_summary_csv(results["summary"], output_dir / "summary.csv")
    export_best_params_csv(results["best_parameters"], output_dir / "best_params.csv")
    write_metadata(results, output_dir / "metadata.json")
    save_detection_quality_comparison(rows, output_dir / "detection_quality_comparison.png")
    save_uncertainty_plot(results["summary"], output_dir / "metric_uncertainty.png")
    write_experiment_summary(results, output_dir / "experiment_summary.md")
    write_html_report(results, output_dir)
    return results


def build_results(
    experiment,
    simulation,
    sensor_config,
    detection_config,
    variants,
    batch_seeds,
    output_dir,
    args,
    validation_source=None,
    validation_grid=None,
    validation_mask=None,
    validation_anomalies=None,
    validation_metadata=None,
    run_label="main",
):
    results = {
        "experiment_id": experiment.get("experiment", {}).get("id", "qs-earth-demo-001"),
        "run_label": run_label,
        "batch_seeds": batch_seeds,
        "detector_variants": [variant["variant"] for variant in variants],
        "validation_source": validation_source,
        "validation_metadata": validation_metadata or {},
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "cli_args": args_metadata(args),
            "config_snapshot": {
                "experiment": experiment,
                "simulation": simulation,
                "sensors": sensor_config,
                "anomaly_detection": detection_config,
            },
            "validation_metadata": validation_metadata or {},
            "runtime": {
                "python": sys.version,
                "platform": platform.platform(),
            },
            "package_versions": package_versions(),
        },
        "runs": [],
    }
    for index, seed in enumerate(batch_seeds):
        results["runs"].append(
            run_single_seed(
                seed,
                simulation,
                sensor_config,
                variants,
                output_dir,
                render_artifacts=index == 0,
                validation_grid=validation_grid,
                validation_mask=validation_mask,
                validation_anomalies=validation_anomalies,
                calibrate_thresholds=getattr(args, "calibrate_thresholds", False),
                target_fpr=getattr(args, "target_fpr", None),
                calibration_split=getattr(args, "calibration_split", "none"),
                spatial_folds=getattr(args, "spatial_folds", 1),
            )
        )
    return results


def run_best_config_experiment(
    parent_results,
    experiment,
    simulation,
    sensor_config,
    detection_config,
    batch_seeds,
    output_dir,
    args,
    validation_source=None,
    validation_grid=None,
    validation_mask=None,
    validation_anomalies=None,
    validation_metadata=None,
):
    best_output_dir = Path(output_dir) / f"best_config_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    best_output_dir.mkdir(parents=True, exist_ok=True)
    best_variants = variants_from_best_rows(parent_results["best_parameters"])
    best_results = build_results(
        experiment,
        simulation,
        sensor_config,
        detection_config,
        best_variants,
        batch_seeds,
        best_output_dir,
        args,
        validation_source=validation_source,
        validation_grid=validation_grid,
        validation_mask=validation_mask,
        validation_anomalies=validation_anomalies,
        validation_metadata=validation_metadata,
        run_label="best_config",
    )
    best_results["tuned_from"] = str(output_dir)
    best_results["output_dir"] = str(best_output_dir)
    return write_output_bundle(best_results, best_output_dir)


def write_grace_like_demo_inputs(output_dir):
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError as exc:
        raise SystemExit("The GRACE demo command requires rasterio. Install with `python -m pip install -e .[geo]`.") from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    grid_path = output_dir / "grace_like_grid.tif"
    mask_path = output_dir / "grace_like_weak_mask.tif"
    manifest_path = output_dir / "validation_manifest.yaml"
    height, width = 36, 48
    y, x = np.mgrid[0:height, 0:width]
    grid = (
        -8.0 * np.exp(-(((x - 14) ** 2 + (y - 12) ** 2) / (2 * 5.0**2)))
        - 5.5 * np.exp(-(((x - 34) ** 2 + (y - 25) ** 2) / (2 * 6.0**2)))
        + 0.4 * np.sin(x / 5.0)
    ).astype(np.float32)
    nodata = -9999.0
    grid[0, 0] = nodata
    mask = ((grid <= -3.0) & (grid != nodata)).astype(np.uint8)
    transform = from_origin(-125.0, 50.0, 0.5, 0.5)
    with rasterio.open(
        grid_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=grid.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(grid, 1)
    with rasterio.open(
        mask_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
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
                "  name: GRACE Tellus demo raster",
                "  source: Download-free GRACE-like fixture generated by quantum-sensing-earth.",
                "  product: mock_grace_tellus_l3_land_demo",
                "  date_range: 2024-01",
                "  units: centimeters equivalent water thickness",
                "  crs: EPSG:4326",
                "  resolution: 0.5 degree pixels",
                "  nodata: -9999",
                "  citation: Demo fixture only; replace with exact JPL/PO.DAAC/NASA citation for real GRACE data.",
                "preprocessing:",
                "  nodata: Fill nodata via configured missing-data handling before detector runs.",
                "  notes: Download-free fixture for CI and workflow demonstration.",
                "mask:",
                "  method: Threshold cells below -3 cm equivalent water thickness.",
                "  provenance: Weak label derived from the same demo raster, not independent ground truth.",
                "  independent: false",
                "  weak_label_warning: This threshold mask is software validation only.",
                "limitations:",
                "  - Demo fixture is not real GRACE data.",
                "  - Weak label mask is derived from the validation grid.",
                "  - Use only to check workflow mechanics.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return grid_path, mask_path, manifest_path


def make_grace_demo(args):
    output_dir = Path(args.output)
    inputs_dir = output_dir / "inputs"
    grid_path, mask_path, manifest_path = write_grace_like_demo_inputs(inputs_dir)
    run_args = argparse.Namespace(
        seeds="1",
        detectors=["z_score", "dbscan", "isolation_forest"],
        output=str(output_dir / "report"),
        sweep=False,
        no_best_config_rerun=True,
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
        spatial_folds=args.spatial_folds,
    )
    results = run(run_args)
    return {
        "inputs_dir": str(inputs_dir),
        "report_dir": str(output_dir / "report"),
        "report_html": str(output_dir / "report" / "report.html"),
        "summary": results["summary"],
    }


def build_config(args=None):
    args = args or argparse.Namespace()
    experiment = load_yaml(CONFIG_DIR / "experiment.yaml")
    simulation = load_yaml(CONFIG_DIR / "simulation_config.yaml")["simulation"]
    sensor_config = load_yaml(CONFIG_DIR / "sensor_model.yaml")["sensors"]
    detection_config = load_yaml(CONFIG_DIR / "anomaly_detection_config.yaml")
    base_seed = simulation.get("random_seed", 42)
    default_seeds = simulation.get("batch_seeds", [base_seed + offset for offset in range(5)])
    seeds = parse_seed_spec(getattr(args, "seeds", None), default_seeds)
    detectors = getattr(args, "detectors", None)
    variants = detector_variants(detection_config, detectors=detectors, sweep=getattr(args, "sweep", False))
    detection_config_snapshot = deepcopy(detection_config)
    return experiment, simulation, sensor_config, detection_config_snapshot, variants, seeds


def run(args=None):
    experiment, simulation, sensor_config, detection_config, variants, batch_seeds = build_config(args)
    output_dir = Path(getattr(args, "output", "outputs") if args else "outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_grid = validation_mask = validation_metadata = validation_anomalies = None
    validation_source = getattr(args, "validation_grid", None) if args else None
    if validation_source:
        validation_grid, validation_mask, validation_metadata, _, validation_anomalies = prepare_validation_data(args)
        batch_seeds = batch_seeds[:1]

    results = build_results(
        experiment,
        simulation,
        sensor_config,
        detection_config,
        variants,
        batch_seeds,
        output_dir,
        args,
        validation_source=validation_source,
        validation_grid=validation_grid,
        validation_mask=validation_mask,
        validation_anomalies=validation_anomalies,
        validation_metadata=validation_metadata,
    )
    write_output_bundle(results, output_dir)
    if getattr(args, "sweep", False) and not getattr(args, "no_best_config_rerun", False):
        best_results = run_best_config_experiment(
            results,
            experiment,
            simulation,
            sensor_config,
            detection_config,
            batch_seeds,
            output_dir,
            args,
            validation_source=validation_source,
            validation_grid=validation_grid,
            validation_mask=validation_mask,
            validation_anomalies=validation_anomalies,
            validation_metadata=validation_metadata,
        )
        results["best_config_output_dir"] = best_results["output_dir"]
        results["best_config_summary"] = best_results["summary"]
        write_output_bundle(results, output_dir)
    print(json.dumps({"output_dir": str(output_dir), "summary": results["summary"]}, indent=2))
    return results


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run quantum-sensing Earth anomaly detection experiments.")
    subparsers = parser.add_subparsers(dest="command")
    doctor_parser = subparsers.add_parser("doctor", help="Validate a GRACE/real-data validation manifest before running.")
    doctor_parser.add_argument("--manifest", required=True, help="validation_manifest.yaml to inspect.")
    demo_parser = subparsers.add_parser("make-grace-demo", help="Generate a download-free GRACE-like GeoTIFF demo and report.")
    demo_parser.add_argument("--output", default="outputs/grace_demo", help="Output directory for demo inputs and report.")
    demo_parser.add_argument("--spatial-folds", type=int, default=4, help="Spatial folds for the demo report.")
    parser.add_argument("--seeds", help="Seed count, comma list, or inclusive range. Examples: 100, 42,43,44, 42-46")
    parser.add_argument("--detectors", nargs="+", choices=["z_score", "isolation_forest", "dbscan"], help="Detector algorithms to run.")
    parser.add_argument("--output", default="outputs", help="Output directory for reports and artifacts.")
    parser.add_argument("--sweep", action="store_true", help="Run simple parameter sweeps for configured detectors.")
    parser.add_argument("--no-best-config-rerun", action="store_true", help="Skip the automatic best-config rerun after a sweep.")
    parser.add_argument("--validation-grid", help="Optional validation gravity grid as .csv, .npy, .tif, or .tiff.")
    parser.add_argument("--validation-mask", help="Optional validation anomaly mask as .csv or .npy.")
    parser.add_argument("--validation-manifest", help="Optional validation_manifest.yaml with provenance and citation metadata.")
    parser.add_argument("--validation-anomalies", help="Optional JSON list of validation anomaly objects with center, sigma, depth, and intensity.")
    parser.add_argument("--missing", default="median", choices=["none", "zero", "median", "mean"], help="Missing-data handling for validation grids.")
    parser.add_argument("--preprocess-detrend", action="store_true", help="Remove a fitted planar trend from validation grids.")
    parser.add_argument("--preprocess-normalize", choices=["none", "zscore", "standardize", "minmax"], help="Normalize validation grids before sensor simulation.")
    parser.add_argument("--preprocess-clip", help="Clip validation grid values as low,high before normalization.")
    parser.add_argument("--calibrate-thresholds", action="store_true", help="Calibrate detector parameters using the validation mask or target false-positive rate.")
    parser.add_argument("--target-fpr", type=float, help="Target false-positive rate for detector calibration.")
    parser.add_argument(
        "--calibration-split",
        default="none",
        choices=["none", "left-right", "top-bottom"],
        help="Tune detectors on one validation region and report metrics on a held-out region.",
    )
    parser.add_argument("--spatial-folds", type=int, default=1, help="Use k-fold spatial calibration/evaluation splits when calibrating detectors.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if getattr(args, "command", None) == "doctor":
        result = doctor_manifest(args.manifest)
        print(json.dumps(result, indent=2))
        return result
    if getattr(args, "command", None) == "make-grace-demo":
        result = make_grace_demo(args)
        print(json.dumps(result, indent=2))
        return result
    return run(args)


if __name__ == "__main__":
    main()
