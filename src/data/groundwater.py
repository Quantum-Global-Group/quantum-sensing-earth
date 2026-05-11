from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.artifacts import normalize_month_key, write_csv


GROUNDWATER_SCHEMA_COLUMNS = [
    "site_id",
    "site_name",
    "source",
    "latitude",
    "longitude",
    "basin_id",
    "basin_name",
    "date",
    "month",
    "value",
    "value_units",
    "measurement_type",
    "quality_flag",
    "source_url",
]
RAW_GROUNDWATER_COLUMNS = [
    "raw_value",
    "raw_value_column",
    "raw_date",
    "raw_measurement_type",
    "raw_units",
    "raw_source_file",
]

ALIASES = {
    "site_id": ["site_id", "site code", "site_code", "station_id", "station id", "well_id", "well id", "station"],
    "site_name": ["site_name", "site name", "station_name", "station name", "well_name", "well name"],
    "source": ["source", "data_source", "agency"],
    "latitude": ["latitude", "lat", "y", "station_latitude"],
    "longitude": ["longitude", "lon", "long", "x", "station_longitude"],
    "basin_id": ["basin_id", "basin id", "basin_number", "basin_subbasin_number"],
    "basin_name": ["basin_name", "basin name", "basin_subbasin_name"],
    "date": ["date", "measurement_date", "measurement date", "msmt_date", "msmt date", "datetime", "time"],
    "value": [
        "value",
        "groundwater_level",
        "groundwater level",
        "groundwater_elevation",
        "groundwater elevation",
        "water_surface_elevation",
        "water surface elevation",
        "depth_to_water",
        "depth to water",
        "rpe_wse",
        "wse",
        "gwe",
        "wlm_rpe",
        "msmt_value",
        "measurement_value",
    ],
    "value_units": ["value_units", "units", "unit", "measurement_units", "measurement units"],
    "measurement_type": ["measurement_type", "measurement type", "parameter", "parameter_name", "type"],
    "quality_flag": ["quality_flag", "quality flag", "quality", "qa_flag", "status"],
    "source_url": ["source_url", "source url", "url"],
}


def canonical_header(name: str) -> str:
    return str(name).strip().lower().replace("-", "_").replace("/", "_")


def column_lookup(columns: list[str]) -> dict[str, str]:
    normalized = {canonical_header(column): column for column in columns}
    lookup: dict[str, str] = {}
    for target, aliases in ALIASES.items():
        candidates = [canonical_header(alias) for alias in aliases]
        for candidate in candidates:
            if candidate in normalized:
                lookup[target] = normalized[candidate]
                break
    return lookup


def normalize_groundwater_dataframe(
    frame: pd.DataFrame,
    source: str = "dwr-periodic",
    source_url: str | None = None,
    source_file: str | None = None,
) -> pd.DataFrame:
    lookup = column_lookup(list(frame.columns))
    rows: dict[str, Any] = {}
    for column in GROUNDWATER_SCHEMA_COLUMNS:
        raw = lookup.get(column)
        rows[column] = frame[raw] if raw else None
    normalized = pd.DataFrame(rows)
    normalized["source"] = normalized["source"].fillna(source)
    normalized["site_name"] = normalized["site_name"].fillna(normalized["site_id"])
    normalized["value_units"] = normalized["value_units"].fillna("unknown")
    normalized["measurement_type"] = normalized["measurement_type"].fillna(infer_measurement_type(lookup.get("value", "")))
    normalized["quality_flag"] = normalized["quality_flag"].fillna("")
    normalized["source_url"] = normalized["source_url"].fillna(source_url or source_file or "")
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
    normalized["month"] = normalized["date"].map(normalize_month_key)
    normalized["value"] = pd.to_numeric(normalized["value"], errors="coerce")
    normalized["latitude"] = pd.to_numeric(normalized["latitude"], errors="coerce")
    normalized["longitude"] = pd.to_numeric(normalized["longitude"], errors="coerce")
    value_col = lookup.get("value")
    date_col = lookup.get("date")
    type_col = lookup.get("measurement_type")
    units_col = lookup.get("value_units")
    normalized["raw_value"] = frame[value_col] if value_col else None
    normalized["raw_value_column"] = value_col or ""
    normalized["raw_date"] = frame[date_col] if date_col else None
    normalized["raw_measurement_type"] = frame[type_col] if type_col else normalized["measurement_type"]
    normalized["raw_units"] = frame[units_col] if units_col else normalized["value_units"]
    normalized["raw_source_file"] = source_file or source_url or ""
    return normalized[GROUNDWATER_SCHEMA_COLUMNS + RAW_GROUNDWATER_COLUMNS]


def normalize_groundwater_observations(path: Path, source: str = "dwr-periodic") -> pd.DataFrame:
    source_path = Path(path)
    frame = pd.read_csv(source_path)
    return normalize_groundwater_dataframe(frame, source=source, source_url=str(source_path), source_file=str(source_path))


def infer_measurement_type(value_column: str) -> str:
    text = canonical_header(value_column)
    if "depth" in text or "wlm" in text:
        return "depth_to_water"
    if "elev" in text or "wse" in text or "gwe" in text:
        return "groundwater_elevation"
    return "groundwater_level"


def validate_groundwater_observations(frame: pd.DataFrame) -> dict[str, list[str]]:
    required = ["site_id", "latitude", "longitude", "date", "month", "value"]
    errors = []
    warnings = []
    for column in required:
        if column not in frame.columns:
            errors.append(f"Missing required column: {column}")
        elif frame[column].isna().all():
            errors.append(f"Column has no usable values: {column}")
    if "basin_id" not in frame.columns or frame["basin_id"].isna().all():
        warnings.append("No basin_id values provided; observations must be spatially joined to basin polygons.")
    if "value_units" in frame and frame["value_units"].fillna("unknown").eq("unknown").all():
        warnings.append("Groundwater value units are unknown; provenance should define feet, meters, or elevation datum.")
    return {"errors": errors, "warnings": warnings}


def load_geojson_features(path: Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    features = []
    for index, feature in enumerate(payload.get("features", []), start=1):
        props = feature.get("properties") or {}
        features.append(
            {
                "basin_id": str(props.get("basin_id") or props.get("Basin_Subbasin_Number") or props.get("Basin_Number") or f"basin_{index}"),
                "basin_name": str(props.get("name") or props.get("basin_name") or props.get("Basin_Subbasin_Name") or props.get("Basin_Name") or f"Basin {index}"),
                "geometry": feature.get("geometry") or {},
            }
        )
    if not features:
        raise ValueError(f"No GeoJSON features found in {path}")
    return features


def ring_contains_point(ring: list[list[float]], lon: float, lat: float) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    x1, y1 = ring[-1][0], ring[-1][1]
    for point in ring:
        x2, y2 = point[0], point[1]
        crosses = (y1 > lat) != (y2 > lat)
        if crosses:
            x_intersect = (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1
            if lon < x_intersect:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def polygon_contains_point(polygon: list[Any], lon: float, lat: float) -> bool:
    if not polygon:
        return False
    outer = polygon[0]
    holes = polygon[1:]
    if not ring_contains_point(outer, lon, lat):
        return False
    return not any(ring_contains_point(hole, lon, lat) for hole in holes)


def geometry_contains_point(geometry: dict[str, Any], lon: float, lat: float) -> bool:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geometry_type == "Polygon":
        return polygon_contains_point(coordinates, lon, lat)
    if geometry_type == "MultiPolygon":
        return any(polygon_contains_point(polygon, lon, lat) for polygon in coordinates)
    return False


def assign_observations_to_basins(frame: pd.DataFrame, basins_path: Path) -> pd.DataFrame:
    features = load_geojson_features(basins_path)
    assigned = frame.copy()
    for idx, row in assigned.iterrows():
        if pd.notna(row.get("basin_id")) and str(row.get("basin_id")).strip():
            continue
        lon = row.get("longitude")
        lat = row.get("latitude")
        if not np.isfinite(lon) or not np.isfinite(lat):
            continue
        for feature in features:
            if geometry_contains_point(feature["geometry"], float(lon), float(lat)):
                assigned.at[idx, "basin_id"] = feature["basin_id"]
                assigned.at[idx, "basin_name"] = feature["basin_name"]
                break
    return assigned


def is_depth_measurement(measurement_type: Any) -> bool:
    return "depth" in str(measurement_type).lower()


def aggregate_groundwater_monthly(frame: pd.DataFrame) -> pd.DataFrame:
    usable = frame.dropna(subset=["basin_id", "month", "value"]).copy()
    if usable.empty:
        return pd.DataFrame()
    grouped = (
        usable.groupby(["basin_id", "basin_name", "month", "value_units", "measurement_type"], dropna=False)
        .agg(
            groundwater_monthly_mean=("value", "mean"),
            groundwater_monthly_min=("value", "min"),
            groundwater_monthly_max=("value", "max"),
            observation_count=("value", "count"),
            site_count=("site_id", pd.Series.nunique),
        )
        .reset_index()
    )
    grouped["basin_baseline"] = grouped.groupby(["basin_id", "measurement_type"], dropna=False)["groundwater_monthly_mean"].transform("mean")
    raw_anomaly = grouped["groundwater_monthly_mean"] - grouped["basin_baseline"]
    sign = grouped["measurement_type"].map(lambda value: -1.0 if is_depth_measurement(value) else 1.0)
    grouped["groundwater_level_anomaly"] = raw_anomaly * sign
    grouped["anomaly_sign_convention"] = grouped["measurement_type"].map(
        lambda value: "positive means shallower water table / more groundwater" if is_depth_measurement(value) else "positive means higher groundwater elevation"
    )
    return grouped


def safe_corr(x_values: list[float], y_values: list[float], minimum: int = 3) -> float | None:
    pairs = [(x, y) for x, y in zip(x_values, y_values) if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < minimum:
        return None
    x = np.asarray([pair[0] for pair in pairs], dtype=float)
    y = np.asarray([pair[1] for pair in pairs], dtype=float)
    if np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def trend_agreement(x_values: list[float], y_values: list[float], minimum: int = 3) -> float | None:
    pairs = [(x, y) for x, y in zip(x_values, y_values) if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < minimum:
        return None
    x = np.asarray([pair[0] for pair in pairs], dtype=float)
    y = np.asarray([pair[1] for pair in pairs], dtype=float)
    return float(np.mean(np.sign(np.diff(x)) == np.sign(np.diff(y))))


def sign_agreement(x_values: list[float], y_values: list[float], minimum: int = 3) -> float | None:
    pairs = [(x, y) for x, y in zip(x_values, y_values) if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < minimum:
        return None
    return float(np.mean([np.sign(x) == np.sign(y) for x, y in pairs]))


def groundwater_validation_metrics(basin_metrics: pd.DataFrame, groundwater_monthly: pd.DataFrame) -> pd.DataFrame:
    if basin_metrics.empty or groundwater_monthly.empty:
        return pd.DataFrame()
    basin = basin_metrics.copy()
    groundwater = groundwater_monthly.copy()
    basin["month"] = basin["month"].map(normalize_month_key)
    groundwater["month"] = groundwater["month"].map(normalize_month_key)
    merged = basin.merge(
        groundwater,
        on=["basin_id", "month"],
        how="inner",
        suffixes=("", "_groundwater"),
    )
    if "basin_name_groundwater" in merged.columns:
        merged["basin_name"] = merged["basin_name"].fillna(merged["basin_name_groundwater"])
    rows = []
    group_cols = ["basin_id", "threshold"]
    for (basin_id, threshold), group in merged.groupby(group_cols, dropna=False, sort=True):
        group = group.sort_values("month")
        valid = group[["grace_mean_cm", "groundwater_level_anomaly"]].dropna()
        valid_months = int(len(valid))
        grace = group["grace_mean_cm"].astype(float).tolist()
        groundwater = group["groundwater_level_anomaly"].astype(float).tolist()
        rows.append(
            {
                "basin_id": basin_id,
                "basin_name": group["basin_name"].iloc[0],
                "threshold": int(threshold) if pd.notna(threshold) else None,
                "months": int(group["month"].nunique()),
                "valid_months": valid_months,
                "status": "ok" if valid_months >= 3 else "insufficient_months",
                "observation_count": int(group["observation_count"].sum()),
                "site_count": int(group["site_count"].max()) if group["site_count"].notna().any() else 0,
                "mean_grace_cm": float(np.nanmean(group["grace_mean_cm"])) if group["grace_mean_cm"].notna().any() else None,
                "mean_gldas_cm": float(np.nanmean(group["gldas_mean_cm"])) if "gldas_mean_cm" in group and group["gldas_mean_cm"].notna().any() else None,
                "mean_usdm_drought_coverage_pct": float(np.nanmean(group["usdm_drought_coverage_pct"])) if group["usdm_drought_coverage_pct"].notna().any() else None,
                "mean_groundwater_value": float(np.nanmean(group["groundwater_monthly_mean"])) if group["groundwater_monthly_mean"].notna().any() else None,
                "mean_groundwater_anomaly": float(np.nanmean(group["groundwater_level_anomaly"])) if group["groundwater_level_anomaly"].notna().any() else None,
                "value_units": group["value_units"].dropna().iloc[0] if group["value_units"].notna().any() else "unknown",
                "measurement_type": group["measurement_type"].dropna().iloc[0] if group["measurement_type"].notna().any() else "groundwater_level",
                "grace_groundwater_correlation": safe_corr(grace, groundwater),
                "grace_groundwater_lag1_correlation": safe_corr(grace[:-1], groundwater[1:]) if len(grace) > 3 else None,
                "grace_groundwater_lag2_correlation": safe_corr(grace[:-2], groundwater[2:]) if len(grace) > 4 else None,
                "grace_groundwater_trend_agreement": trend_agreement(grace, groundwater),
                "grace_groundwater_sign_agreement": sign_agreement(grace, groundwater),
            }
        )
    return pd.DataFrame(rows)


@dataclass
class GroundwaterTrackResult:
    observations: pd.DataFrame
    monthly: pd.DataFrame
    metrics: pd.DataFrame
    summary: dict[str, Any]


def write_groundwater_track(
    output_dir: Path,
    observations_path: Path,
    basins_path: Path,
    basin_metrics_path: Path,
    source: str = "dwr-periodic",
) -> GroundwaterTrackResult:
    output_dir = Path(output_dir)
    observations = normalize_groundwater_observations(observations_path, source=source)
    if observations["basin_id"].isna().all():
        observations = assign_observations_to_basins(observations, basins_path)
    validation = validate_groundwater_observations(observations)
    observations_csv = output_dir / "groundwater_observations.csv"
    observations.to_csv(observations_csv, index=False)

    monthly = aggregate_groundwater_monthly(observations)
    monthly_csv = output_dir / "groundwater_basin_monthly.csv"
    monthly.to_csv(monthly_csv, index=False)

    basin_metrics = pd.read_csv(basin_metrics_path) if Path(basin_metrics_path).exists() else pd.DataFrame()
    metrics = groundwater_validation_metrics(basin_metrics, monthly)
    metrics_csv = output_dir / "groundwater_validation_metrics.csv"
    metrics.to_csv(metrics_csv, index=False)

    summary_rows = metrics.to_dict("records") if not metrics.empty else []
    summary_csv = output_dir / "groundwater_validation_summary.csv"
    write_csv(summary_csv, summary_rows)
    valid_rows = metrics[metrics["status"].eq("ok")] if not metrics.empty else pd.DataFrame()
    summary = {
        "schema_version": "groundwater-validation-v1",
        "status": "ok" if not valid_rows.empty else ("insufficient_months" if not metrics.empty else "no_groundwater_overlap"),
        "source": source,
        "observations_path": str(observations_path),
        "basins_path": str(basins_path),
        "basin_metrics_path": str(basin_metrics_path),
        "observation_rows": int(len(observations)),
        "groundwater_months": sorted(month for month in monthly["month"].dropna().astype(str).unique()) if not monthly.empty else [],
        "basin_month_rows": int(len(monthly)),
        "valid_basin_threshold_rows": int(len(valid_rows)),
        "insufficient_basin_threshold_rows": int(len(metrics) - len(valid_rows)) if not metrics.empty else 0,
        "metrics_csv": str(metrics_csv),
        "summary_csv": str(summary_csv),
        "observations_csv": str(observations_csv),
        "monthly_csv": str(monthly_csv),
        "validation": validation,
        "claim_note": "Groundwater validation has begun, but groundwater discovery is not proven and quantum advantage is not claimed.",
    }
    (output_dir / "groundwater_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "groundwater_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return GroundwaterTrackResult(observations=observations, monthly=monthly, metrics=metrics, summary=summary)
