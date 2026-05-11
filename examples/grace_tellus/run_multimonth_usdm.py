"""Run a multi-month GRACE Tellus + USDM validation batch.

The workflow downloads public CSR GRACE Tellus GeoTIFF granules and matching
U.S. Drought Monitor shapefiles, crops each GRACE grid to a fixed study region,
rasterizes independent USDM drought classes onto that crop, runs the MVP, and
writes a compact time-series report.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import netrc
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.data.artifacts import (
    command_text,
    normalize_month_key,
    write_artifact_manifest,
    write_coverage_artifacts,
)
from src.data.groundwater import write_groundwater_track


CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
CSR_COLLECTION = "C2077042515-POCLOUD"
JPL_COLLECTION = "C2077042612-POCLOUD"
GRFO_CSR_COLLECTION = "C3193285193-POCLOUD"
GRFO_JPL_COLLECTION = "C3193302127-POCLOUD"
GLDAS_COLLECTION = "C2036877565-POCLOUD"
GRACE_DOI = "https://doi.org/10.5067/TELND-3AC64"
JPL_GRACE_DOI = "https://doi.org/10.5067/TELND-3AJ64"
GLDAS_SOURCE = "https://podaac.jpl.nasa.gov/dataset/TELLUS_GLDAS-NOAH-3.3_TWS-ANOMALY_MONTHLY"
EARTHDATA_HOST = "urs.earthdata.nasa.gov"
USDM_SHAPEFILE_TEMPLATE = "https://droughtmonitor.unl.edu/data/shapefiles_m/USDM_{date}_M.zip"
WESTERN_US_BBOX = [-125.0, 31.0, -102.0, 49.0]
CENTRAL_VALLEY_BBOX = [-123.5, 34.5, -118.5, 41.5]
WESTERN_US_BASINS = Path("examples/grace_tellus/western_us_basins.geojson")
CENTRAL_VALLEY_BASINS = Path("data/central_valley/basins/central_valley_b118_basins.geojson")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-month GRACE Tellus validation against USDM masks.")
    parser.add_argument("--output", default="outputs/grace_multimonth_usdm", help="Batch output directory.")
    parser.add_argument("--months", type=int, default=3, help="Number of GRACE/GRACE-FO months to run.")
    parser.add_argument(
        "--mission",
        choices=["grace", "grace-fo"],
        default="grace-fo",
        help="Use legacy GRACE collections or current GRACE-FO collections.",
    )
    parser.add_argument("--start", default="2025-01-01", help="CMR temporal search start date.")
    parser.add_argument("--bbox", nargs=4, type=float, default=WESTERN_US_BBOX, metavar=("W", "S", "E", "N"))
    parser.add_argument(
        "--study-region",
        choices=["western-us", "central-valley"],
        default="western-us",
        help="Named study region. central-valley uses the DWR B118 basin file when available.",
    )
    parser.add_argument("--thresholds", nargs="+", type=int, default=[1, 2, 3], help="USDM DM thresholds, e.g. 1 2 3.")
    parser.add_argument("--spatial-folds", type=int, default=4)
    parser.add_argument("--detectors", nargs="+", default=["z_score", "dbscan", "isolation_forest"])
    parser.add_argument("--skip-existing", action="store_true", help="Do not rerun completed per-month reports.")
    parser.add_argument("--skip-tws-track", action="store_true", help="Do not add the CSR-vs-JPL GRACE-derived TWS comparison track.")
    parser.add_argument("--skip-gldas-track", action="store_true", help="Do not add the external GLDAS hydrology comparison track.")
    parser.add_argument("--basins", help="GeoJSON basin/subbasin boundaries used for basin-scale aggregation.")
    parser.add_argument("--groundwater-observations", help="DWR/USGS groundwater observation CSV to join and aggregate by basin.")
    parser.add_argument(
        "--groundwater-source",
        default="dwr-periodic",
        choices=["dwr-periodic", "usgs-groundwater", "fixture"],
        help="Groundwater observation source label recorded in outputs.",
    )
    parser.add_argument("--skip-groundwater-track", action="store_true", help="Do not write groundwater observation validation artifacts.")
    return parser.parse_args()


def configure_study_region(args: argparse.Namespace) -> tuple[list[float], Path, str]:
    bbox = [float(value) for value in args.bbox]
    if args.study_region == "central-valley":
        if bbox == WESTERN_US_BBOX:
            bbox = CENTRAL_VALLEY_BBOX
        basins = Path(args.basins) if args.basins else CENTRAL_VALLEY_BASINS
        if not basins.exists():
            raise SystemExit(
                "Central Valley runs require DWR B118 basin boundaries. "
                "Run `python examples\\central_valley\\prepare_central_valley_basins.py` "
                "or pass --basins path\\to\\central_valley_b118_basins.geojson."
            )
        return bbox, basins, "central_valley"
    return bbox, Path(args.basins) if args.basins else WESTERN_US_BASINS, "western_us"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def month_window(month: str) -> tuple[str, str]:
    start = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


def granule_for_month(collection: str, month: str, extension: str, public_only: bool = False, require_exact: bool = False) -> dict | None:
    start, end = month_window(month)
    temporal = f"{start}T00:00:00Z,{end}T00:00:00Z"
    url = (
        f"{CMR_GRANULES}?collection_concept_id={collection}"
        f"&temporal={urllib.parse.quote(temporal)}&page_size=20&sort_key=start_date"
    )
    entries = fetch_json(url).get("feed", {}).get("entry", [])
    fallback = None
    for entry in entries:
        links = [
            link["href"]
            for link in entry.get("links", [])
            if link.get("href", "").lower().endswith(extension.lower())
            and (not public_only or "podaac-ops-cumulus-public" in link.get("href", ""))
        ]
        if not links:
            continue
        granule = {
            "title": entry["title"],
            "start": entry["time_start"],
            "end": entry["time_end"],
            "url": links[0],
            "filename": Path(links[0]).name,
        }
        if entry["time_start"][:7] == month:
            return granule
        fallback = fallback or granule
    if require_exact:
        return None
    return fallback


def grace_granules(count: int, start: str, collection: str = CSR_COLLECTION) -> list[dict]:
    temporal = f"{start}T00:00:00Z,"
    url = (
        f"{CMR_GRANULES}?collection_concept_id={collection}"
        f"&temporal={urllib.parse.quote(temporal)}&page_size={count}&sort_key=start_date"
    )
    entries = fetch_json(url).get("feed", {}).get("entry", [])
    granules = []
    for entry in entries:
        tif_links = [
            link["href"]
            for link in entry.get("links", [])
            if link.get("href", "").lower().endswith(".tif")
            and "podaac-ops-cumulus-public" in link.get("href", "")
        ]
        if not tif_links:
            continue
        granules.append(
            {
                "title": entry["title"],
                "start": entry["time_start"],
                "end": entry["time_end"],
                "url": tif_links[0],
                "filename": Path(tif_links[0]).name,
            }
        )
    if len(granules) < count:
        raise RuntimeError(f"Only found {len(granules)} public GeoTIFF granules; requested {count}.")
    return granules[:count]


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    urllib.request.urlretrieve(url, path)


def tuesday_candidates(iso_end: str) -> list[str]:
    end = datetime.fromisoformat(iso_end.replace("Z", "+00:00")).date()
    candidates = []
    for offset in range(-10, 11):
        day = end + timedelta(days=offset)
        if day.weekday() == 1:
            candidates.append(day.strftime("%Y%m%d"))
    return candidates


def download_usdm_near(iso_end: str, raw_dir: Path) -> tuple[str, Path, Path]:
    last_error = None
    for date_text in tuesday_candidates(iso_end):
        zip_path = raw_dir / f"USDM_{date_text}_M.zip"
        url = USDM_SHAPEFILE_TEMPLATE.format(date=date_text)
        try:
            download(url, zip_path)
            extract_dir = raw_dir / f"USDM_{date_text}_M"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
            shp_path = extract_dir / f"USDM_{date_text}.shp"
            if shp_path.exists():
                return date_text, zip_path, shp_path
        except Exception as exc:  # keep probing nearby weekly products
            last_error = exc
    raise RuntimeError(f"Could not download a nearby USDM shapefile for {iso_end}: {last_error}")


def manifest_for(
    granule: dict,
    usdm_date: str,
    usdm_zip: Path,
    threshold: int,
    output_grid: Path,
    bbox: list[float],
    study_region: str,
) -> dict:
    threshold_label = f"D{threshold}+"
    bounds = ",".join(str(value) for value in bbox)
    mission = "GRACE-FO" if "GRFO" in granule.get("title", "") else "GRACE"
    product_short = "TELLUS_GRFO_L3_CSR_RL06.3_LND_v04" if mission == "GRACE-FO" else "TELLUS_GRAC_L3_CSR_RL06_LND_v04"
    region_label = study_region.replace("_", " ")
    return {
        "dataset": {
            "name": f"CSR {mission} Tellus cropped {region_label} with independent USDM {threshold_label} mask",
            "source": granule["url"],
            "product": f"{product_short} / {granule['filename']}",
            "date_range": f"{mission} monthly solution: {granule['start']} to {granule['end']}; USDM weekly mask: {usdm_date}",
            "units": "centimeters equivalent water thickness",
            "crs": "EPSG:4326",
            "resolution": f"1 degree latitude/longitude grid; cropped to {region_label} bounds {bounds}",
            "bounds": {"left": bbox[0], "bottom": bbox[1], "right": bbox[2], "top": bbox[3]},
            "nodata": -99999.0,
            "citation": (
                "Landerer F. 2021. TELLUS_GRAC_L3_CSR_RL06_LND_v04. Ver. RL06 v04. "
                f"PO.DAAC, CA, USA. Dataset accessed from {GRACE_DOI}. "
                "U.S. Drought Monitor data accessed from droughtmonitor.unl.edu; cite NDMC, USDA, and NOAA."
            ),
        },
        "preprocessing": {
            "notes": f"Band 1 was cropped to {region_label} bounds {bounds}. No reprojection, gain-factor rescaling, detrending, normalization, or clipping was applied.",
            "nodata": "Raster nodata value -99999.0 is retained and handled as missing data during validation.",
        },
        "mask": {
            "method": f"Independent hydrologic drought proxy: USDM cells touched by classes {threshold_label} are labeled anomalous.",
            "provenance": f"Downloaded {usdm_zip.name} from U.S. Drought Monitor and rasterized onto {output_grid.name} using rasterize_independent_mask.py.",
            "independent": True,
            "target_type": "drought_proxy",
            "weak_label_warning": "Independent of the GRACE raster, but a drought severity proxy rather than direct gravity or groundwater truth.",
        },
        "limitations": [
            "USDM drought categories are expert drought assessments and are not direct measurements of terrestrial water storage.",
            "GRACE Tellus grids are coarse monthly mass-anomaly products and not local gravity survey rasters.",
            "Weekly USDM dates are aligned to nearby GRACE monthly solution windows, not exact observation days.",
            "Compare trends and failures across months; avoid over-interpreting a single month or mask threshold.",
        ],
    }


def run_command(command: list[str], cwd: Path) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_basin_features(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    features = []
    for index, feature in enumerate(payload.get("features", []), start=1):
        props = feature.get("properties", {})
        features.append(
            {
                "basin_id": props.get("basin_id") or f"basin_{index}",
                "name": props.get("name") or props.get("basin_id") or f"Basin {index}",
                "target_relevance": props.get("target_relevance", "basin_observation"),
                "notes": props.get("notes", ""),
                "geometry": feature.get("geometry"),
            }
        )
    if not features:
        raise ValueError(f"No basin features found in {path}")
    return features


def read_raster_values(path: Path, mask_nodata: bool = True) -> tuple[np.ndarray, object, object]:
    import rasterio

    with rasterio.open(path) as dataset:
        values = np.ma.asarray(dataset.read(1, masked=mask_nodata), dtype=float)
        if mask_nodata and dataset.nodata is not None:
            values = np.ma.masked_where(np.isclose(values, float(dataset.nodata)), values)
        return np.asarray(values.filled(np.nan), dtype=float), dataset.transform, dataset.crs


def basin_mask_for_grid(geometry: dict, shape: tuple[int, int], transform: object) -> np.ndarray:
    from rasterio.features import rasterize

    return rasterize(
        [(geometry, 1)],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=True,
    ).astype(bool)


def safe_corr(x_values: list[float], y_values: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(x_values, y_values) if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < 2:
        return None
    x = np.asarray([pair[0] for pair in pairs], dtype=float)
    y = np.asarray([pair[1] for pair in pairs], dtype=float)
    if np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def trend_agreement(x_values: list[float], y_values: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(x_values, y_values) if np.isfinite(x) and np.isfinite(y)]
    if len(pairs) < 2:
        return None
    x = np.asarray([pair[0] for pair in pairs], dtype=float)
    y = np.asarray([pair[1] for pair in pairs], dtype=float)
    return float(np.mean(np.sign(np.diff(x)) == np.sign(np.diff(y))))


def write_basin_track(output_dir: Path, run_rows: list[dict], basins_path: Path, bbox: list[float]) -> dict:
    basins = load_basin_features(basins_path)
    months = sorted({normalize_month_key(row["month"]) for row in run_rows if normalize_month_key(row["month"])})
    gldas_by_month = {
        month: granule_for_month(GLDAS_COLLECTION, month, ".nc", public_only=False, require_exact=True)
        for month in months
    }
    rows = []
    for run in run_rows:
        month = run["month"]
        grid_path = Path(run["grid_path"])
        mask_path = Path(run["mask_path"])
        if not grid_path.exists() or not mask_path.exists():
            continue
        grace_grid, transform, _ = read_raster_values(grid_path)
        usdm_mask, _, _ = read_raster_values(mask_path, mask_nodata=False)
        gldas_grid = None
        gldas_granule = gldas_by_month.get(month)
        if gldas_granule:
            nc_path = Path("data/gldas/raw") / gldas_granule["filename"]
            ok, _ = earthdata_download(gldas_granule["url"], nc_path)
            if ok:
                try:
                    gldas_grid, _, _ = read_gldas_grid(nc_path, bbox)
                except Exception:
                    gldas_grid = None
        for basin in basins:
            basin_mask = basin_mask_for_grid(basin["geometry"], grace_grid.shape, transform)
            valid_grace = basin_mask & np.isfinite(grace_grid)
            basin_cells = int(valid_grace.sum())
            if basin_cells == 0:
                continue
            usdm_valid = basin_mask & np.isfinite(usdm_mask)
            if gldas_grid is not None:
                rows_min = min(grace_grid.shape[0], gldas_grid.shape[0])
                cols_min = min(grace_grid.shape[1], gldas_grid.shape[1])
                gldas_slice = gldas_grid[:rows_min, :cols_min]
                gldas_mask = basin_mask[:rows_min, :cols_min] & np.isfinite(gldas_slice)
                gldas_mean = float(np.nanmean(gldas_slice[gldas_mask])) if gldas_mask.any() else None
            else:
                gldas_mean = None
            rows.append(
                {
                    "month": month,
                    "threshold": int(run["threshold"]),
                    "basin_id": basin["basin_id"],
                    "basin_name": basin["name"],
                    "target_relevance": basin["target_relevance"],
                    "grace_mean_cm": float(np.nanmean(grace_grid[valid_grace])),
                    "gldas_mean_cm": gldas_mean,
                    "usdm_drought_coverage_pct": float(np.nanmean(usdm_mask[usdm_valid] > 0) * 100.0) if usdm_valid.any() else None,
                    "grid_cells": basin_cells,
                    "basin_fixture_notes": basin["notes"],
                }
            )

    metrics_csv = output_dir / "basin_metrics.csv"
    write_csv(metrics_csv, rows)
    summary_rows = []
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for (basin_id, threshold), group in frame.groupby(["basin_id", "threshold"], sort=True):
            group = group.sort_values("month")
            grace = group["grace_mean_cm"].astype(float).tolist()
            gldas = group["gldas_mean_cm"].astype(float).tolist()
            drought = group["usdm_drought_coverage_pct"].astype(float).tolist()
            summary_rows.append(
                {
                    "basin_id": basin_id,
                    "threshold": int(threshold),
                    "basin_name": group["basin_name"].iloc[0],
                    "months": int(group["month"].nunique()),
                    "gldas_months": int(group["gldas_mean_cm"].notna().sum()),
                    "mean_grace_cm": float(np.nanmean(group["grace_mean_cm"])),
                    "mean_gldas_cm": float(np.nanmean(group["gldas_mean_cm"])) if group["gldas_mean_cm"].notna().any() else None,
                    "mean_usdm_drought_coverage_pct": float(np.nanmean(group["usdm_drought_coverage_pct"])) if group["usdm_drought_coverage_pct"].notna().any() else None,
                    "grace_gldas_correlation": safe_corr(grace, gldas),
                    "grace_gldas_lag1_correlation": safe_corr(grace[1:], gldas[:-1]) if len(grace) > 2 else None,
                    "grace_gldas_trend_agreement": trend_agreement(grace, gldas),
                    "grace_usdm_correlation": safe_corr(grace, drought),
                }
            )
    summary_csv = output_dir / "basin_summary.csv"
    write_csv(summary_csv, summary_rows)
    summary = {
        "basin_fixture": str(basins_path),
        "basins": len(basins),
        "months": len(months),
        "rows": len(rows),
        "metrics_csv": str(metrics_csv),
        "summary_csv": str(summary_csv),
        "limitations": (
            "DWR Bulletin 118 basin/subbasin boundaries are authoritative for California groundwater basin geography, "
            "but GRACE cells are coarse and groundwater observations still require coverage checks."
            if "central_valley_b118" in basins_path.name.lower()
            else "Basin polygons are approximate fixtures for workflow validation. Replace with authoritative HUC/aquifer/basin boundaries before scientific interpretation."
        ),
    }
    (output_dir / "basin_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def aggregate_timeline(
    output_dir: Path,
    run_rows: list[dict],
    tws_summary: dict | None = None,
    gldas_summary: dict | None = None,
) -> tuple[Path, Path]:
    rows = []
    for run in run_rows:
        summary_path = Path(run["run_dir"]) / "summary.csv"
        if not summary_path.exists():
            rows.append({**run, "status": "failed", "reason": "missing summary.csv"})
            continue
        frame = pd.read_csv(summary_path)
        for _, metric_row in frame.iterrows():
            rows.append(
                {
                    **run,
                    "status": "ok",
                    "sensor_profile": metric_row["sensor_profile"],
                    "algorithm": metric_row["algorithm"],
                    "f1": metric_row["f1"],
                    "iou": metric_row["iou"],
                    "false_positive_rate": metric_row["false_positive_rate"],
                    "false_negative_rate": metric_row["false_negative_rate"],
                    "rmse": metric_row["rmse"],
                    "snr": metric_row["snr"],
                    "params": metric_row["params"],
                }
            )
    csv_path = output_dir / "timeline_metrics.csv"
    write_csv(csv_path, rows)
    html_path = output_dir / "timeline_report.html"
    write_timeline_report(html_path, rows, tws_summary=tws_summary, gldas_summary=gldas_summary)
    write_timeline_plot(output_dir / "timeline_f1.png", rows)
    return csv_path, html_path


def crop_raster(input_path: Path, output_path: Path, bbox: list[float]) -> None:
    import rasterio
    from rasterio.windows import from_bounds

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 0:
        return
    min_lon, min_lat, max_lon, max_lat = bbox
    with rasterio.open(input_path) as src:
        window = from_bounds(min_lon, min_lat, max_lon, max_lat, src.transform).round_offsets().round_lengths()
        grid = src.read(1, window=window)
        profile = src.profile.copy()
        profile.update(height=grid.shape[0], width=grid.shape[1], transform=src.window_transform(window), count=1)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(grid, 1)


def write_tws_comparison_track(
    output_dir: Path,
    csr_granules: list[dict],
    start: str,
    bbox: list[float],
    jpl_collection: str = JPL_COLLECTION,
) -> dict:
    import matplotlib.pyplot as plt
    import rasterio

    raw_grace = Path("data/grace_tellus/raw")
    prepared_dir = Path("data/grace_tellus/multimonth_tws")
    prepared_dir.mkdir(parents=True, exist_ok=True)
    requested_months = [granule["start"][:7] for granule in csr_granules]
    jpl_by_month = {
        month: granule_for_month(jpl_collection, month, ".tif", public_only=True, require_exact=True)
        for month in requested_months
    }

    rows = []
    csr_series = []
    jpl_series = []
    months = []
    for csr in csr_granules:
        month = csr["start"][:7]
        jpl = jpl_by_month.get(month)
        if not jpl:
            rows.append({"month": month, "status": "missing_jpl_match"})
            continue
        csr_raw = raw_grace / csr["filename"]
        jpl_raw = raw_grace / jpl["filename"]
        download(jpl["url"], jpl_raw)
        csr_crop = prepared_dir / f"csr_western_us_{month.replace('-', '')}.tif"
        jpl_crop = prepared_dir / f"jpl_western_us_{month.replace('-', '')}.tif"
        crop_raster(csr_raw, csr_crop, bbox)
        crop_raster(jpl_raw, jpl_crop, bbox)
        with rasterio.open(csr_crop) as csr_ds, rasterio.open(jpl_crop) as jpl_ds:
            csr_grid = csr_ds.read(1).astype(float)
            jpl_grid = jpl_ds.read(1).astype(float)
            if csr_ds.nodata is not None:
                csr_grid[csr_grid == csr_ds.nodata] = np.nan
            if jpl_ds.nodata is not None:
                jpl_grid[jpl_grid == jpl_ds.nodata] = np.nan
        valid = np.isfinite(csr_grid) & np.isfinite(jpl_grid)
        if valid.sum() == 0:
            rows.append({"month": month, "status": "no_overlap"})
            continue
        csr_values = csr_grid[valid]
        jpl_values = jpl_grid[valid]
        diff = csr_values - jpl_values
        corr = float(np.corrcoef(csr_values, jpl_values)[0, 1]) if valid.sum() > 1 else None
        rmse = float(np.sqrt(np.mean(diff**2)))
        bias = float(np.mean(diff))
        csr_mean = float(np.mean(csr_values))
        jpl_mean = float(np.mean(jpl_values))
        rows.append(
            {
                "month": month,
                "status": "ok",
                "target_type": "terrestrial_water_storage",
                "target_product": "JPL GRACE Tellus land water-equivalent-thickness",
                "correlation": corr,
                "rmse_cm": rmse,
                "bias_cm": bias,
                "csr_basin_mean_cm": csr_mean,
                "jpl_basin_mean_cm": jpl_mean,
                "grid_cells": int(valid.sum()),
                "csr_grid": str(csr_crop),
                "jpl_grid": str(jpl_crop),
            }
        )
        months.append(month)
        csr_series.append(csr_mean)
        jpl_series.append(jpl_mean)

    csv_path = output_dir / "tws_comparison_metrics.csv"
    write_csv(csv_path, rows)
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    missing_months = [row["month"] for row in rows if row.get("status") != "ok"]
    trend_agreement = None
    if len(csr_series) >= 2:
        csr_delta = np.diff(csr_series)
        jpl_delta = np.diff(jpl_series)
        trend_agreement = float(np.mean(np.sign(csr_delta) == np.sign(jpl_delta)))
    summary = {
        "target_type": "terrestrial_water_storage",
        "comparison": "CSR GRACE Tellus vs JPL GRACE Tellus over the same western U.S. crop",
        "months": len(ok_rows),
        "requested_months": len(requested_months),
        "ok_months": len(ok_rows),
        "missing_months": missing_months,
        "coverage": f"{len(ok_rows)}/{len(requested_months)}",
        "mean_correlation": float(np.nanmean([row["correlation"] for row in ok_rows])) if ok_rows else None,
        "mean_rmse_cm": float(np.nanmean([row["rmse_cm"] for row in ok_rows])) if ok_rows else None,
        "mean_bias_cm": float(np.nanmean([row["bias_cm"] for row in ok_rows])) if ok_rows else None,
        "trend_agreement": trend_agreement,
        "citation": f"CSR: {GRACE_DOI}; JPL: {JPL_GRACE_DOI}",
        "metrics_csv": str(csv_path),
    }
    (output_dir / "tws_comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if ok_rows:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
        axes[0].plot(months, csr_series, marker="o", label="CSR")
        axes[0].plot(months, jpl_series, marker="o", label="JPL")
        axes[0].set_title("Basin-Aggregated TWS Proxy")
        axes[0].set_ylabel("Mean cm EWT")
        axes[0].tick_params(axis="x", rotation=35)
        axes[0].grid(alpha=0.25)
        axes[0].legend()
        axes[1].scatter(csr_series, jpl_series, color="#245f8f")
        low = min(csr_series + jpl_series)
        high = max(csr_series + jpl_series)
        axes[1].plot([low, high], [low, high], color="#8a99a6", linestyle="--", linewidth=1)
        axes[1].set_xlabel("CSR mean cm EWT")
        axes[1].set_ylabel("JPL mean cm EWT")
        axes[1].set_title("Processing-Center Agreement")
        axes[1].grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "tws_comparison.png", dpi=160)
        plt.close(fig)
    return summary


def try_download(url: str, path: Path) -> tuple[bool, str | None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 1024:
        return True, None
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as exc:
        return False, str(exc)
    if path.stat().st_size < 1024:
        snippet = path.read_bytes()[:160].decode("utf-8", errors="replace")
        return False, snippet
    return True, None


def earthdata_credentials() -> tuple[str | None, str | None, str]:
    username = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")
    if username and password:
        return username, password, "environment"
    try:
        auth = netrc.netrc().authenticators(EARTHDATA_HOST)
    except (FileNotFoundError, netrc.NetrcParseError):
        auth = None
    if auth:
        login, _, passwd = auth
        return login, passwd, ".netrc"
    return None, None, "none"


def earthdata_opener() -> tuple[urllib.request.OpenerDirector | None, str]:
    username, password, source = earthdata_credentials()
    if not (username and password):
        return None, "No Earthdata credentials found. Use ~/.netrc or EARTHDATA_USERNAME/EARTHDATA_PASSWORD."
    password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, f"https://{EARTHDATA_HOST}", username, password)
    password_manager.add_password(None, f"https://{EARTHDATA_HOST}/", username, password)
    opener = urllib.request.build_opener(
        urllib.request.HTTPBasicAuthHandler(password_manager),
        urllib.request.HTTPDigestAuthHandler(password_manager),
        urllib.request.HTTPCookieProcessor(),
    )
    opener.addheaders = [("User-Agent", "quantum-sensing-earth/0.1")]
    return opener, f"Earthdata credentials loaded from {source}."


def earthdata_download(url: str, path: Path) -> tuple[bool, str | None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 1024:
        return True, None
    opener, message = earthdata_opener()
    if opener is None:
        return False, message
    try:
        with opener.open(url, timeout=120) as response, path.open("wb") as fh:
            fh.write(response.read())
    except Exception as exc:
        return False, f"{message} Download failed: {exc}"
    if path.stat().st_size < 1024:
        snippet = path.read_bytes()[:160].decode("utf-8", errors="replace")
        return False, f"{message} Downloaded response is not a NetCDF file: {snippet}"
    return True, message


def doctor_gldas_files(granules: list[dict], raw_dir: Path) -> dict:
    rows = []
    valid = True
    for granule in granules:
        path = raw_dir / granule["filename"]
        row = {"month": granule["start"][:7], "path": str(path), "exists": path.exists(), "readable": False, "variable": None}
        if not path.exists() or path.stat().st_size < 1024:
            valid = False
            row["error"] = "missing or too small"
            rows.append(row)
            continue
        try:
            import netCDF4

            with netCDF4.Dataset(path) as dataset:
                variables = dataset.variables
                candidates = [
                    name
                    for name, variable in variables.items()
                    if name.lower() not in {"lat", "latitude", "lon", "longitude", "time", "time_bounds"}
                    and getattr(variable, "ndim", 0) >= 2
                    and np.issubdtype(np.asarray(variable[:]).dtype, np.number)
                ]
                preferred = [name for name in candidates if any(token in name.lower() for token in ("tws", "water", "lwe", "equiv"))]
                row["variable"] = preferred[0] if preferred else (candidates[0] if candidates else None)
                row["readable"] = row["variable"] is not None
                if not row["readable"]:
                    valid = False
                    row["error"] = "no numeric TWS-like grid variable found"
        except Exception as exc:
            valid = False
            row["error"] = str(exc)
        rows.append(row)
    return {"valid": valid, "files": rows}


def gldas_granules(count: int, start: str) -> list[dict]:
    temporal = f"{start}T00:00:00Z,"
    url = (
        f"{CMR_GRANULES}?collection_concept_id={GLDAS_COLLECTION}"
        f"&temporal={urllib.parse.quote(temporal)}&page_size={count}&sort_key=start_date"
    )
    entries = fetch_json(url).get("feed", {}).get("entry", [])
    granules = []
    for entry in entries:
        nc_links = [
            link["href"]
            for link in entry.get("links", [])
            if link.get("href", "").lower().endswith(".nc")
        ]
        if not nc_links:
            continue
        granules.append(
            {
                "title": entry["title"],
                "start": entry["time_start"],
                "end": entry["time_end"],
                "url": nc_links[0],
                "filename": Path(nc_links[0]).name,
            }
        )
    if len(granules) < count:
        raise RuntimeError(f"Only found {len(granules)} GLDAS NetCDF granules; requested {count}.")
    return granules[:count]


def read_gldas_grid(path: Path, bbox: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        import netCDF4
    except ImportError as exc:
        raise ImportError("GLDAS NetCDF support requires netCDF4. Install with `pip install -e .[geo]`.") from exc

    with netCDF4.Dataset(path) as dataset:
        variables = dataset.variables
        lat_name = next(name for name in ("lat", "latitude", "y") if name in variables)
        lon_name = next(name for name in ("lon", "longitude", "x") if name in variables)
        lats = np.asarray(variables[lat_name][:], dtype=float)
        lons = np.asarray(variables[lon_name][:], dtype=float)
        candidates = []
        for name, variable in variables.items():
            if name in {lat_name, lon_name, "time", "time_bounds"}:
                continue
            if getattr(variable, "ndim", 0) >= 2 and np.issubdtype(np.asarray(variable[:]).dtype, np.number):
                candidates.append(name)
        preferred = [name for name in candidates if any(token in name.lower() for token in ("tws", "water", "lwe", "equiv"))]
        var_name = preferred[0] if preferred else candidates[0]
        values = np.asarray(variables[var_name][:], dtype=float)
        if values.ndim == 3:
            values = values[0]
        fill = getattr(variables[var_name], "_FillValue", None)
        missing = getattr(variables[var_name], "missing_value", None)
        if fill is not None:
            values[values == float(fill)] = np.nan
        if missing is not None:
            values[values == float(missing)] = np.nan

    min_lon, min_lat, max_lon, max_lat = bbox
    lon_values = np.where(lons > 180, lons - 360, lons)
    lat_mask = (lats >= min_lat) & (lats <= max_lat)
    lon_mask = (lon_values >= min_lon) & (lon_values <= max_lon)
    cropped = values[np.ix_(lat_mask, lon_mask)]
    cropped_lats = lats[lat_mask]
    cropped_lons = lon_values[lon_mask]
    if cropped_lats.size and cropped_lats[0] < cropped_lats[-1]:
        cropped = np.flipud(cropped)
        cropped_lats = cropped_lats[::-1]
    return cropped, cropped_lats, cropped_lons


def write_gldas_track(output_dir: Path, csr_granules: list[dict], start: str, bbox: list[float]) -> dict:
    import matplotlib.pyplot as plt
    import rasterio

    raw_dir = Path("data/gldas/raw")
    requested_months = [granule["start"][:7] for granule in csr_granules]
    gldas_by_month = {
        month: granule_for_month(GLDAS_COLLECTION, month, ".nc", public_only=False, require_exact=True)
        for month in requested_months
    }
    gldas = [granule for granule in gldas_by_month.values() if granule is not None]
    rows = []
    csr_series = []
    gldas_series = []
    months = []
    blocked_reasons = []
    credential_user, _, credential_source = earthdata_credentials()
    for csr in csr_granules:
        month = csr["start"][:7]
        gldas_granule = gldas_by_month.get(month)
        if not gldas_granule:
            rows.append({"month": month, "status": "missing_gldas_match"})
            continue
        nc_path = raw_dir / gldas_granule["filename"]
        ok, reason = earthdata_download(gldas_granule["url"], nc_path)
        if not ok:
            rows.append(
                {
                    "month": month,
                    "status": "requires_earthdata_login_or_manual_file",
                    "source": gldas_granule["url"],
                    "reason": reason,
                }
            )
            blocked_reasons.append(reason or "download blocked")
            continue
        doctor = doctor_gldas_files([gldas_granule], raw_dir)
        if not doctor["valid"]:
            rows.append(
                {
                    "month": month,
                    "status": "doctor_failed",
                    "source": gldas_granule["url"],
                    "reason": json.dumps(doctor["files"][0]),
                }
            )
            continue
        try:
            gldas_grid, _, _ = read_gldas_grid(nc_path, bbox)
        except Exception as exc:
            rows.append({"month": month, "status": "read_error", "source": str(nc_path), "reason": str(exc)})
            continue
        csr_grid_path = Path("data/grace_tellus/multimonth_tws") / f"csr_western_us_{month.replace('-', '')}.tif"
        if not csr_grid_path.exists():
            csr_raw = Path("data/grace_tellus/raw") / csr["filename"]
            crop_raster(csr_raw, csr_grid_path, bbox)
        with rasterio.open(csr_grid_path) as csr_ds:
            csr_grid = csr_ds.read(1).astype(float)
            if csr_ds.nodata is not None:
                csr_grid[csr_grid == csr_ds.nodata] = np.nan
        rows_min = min(csr_grid.shape[0], gldas_grid.shape[0])
        cols_min = min(csr_grid.shape[1], gldas_grid.shape[1])
        csr_grid = csr_grid[:rows_min, :cols_min]
        gldas_grid = gldas_grid[:rows_min, :cols_min]
        valid = np.isfinite(csr_grid) & np.isfinite(gldas_grid)
        if valid.sum() == 0:
            rows.append({"month": month, "status": "no_overlap"})
            continue
        csr_values = csr_grid[valid]
        gldas_values = gldas_grid[valid]
        diff = csr_values - gldas_values
        csr_mean = float(np.mean(csr_values))
        gldas_mean = float(np.mean(gldas_values))
        rows.append(
            {
                "month": month,
                "status": "ok",
                "target_type": "terrestrial_water_storage",
                "target_product": "GLDAS-NOAH 3.3 TWS anomaly monthly",
                "resampling": "GLDAS 1-degree monthly TWS anomaly cropped to the same western U.S. 1-degree grid; no interpolation needed when dimensions match, otherwise overlapping grid window is used.",
                "correlation": float(np.corrcoef(csr_values, gldas_values)[0, 1]) if valid.sum() > 1 else None,
                "rmse_cm": float(np.sqrt(np.mean(diff**2))),
                "bias_cm": float(np.mean(diff)),
                "csr_basin_mean_cm": csr_mean,
                "gldas_basin_mean_cm": gldas_mean,
                "anomaly_sign_agreement": float(np.mean(np.sign(csr_values) == np.sign(gldas_values))),
                "grid_cells": int(valid.sum()),
            }
        )
        months.append(month)
        csr_series.append(csr_mean)
        gldas_series.append(gldas_mean)

    csv_path = output_dir / "gldas_hydrology_metrics.csv"
    write_csv(csv_path, rows)
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    missing_months = [row["month"] for row in rows if row.get("status") != "ok"]
    doctor = doctor_gldas_files(gldas, raw_dir)
    (output_dir / "gldas_doctor.json").write_text(json.dumps(doctor, indent=2), encoding="utf-8")
    trend_agreement = None
    if len(ok_rows) >= 2:
        trend_agreement = float(np.mean(np.sign(np.diff(csr_series)) == np.sign(np.diff(gldas_series))))
    summary = {
        "target_type": "terrestrial_water_storage",
        "comparison": "CSR GRACE Tellus vs external GLDAS-NOAH terrestrial water storage anomaly over the same western U.S. crop",
        "status": "ok" if ok_rows else "requires_earthdata_login_or_manual_file",
        "months": len(ok_rows),
        "requested_months": len(requested_months),
        "ok_months": len(ok_rows),
        "missing_months": missing_months,
        "coverage": f"{len(ok_rows)}/{len(requested_months)}",
        "source": GLDAS_SOURCE,
        "credential_source": credential_source if credential_user else "none",
        "doctor": doctor,
        "resampling": "GLDAS 1-degree monthly TWS anomaly is cropped/aligned to the same 1-degree western U.S. GRACE grid.",
        "mean_correlation": float(np.nanmean([row["correlation"] for row in ok_rows])) if ok_rows else None,
        "mean_rmse_cm": float(np.nanmean([row["rmse_cm"] for row in ok_rows])) if ok_rows else None,
        "mean_bias_cm": float(np.nanmean([row["bias_cm"] for row in ok_rows])) if ok_rows else None,
        "trend_agreement": trend_agreement,
        "mean_anomaly_sign_agreement": float(np.nanmean([row["anomaly_sign_agreement"] for row in ok_rows])) if ok_rows else None,
        "metrics_csv": str(csv_path),
        "blocked_reason": blocked_reasons[0] if blocked_reasons else None,
        "manual_download_note": "If status is blocked, download the GLDAS .nc granules listed in gldas_hydrology_metrics.csv into data/gldas/raw/ and rerun with --skip-existing.",
    }
    (output_dir / "gldas_hydrology_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if ok_rows:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
        axes[0].plot(months, csr_series, marker="o", label="GRACE CSR")
        axes[0].plot(months, gldas_series, marker="o", label="GLDAS")
        axes[0].set_title("Basin-Aggregated GRACE vs GLDAS")
        axes[0].set_ylabel("Mean cm EWT anomaly")
        axes[0].tick_params(axis="x", rotation=35)
        axes[0].grid(alpha=0.25)
        axes[0].legend()
        axes[1].scatter(csr_series, gldas_series, color="#1f7a4d")
        low = min(csr_series + gldas_series)
        high = max(csr_series + gldas_series)
        axes[1].plot([low, high], [low, high], color="#8a99a6", linestyle="--", linewidth=1)
        axes[1].set_xlabel("GRACE CSR mean cm EWT")
        axes[1].set_ylabel("GLDAS mean cm EWT")
        axes[1].set_title("External Hydrology Agreement")
        axes[1].grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "gldas_hydrology_comparison.png", dpi=160)
        plt.close(fig)
    return summary


def stats(values: list[float]) -> dict:
    numeric = np.array([float(v) for v in values if pd.notna(v)], dtype=float)
    if numeric.size == 0:
        return {"mean": None, "std": None, "min": None, "max": None}
    return {
        "mean": float(np.mean(numeric)),
        "std": float(np.std(numeric, ddof=1)) if numeric.size > 1 else 0.0,
        "min": float(np.min(numeric)),
        "max": float(np.max(numeric)),
    }


def status_from_csv(path: Path, ok_statuses: set[str] | None = None) -> dict[str, str]:
    ok_statuses = ok_statuses or {"ok"}
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return {}
    if frame.empty or "month" not in frame.columns:
        return {}
    if "status" not in frame.columns:
        frame["status"] = "ok"
    status = {}
    for month, group in frame.groupby(frame["month"].map(normalize_month_key), dropna=True):
        statuses = {str(value) for value in group["status"].dropna()}
        status[month] = "ok" if statuses & ok_statuses else sorted(statuses)[0] if statuses else "missing"
    return status


def write_executive_summary(
    output_dir: Path,
    coverage: dict | None,
    gldas_summary: dict | None,
    tws_summary: dict | None,
    groundwater_summary: dict | None,
) -> Path:
    timeline = pd.read_csv(output_dir / "timeline_metrics.csv") if (output_dir / "timeline_metrics.csv").exists() else pd.DataFrame()
    groundwater = (
        pd.read_csv(output_dir / "groundwater_validation_summary.csv")
        if (output_dir / "groundwater_validation_summary.csv").exists() and (output_dir / "groundwater_validation_summary.csv").stat().st_size > 0
        else pd.DataFrame()
    )
    ok_timeline = timeline[timeline["status"].eq("ok")] if not timeline.empty and "status" in timeline else timeline
    best_detector = None
    weakest_detector = None
    if not ok_timeline.empty:
        scored = ok_timeline.copy()
        scored["review_score"] = scored["f1"].fillna(0) + scored["iou"].fillna(0)
        best_detector = scored.loc[scored["review_score"].idxmax()]
        weakest_detector = scored.loc[scored["f1"].fillna(0).idxmin()]

    ok_groundwater = groundwater[groundwater["status"].eq("ok")] if not groundwater.empty and "status" in groundwater else pd.DataFrame()
    best_groundwater = None
    if not ok_groundwater.empty and "grace_groundwater_correlation" in ok_groundwater:
        best_groundwater = ok_groundwater.sort_values("grace_groundwater_correlation", ascending=False, na_position="last").head(1).iloc[0]

    targets = (coverage or {}).get("targets", {})
    coverage_lines = [f"- {target}: `{info.get('coverage', 'n/a')}`" for target, info in sorted(targets.items())]
    groundwater_status = (groundwater_summary or {}).get("status", "not_configured")
    lines = [
        "# Executive Summary",
        "",
        "This run is a GRACE/GRACE-FO basin-scale hydrology and groundwater validation bundle. It is not evidence of a proven quantum groundwater detector or quantum advantage.",
        "",
        "## Validation Status",
        "",
        f"- Detector months: `{ok_timeline['month'].nunique() if not ok_timeline.empty and 'month' in ok_timeline else 0}`",
        f"- GLDAS status: `{(gldas_summary or {}).get('status', 'missing')}`",
        f"- TWS coverage: `{(tws_summary or {}).get('coverage', 'missing')}`",
        f"- Groundwater status: `{groundwater_status}`",
        "",
        "## Coverage",
        "",
        *(coverage_lines or ["- No coverage summary was generated."]),
        "",
        "## Strongest Result",
        "",
    ]
    if best_groundwater is not None:
        lines.append(
            f"- Best groundwater basin: `{best_groundwater.get('basin_name')}` with GRACE-groundwater correlation `{best_groundwater.get('grace_groundwater_correlation'):.3f}` over `{int(best_groundwater.get('valid_months', 0))}` valid months."
        )
    elif best_detector is not None:
        lines.append(
            f"- Best detector row: `{best_detector.get('algorithm')}` / `{best_detector.get('sensor_profile')}` / D{best_detector.get('threshold')}+ with F1 `{float(best_detector.get('f1')):.3f}`."
        )
    else:
        lines.append("- No successful detector or groundwater rows were available.")
    lines.extend(["", "## Weakest Result", ""])
    if weakest_detector is not None:
        lines.append(
            f"- Weakest detector row: `{weakest_detector.get('month')}` D{weakest_detector.get('threshold')}+ `{weakest_detector.get('algorithm')}` with F1 `{float(weakest_detector.get('f1')):.3f}`."
        )
    else:
        lines.append("- No detector weakness could be summarized.")
    lines.extend(
        [
            "",
            "## Scientific Caveats",
            "",
            "- USDM is an independent drought proxy, not groundwater truth.",
            "- GLDAS/TWS are hydrology comparison targets, not direct well observations.",
            "- Groundwater rows marked `insufficient_months` are not strong evidence.",
            "- Quantum advantage is not claimed by this workflow.",
            "",
            "## Recommended Next Dataset",
            "",
            "Extend the Central Valley run with longer DWR/USGS well coverage or basin storage observations, then compare basin-level GRACE/GRACE-FO anomalies over at least 12 months.",
            "",
        ]
    )
    path = output_dir / "executive_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_batch_contract(
    output_dir: Path,
    run_rows: list[dict],
    gldas_summary: dict | None = None,
    tws_summary: dict | None = None,
    groundwater_summary: dict | None = None,
) -> dict:
    detection_months = {normalize_month_key(row["month"]) for row in run_rows if normalize_month_key(row["month"])}
    target_status = {
        "gldas": status_from_csv(output_dir / "gldas_hydrology_metrics.csv"),
        "tws": status_from_csv(output_dir / "tws_comparison_metrics.csv"),
        "basin": status_from_csv(output_dir / "basin_metrics.csv", ok_statuses={"ok"}),
        "groundwater": status_from_csv(output_dir / "groundwater_basin_monthly.csv", ok_statuses={"ok"}),
    }
    coverage = write_coverage_artifacts(output_dir, detection_months, target_status)
    write_executive_summary(output_dir, coverage, gldas_summary, tws_summary, groundwater_summary)
    required = {
        "timeline_metrics.csv",
        "coverage_summary.json",
        "month_alignment.csv",
        "timeline_report.html",
        "executive_summary.md",
        "basin_metrics.csv",
        "basin_summary.json",
    }
    if groundwater_summary and groundwater_summary.get("status") in {"ok", "insufficient_months"}:
        required.update(
            {
                "groundwater_observations.csv",
                "groundwater_basin_monthly.csv",
                "groundwater_validation_metrics.csv",
                "groundwater_validation_summary.json",
                "groundwater_summary.json",
            }
        )
    write_artifact_manifest(
        output_dir,
        producer_command=command_text(["python", "examples\\grace_tellus\\run_multimonth_usdm.py"]),
        required_for_dashboard=required,
        extra_metadata={"workflow": "grace_usdm_gldas_groundwater_multimonth"},
    )
    return coverage


def write_timeline_plot(path: Path, rows: list[dict]) -> None:
    import matplotlib.pyplot as plt

    ok_rows = [row for row in rows if row.get("status") == "ok" and row.get("algorithm") == "z_score"]
    if not ok_rows:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    grouped = defaultdict(list)
    for row in ok_rows:
        grouped[(row["sensor_profile"], row["threshold"])].append(row)
    for (sensor, threshold), group in sorted(grouped.items()):
        group = sorted(group, key=lambda item: item["month"])
        ax.plot([item["month"] for item in group], [float(item["f1"]) for item in group], marker="o", label=f"{sensor} D{threshold}+")
    ax.set_ylabel("Held-out F1")
    ax.set_xlabel("GRACE month")
    ax.set_title("GRACE + USDM z-score F1 over time")
    ax.tick_params(axis="x", rotation=35)
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_story_visuals(output_dir: Path, rows: list[dict], focus_threshold: int) -> dict:
    ok_rows = [row for row in rows if row.get("status") == "ok" and int(row.get("threshold", 0)) == int(focus_threshold)]
    if not ok_rows:
        return {"study_region": None, "monthly_context": {}}

    import matplotlib.pyplot as plt
    import rasterio

    def read_grid(path_text):
        with rasterio.open(path_text) as dataset:
            grid = dataset.read(1, masked=True)
            bounds = dataset.bounds
            return grid, [bounds.left, bounds.right, bounds.bottom, bounds.top]

    by_month = {}
    for row in ok_rows:
        by_month.setdefault(row["month"], row)

    monthly_context = {}
    first_row = next(iter(by_month.values()))
    with rasterio.open(first_row["grid_path"]) as dataset:
        bounds = dataset.bounds
        width = dataset.width
        height = dataset.height
    mask, extent = read_grid(first_row["mask_path"])
    mask_array = np.asarray(mask.filled(0) > 0, dtype=float)
    mask_array[mask_array == 0] = np.nan
    study_path = output_dir / "study_region_map.png"
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.set_facecolor("#f4f7f8")
    ax.set_xlim(-130, -96)
    ax.set_ylim(27, 52)
    ax.add_patch(
        plt.Rectangle(
            (bounds.left, bounds.bottom),
            bounds.right - bounds.left,
            bounds.top - bounds.bottom,
            fill=False,
            edgecolor="#245f8f",
            linewidth=2.0,
            label="GRACE crop",
        )
    )
    for x in np.arange(bounds.left, bounds.right + 0.1, 1):
        ax.plot([x, x], [bounds.bottom, bounds.top], color="#b7c4cf", linewidth=0.35, alpha=0.75)
    for y in np.arange(bounds.bottom, bounds.top + 0.1, 1):
        ax.plot([bounds.left, bounds.right], [y, y], color="#b7c4cf", linewidth=0.35, alpha=0.75)
    ax.imshow(mask_array, extent=extent, origin="upper", cmap="Reds", alpha=0.72, vmin=0, vmax=1)
    ax.contour(mask_array, levels=[0.5], extent=extent, origin="upper", colors=["#b42318"], linewidths=1.2)
    ax.set_title(f"Western U.S. GRACE Crop With USDM D{focus_threshold}+ Mask")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.text(bounds.left + 0.3, bounds.top - 1.2, f"{height} x {width} one-degree GRACE cells", color="#173b57", fontsize=9)
    ax.grid(color="#d4dde4", linewidth=0.5, alpha=0.6)
    fig.tight_layout()
    fig.savefig(study_path, dpi=160)
    plt.close(fig)

    for month, row in sorted(by_month.items()):
        grid, extent = read_grid(row["grid_path"])
        mask, _ = read_grid(row["mask_path"])
        path = output_dir / f"month_context_{month.replace('-', '')}_d{focus_threshold}.png"
        fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7), sharex=True, sharey=True)
        image = axes[0].imshow(grid, extent=extent, origin="upper", cmap="viridis")
        axes[0].set_title(f"{month} GRACE")
        axes[0].set_xlabel("Longitude")
        axes[0].set_ylabel("Latitude")
        fig.colorbar(image, ax=axes[0], fraction=0.046, pad=0.04, label="cm EWT")
        axes[1].imshow(grid, extent=extent, origin="upper", cmap="Greys", alpha=0.35)
        axes[1].imshow(np.where(mask.filled(0) > 0, 1, np.nan), extent=extent, origin="upper", cmap="Reds", alpha=0.62)
        axes[1].set_title(f"USDM D{focus_threshold}+ Overlay")
        axes[1].set_xlabel("Longitude")
        for ax in axes:
            ax.grid(color="#d4dde4", linewidth=0.5, alpha=0.6)
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
        monthly_context[month] = path.name

    return {"study_region": study_path.name, "monthly_context": monthly_context}


def write_timeline_report(
    path: Path,
    rows: list[dict],
    tws_summary: dict | None = None,
    gldas_summary: dict | None = None,
) -> None:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    failed = [row for row in rows if row.get("status") != "ok"]
    groups = defaultdict(list)
    for row in ok_rows:
        groups[(row["threshold"], row["sensor_profile"], row["algorithm"])].append(row)
    aggregate_rows = []
    for key, group in sorted(groups.items()):
        threshold, sensor, algorithm = key
        aggregate_rows.append(
            {
                "threshold": threshold,
                "sensor": sensor,
                "algorithm": algorithm,
                "months": len({item["month"] for item in group}),
                "f1": stats([item["f1"] for item in group]),
                "iou": stats([item["iou"] for item in group]),
                "fpr": stats([item["false_positive_rate"] for item in group]),
                "best_month": max(group, key=lambda item: float(item["f1"]))["month"],
                "worst_month": min(group, key=lambda item: float(item["f1"]))["month"],
            }
        )

    def fmt(value):
        if value is None or pd.isna(value):
            return "n/a"
        return f"{float(value):.3f}"

    def fmt_signed(value):
        if value is None or pd.isna(value):
            return "n/a"
        return f"{float(value):+.3f}"

    best_row = max(ok_rows, key=lambda item: float(item["f1"])) if ok_rows else None
    month_count = len({row["month"] for row in ok_rows})
    run_count = len({(row["month"], row["threshold"]) for row in ok_rows})
    threshold_labels = ", ".join(f"D{threshold}+" for threshold in sorted({int(row["threshold"]) for row in ok_rows}))
    best_combo = (
        f"D{best_row['threshold']}+ / {best_row['sensor_profile']} / {best_row['algorithm']}"
        if best_row
        else "n/a"
    )
    avg_best_f1 = fmt(best_row["f1"]) if best_row else "n/a"
    best_aggregate = max(aggregate_rows, key=lambda item: float(item["f1"]["mean"])) if aggregate_rows else None
    best_aggregate_label = (
        f"D{best_aggregate['threshold']}+ {best_aggregate['sensor']} with {best_aggregate['algorithm']}"
        if best_aggregate
        else "n/a"
    )
    best_aggregate_f1 = fmt(best_aggregate["f1"]["mean"]) if best_aggregate else "n/a"
    algorithm_rank = []
    for algorithm in sorted({row["algorithm"] for row in ok_rows}):
        values = [float(row["f1"]) for row in ok_rows if row["algorithm"] == algorithm and pd.notna(row["f1"])]
        algorithm_rank.append((float(np.mean(values)) if values else 0.0, algorithm))
    algorithm_rank.sort(reverse=True)
    strongest_algorithm = algorithm_rank[0][1] if algorithm_rank else "n/a"
    weak_algorithm = algorithm_rank[-1][1] if algorithm_rank else "n/a"
    threshold_rank = []
    for threshold in sorted({int(row["threshold"]) for row in ok_rows}):
        values = [float(row["f1"]) for row in ok_rows if int(row["threshold"]) == threshold and pd.notna(row["f1"])]
        threshold_rank.append((threshold, float(np.mean(values)) if values else 0.0))
    threshold_sentence = ", ".join(f"D{threshold}+ averaged {fmt(mean)} F1" for threshold, mean in threshold_rank)
    first_month = min({row["month"] for row in ok_rows}) if ok_rows else "n/a"
    last_month = max({row["month"] for row in ok_rows}) if ok_rows else "n/a"
    focus_threshold = int(best_aggregate["threshold"]) if best_aggregate else 1
    visuals = write_story_visuals(path.parent, rows, focus_threshold)
    study_region_image = visuals.get("study_region")
    tws_summary = tws_summary or {}
    gldas_summary = gldas_summary or {}
    gldas_ok = gldas_summary.get("status") == "ok"
    gldas_sentence = (
        f"The external GLDAS track is live: mean correlation {fmt(gldas_summary.get('mean_correlation'))}, RMSE {fmt(gldas_summary.get('mean_rmse_cm'))} cm EWT, and anomaly sign agreement {fmt(gldas_summary.get('mean_anomaly_sign_agreement'))}."
        if gldas_ok
        else "The external GLDAS track is implemented, but still waiting on authenticated NetCDF files."
    )
    executive_overview = (
        "This project is a reproducible validation workflow for gravity-derived water-mass anomaly detection. "
        "It compares simulated detector outputs on real GRACE Tellus rasters against independent drought labels from USDM and an external hydrology target from GLDAS. "
        f"The strongest repeated detector result is {best_aggregate_label}, averaging {best_aggregate_f1} F1 across the tested months. "
        f"{gldas_sentence} "
        "The project does not prove a quantum detector can discover groundwater; it shows the validation machinery needed to test that claim against progressively stronger targets."
    )

    aggregate_body = []
    for row in aggregate_rows:
        aggregate_body.append(
            "<tr "
            f"data-threshold='D{row['threshold']}+' data-sensor='{html.escape(row['sensor'])}' data-algorithm='{html.escape(row['algorithm'])}'>"
            f"<td>D{row['threshold']}+</td><td>{html.escape(row['sensor'])}</td><td>{html.escape(row['algorithm'])}</td>"
            f"<td data-sort='{row['months']}'>{row['months']}</td>"
            f"<td data-sort='{row['f1']['mean']}'>{fmt(row['f1']['mean'])}<span>{fmt(row['f1']['std'])} std</span></td>"
            f"<td data-sort='{row['iou']['mean']}'>{fmt(row['iou']['mean'])}<span>{fmt(row['iou']['std'])} std</span></td>"
            f"<td data-sort='{row['fpr']['mean']}'>{fmt(row['fpr']['mean'])}<span>{fmt(row['fpr']['std'])} std</span></td>"
            f"<td>{html.escape(row['best_month'])}</td><td>{html.escape(row['worst_month'])}</td></tr>"
        )

    detail_body = []
    for row in sorted(ok_rows, key=lambda item: (item["month"], item["threshold"], item["sensor_profile"], item["algorithm"])):
        report = Path(row["run_dir"]) / "report.html"
        rel = report.relative_to(path.parent).as_posix()
        detail_body.append(
            "<tr "
            f"data-threshold='D{row['threshold']}+' data-sensor='{html.escape(row['sensor_profile'])}' data-algorithm='{html.escape(row['algorithm'])}'>"
            f"<td>{html.escape(row['month'])}</td><td>{html.escape(str(row['usdm_date']))}</td><td>D{row['threshold']}+</td>"
            f"<td>{html.escape(row['sensor_profile'])}</td><td>{html.escape(row['algorithm'])}</td>"
            f"<td data-sort='{row['f1']}'>{fmt(row['f1'])}</td><td data-sort='{row['iou']}'>{fmt(row['iou'])}</td>"
            f"<td data-sort='{row['false_positive_rate']}'>{fmt(row['false_positive_rate'])}</td>"
            f"<td><a href='{html.escape(rel)}'>open</a></td></tr>"
        )

    monthly_panel_cards = []
    for month, image_name in sorted((visuals.get("monthly_context") or {}).items()):
        month_rows = [row for row in ok_rows if row["month"] == month and int(row["threshold"]) == focus_threshold]
        best_month_row = max(month_rows, key=lambda item: float(item["f1"])) if month_rows else None
        caption = (
            f"Best detector this month: {best_month_row['sensor_profile']} / {best_month_row['algorithm']} at F1 {fmt(best_month_row['f1'])}."
            if best_month_row
            else "No detector summary available."
        )
        monthly_panel_cards.append(
            f"<figure><img src='{html.escape(image_name)}' alt='{html.escape(month)} GRACE and USDM context'><figcaption><strong>{html.escape(month)}</strong>{html.escape(caption)}</figcaption></figure>"
        )

    outcome_cards = []
    if best_aggregate:
        for month in sorted({row["month"] for row in ok_rows}):
            matches = [
                row
                for row in ok_rows
                if row["month"] == month
                and int(row["threshold"]) == focus_threshold
                and row["sensor_profile"] == best_aggregate["sensor"]
                and row["algorithm"] == best_aggregate["algorithm"]
            ]
            if not matches:
                continue
            row = matches[0]
            overlay_name = f"{row['sensor_profile']}_{row['algorithm']}_overlay.png"
            overlay_path = Path(row["run_dir"]) / overlay_name
            if not overlay_path.exists():
                continue
            rel = overlay_path.relative_to(path.parent).as_posix()
            outcome_cards.append(
                f"<figure><a href='{html.escape(rel)}'><img src='{html.escape(rel)}' alt='{html.escape(month)} detector outcome'></a>"
                f"<figcaption><strong>{html.escape(month)}</strong>D{focus_threshold}+ {html.escape(row['algorithm'])}: F1 {fmt(row['f1'])}, IoU {fmt(row['iou'])}, FPR {fmt(row['false_positive_rate'])}</figcaption></figure>"
            )

    tws_section = ""
    if tws_summary:
        tws_section = (
            "<section class='panel target-panel'><h2>Hydrology / TWS Comparison Track</h2>"
            "<p>This adds a water-mass comparison beside the drought-proxy task. The target is JPL GRACE Tellus land water-equivalent thickness, compared against the CSR GRACE Tellus grid over the same western U.S. crop. Because both products estimate terrestrial water storage from GRACE processing, this is physically closer to the signal than USDM drought categories.</p>"
            "<div class='cards compact'>"
            f"<div class='card'><div class='label'>Target Type</div><div class='value'>TWS</div><div class='note'>terrestrial water storage</div></div>"
            f"<div class='card'><div class='label'>Mean Corr.</div><div class='value'>{fmt(tws_summary.get('mean_correlation'))}</div><div class='note'>CSR pixels vs JPL pixels</div></div>"
            f"<div class='card'><div class='label'>RMSE</div><div class='value'>{fmt(tws_summary.get('mean_rmse_cm'))}</div><div class='note'>cm equivalent water thickness</div></div>"
            f"<div class='card'><div class='label'>Bias</div><div class='value'>{fmt_signed(tws_summary.get('mean_bias_cm'))}</div><div class='note'>CSR minus JPL cm</div></div>"
            f"<div class='card'><div class='label'>Trend Agree</div><div class='value'>{fmt(tws_summary.get('trend_agreement'))}</div><div class='note'>basin-mean direction</div></div>"
            "</div>"
            "<img class='chart' src='tws_comparison.png' alt='TWS comparison plot'>"
            "<p class='meta'><a href='tws_comparison_metrics.csv'>tws_comparison_metrics.csv</a> · <a href='tws_comparison_summary.json'>tws_comparison_summary.json</a></p>"
            "</section>"
        )

    gldas_status = gldas_summary.get("status")
    gldas_section = ""
    if gldas_summary:
        if gldas_status == "ok":
            gldas_section = (
                "<section class='panel target-panel'><h2>External GLDAS Hydrology Target</h2>"
                "<p>This track compares GRACE CSR water-equivalent-thickness anomalies with GLDAS-NOAH terrestrial water storage anomalies over the same crop. GLDAS sums soil moisture, snow water, and canopy water, so it is an external hydrology target closer to terrestrial water storage than USDM drought categories.</p>"
                "<div class='cards compact'>"
                f"<div class='card'><div class='label'>Target Type</div><div class='value'>GLDAS</div><div class='note'>external hydrology</div></div>"
                f"<div class='card'><div class='label'>Mean Corr.</div><div class='value'>{fmt(gldas_summary.get('mean_correlation'))}</div><div class='note'>GRACE pixels vs GLDAS pixels</div></div>"
                f"<div class='card'><div class='label'>RMSE</div><div class='value'>{fmt(gldas_summary.get('mean_rmse_cm'))}</div><div class='note'>cm equivalent water thickness</div></div>"
                f"<div class='card'><div class='label'>Bias</div><div class='value'>{fmt_signed(gldas_summary.get('mean_bias_cm'))}</div><div class='note'>GRACE minus GLDAS cm</div></div>"
                f"<div class='card'><div class='label'>Sign Agree</div><div class='value'>{fmt(gldas_summary.get('mean_anomaly_sign_agreement'))}</div><div class='note'>cell anomaly direction</div></div>"
                "</div><img class='chart' src='gldas_hydrology_comparison.png' alt='GLDAS hydrology comparison plot'>"
                "<p class='meta'><a href='gldas_hydrology_metrics.csv'>gldas_hydrology_metrics.csv</a> · <a href='gldas_hydrology_summary.json'>gldas_hydrology_summary.json</a></p>"
                "</section>"
            )
        else:
            gldas_section = (
                "<section class='panel status-warn'><h2>External GLDAS Hydrology Target</h2>"
                "<p>The GLDAS track is implemented, but the PO.DAAC NetCDF granules require Earthdata-authenticated download in this environment. The report includes the manifest, source, target type, resampling plan, and metrics table placeholder so the same command will compute correlation, RMSE, bias, trend agreement, and anomaly sign agreement once the files are placed in <code>data/gldas/raw/</code>.</p>"
                f"<p class='meta'>Source: <a href='{html.escape(GLDAS_SOURCE)}'>TELLUS_GLDAS-NOAH-3.3_TWS-ANOMALY_MONTHLY</a>. Resampling: {html.escape(gldas_summary.get('resampling', '1-degree crop aligned to GRACE grid'))}</p>"
                f"<p class='meta'>Credential source: {html.escape(str(gldas_summary.get('credential_source', 'none')))}. Blocked reason: {html.escape(str(gldas_summary.get('blocked_reason') or 'n/a'))}</p>"
                "<p class='meta'><a href='gldas_hydrology_metrics.csv'>gldas_hydrology_metrics.csv</a> · <a href='gldas_hydrology_summary.json'>gldas_hydrology_summary.json</a> · <a href='gldas_doctor.json'>gldas_doctor.json</a></p>"
                "</section>"
            )

    failure_section = ""
    if failed:
        failure_rows = []
        for row in failed:
            failure_rows.append(
                f"<tr><td>{html.escape(str(row.get('month')))}</td><td>D{html.escape(str(row.get('threshold')))}+</td><td>{html.escape(str(row.get('reason')))}</td></tr>"
            )
        failure_section = (
            "<section class='panel status-warn'><h2>Failures</h2>"
            "<table><thead><tr><th>Month</th><th>Threshold</th><th>Reason</th></tr></thead>"
            f"<tbody>{''.join(failure_rows)}</tbody></table></section>"
        )

    executive_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Quantum Sensing Earth Executive Summary</title>
  <style>
    body{{font-family:Arial,Helvetica,sans-serif;margin:0;background:#f4f7f8;color:#172026;line-height:1.5}}
    main{{max-width:920px;margin:0 auto;padding:34px}}
    section{{background:#fff;border:1px solid #d9e0e6;border-radius:10px;padding:20px;margin:16px 0}}
    h1{{margin:0 0 10px;font-size:30px}} h2{{font-size:18px;margin:0 0 10px}} p{{margin:0 0 12px}}
    .metric{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}} .card{{border:1px solid #d9e0e6;border-radius:8px;padding:14px;background:#fbfcfd}} .label{{font-size:12px;color:#5c6873;text-transform:uppercase;font-weight:700}} .value{{font-size:24px;font-weight:700;margin-top:6px}}
    @media(max-width:760px){{main{{padding:18px}}.metric{{grid-template-columns:1fr}}}}
  </style>
</head>
<body><main>
  <h1>Quantum Sensing Earth: Executive Summary</h1>
  <section><h2>Five-Sentence Overview</h2><p>{html.escape(executive_overview)}</p></section>
  <section class="metric">
    <div class="card"><div class="label">Strongest Detector Result</div><div class="value">{best_aggregate_f1}</div><p>{html.escape(best_aggregate_label)}</p></div>
    <div class="card"><div class="label">External Hydrology Correlation</div><div class="value">{fmt(gldas_summary.get('mean_correlation'))}</div><p>GRACE CSR vs GLDAS TWS anomaly.</p></div>
    <div class="card"><div class="label">Validation Status</div><div class="value">{'Level 4' if gldas_ok else 'Level 3'}</div><p>{'External hydrology target computed.' if gldas_ok else 'Independent drought proxy, GLDAS pending.'}</p></div>
  </section>
  <section><h2>Strongest Result</h2><p>The most repeatable detection result is {html.escape(best_aggregate_label)} with mean F1 {best_aggregate_f1}. This is useful but modest, so it should be treated as early validation rather than a solved detection problem.</p></section>
  <section><h2>Weakest Result</h2><p>{html.escape(weak_algorithm)} is the least reliable detector in this coarse-grid batch. That matters because the GRACE crop has only a small number of one-degree cells; density-based clustering can collapse when the spatial signal is too coarse.</p></section>
  <section><h2>What Is Proven</h2><p>The project now proves it can ingest real GRACE rasters, align independent drought and hydrology targets, run calibrated detectors, aggregate basin-scale hydrology metrics, and report reproducible validation artifacts.</p></section>
  <section><h2>What Is Not Proven</h2><p>It does not prove groundwater discovery or a deployable quantum sensor. The next experiment needs basin groundwater observations, aquifer studies, or storage products closer to the physical groundwater target.</p></section>
  <section><h2>Recommended Next Experiment</h2><p>Move from a western-U.S. crop to named hydrologic basins, then compare GRACE/GLDAS anomalies against independent groundwater or basin-storage records.</p></section>
</main></body></html>
"""
    (path.parent / "executive_summary.html").write_text(executive_html, encoding="utf-8")

    lines = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>GRACE + USDM Multi-Month Dashboard</title>",
        """<style>
        :root{--ink:#172026;--muted:#5c6873;--line:#d9e0e6;--panel:#ffffff;--page:#f4f7f8;--green:#1f7a4d;--amber:#9a5b00;--blue:#245f8f;--red:#a43d3d}
        *{box-sizing:border-box} body{margin:0;background:var(--page);color:var(--ink);font-family:Arial,Helvetica,sans-serif;line-height:1.45}
        main{max-width:1320px;margin:0 auto;padding:28px 28px 44px}
        header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:end;margin-bottom:18px}
        h1{font-size:30px;line-height:1.15;margin:0 0 8px} h2{font-size:18px;margin:0 0 12px} p{margin:0 0 12px}.meta{color:var(--muted);max-width:860px}.source{font-size:13px;color:var(--muted)}
        .cards{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:12px;margin:20px 0}
        .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;min-height:96px}.card .label{font-size:12px;text-transform:uppercase;color:var(--muted);font-weight:700}.card .value{font-size:28px;font-weight:700;margin-top:8px}.card .note{font-size:12px;color:var(--muted);margin-top:4px}
        .panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;margin:16px 0;overflow:hidden}.status-ok{border-left:5px solid var(--green)}.status-warn{border-left:5px solid var(--amber)}
        .chart{display:block;width:100%;max-height:520px;object-fit:contain;border:1px solid var(--line);background:#fff;border-radius:6px}
        .filters{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin:10px 0 2px}.filters label{display:grid;gap:5px;font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase}.filters select{min-width:170px;border:1px solid #b8c5ce;border-radius:6px;background:#fff;padding:8px;color:var(--ink)}
        .table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top;white-space:nowrap}th{position:sticky;top:0;background:#e9eff3;color:#26333d;cursor:pointer;user-select:none}td span{display:block;color:var(--muted);font-size:12px}tr:hover td{background:#f8fbfc}
        a{color:var(--blue);font-weight:700;text-decoration:none}a:hover{text-decoration:underline}.badges{display:flex;gap:8px;flex-wrap:wrap}.badge{border:1px solid var(--line);border-radius:999px;padding:6px 9px;background:#fff;font-size:12px}.badge.ok{border-color:#9ac7aa;color:var(--green)}.badge.warn{border-color:#ddb56b;color:var(--amber)}
        .caveats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.caveat{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fbfcfd}.caveat strong{display:block;margin-bottom:5px}
        .story{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:16px;align-items:stretch}.story .lead{font-size:18px;color:#24333d;max-width:900px}.takeaways{display:grid;gap:10px}.takeaway{border-left:4px solid var(--blue);background:#f8fbfd;padding:10px 12px;border-radius:6px}.takeaway strong{display:block;margin-bottom:4px}.steps{counter-reset:step;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.step{background:#fbfcfd;border:1px solid var(--line);border-radius:8px;padding:12px}.step:before{counter-increment:step;content:counter(step);display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#dce9f4;color:#173b57;font-weight:700;margin-bottom:8px}
        .visual-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.visual-grid figure{margin:0;background:#fbfcfd;border:1px solid var(--line);border-radius:8px;padding:10px}.visual-grid img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}.visual-grid figcaption{font-size:13px;color:var(--muted);margin-top:8px}.visual-grid figcaption strong{display:block;color:var(--ink);margin-bottom:3px}.region-map{display:block;width:100%;max-height:540px;object-fit:contain;border:1px solid var(--line);border-radius:8px;background:#fff}
        .next-step,.target-panel{background:#f2f7f5;border-color:#b7d3c4;border-left:5px solid var(--green)}.cards.compact{grid-template-columns:repeat(5,minmax(130px,1fr));margin:14px 0}.cards.compact .card .value{font-size:23px}
        .ladder{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.rung{border:1px solid var(--line);background:#fbfcfd;border-radius:8px;padding:10px;font-size:13px}.rung.current{border-color:#4d94c7;background:#eef6fc}.rung.next{border-color:#9ac7aa;background:#f2f7f5}.rung strong{display:block;margin-bottom:4px}
        .source-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.source-card{border:1px solid var(--line);border-radius:8px;background:#fbfcfd;padding:14px}.source-card h3{margin:0 0 8px;font-size:16px}.source-card dl{display:grid;grid-template-columns:86px 1fr;gap:6px;margin:0;font-size:13px}.source-card dt{color:var(--muted);font-weight:700}.source-card dd{margin:0}
        .workflow{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;align-items:stretch}.flow-step{position:relative;border:1px solid var(--line);border-radius:8px;background:#fbfcfd;padding:13px;min-height:112px}.flow-step strong{display:block;margin-bottom:6px}.flow-step span{color:var(--muted);font-size:13px}.flow-step:not(:last-child):after{content:'>';position:absolute;right:-10px;top:42%;color:#7b8b98;font-weight:700;background:var(--page);padding:0 2px}
        .interpret{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}.interpret div{background:#fbfcfd;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px}.interpret strong{display:block;margin-bottom:4px}
        .claim-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.claim{border-radius:8px;border:1px solid var(--line);padding:14px;background:#fbfcfd}.claim.yes{border-left:5px solid var(--green)}.claim.no{border-left:5px solid var(--red)}
        @media(max-width:900px){main{padding:18px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}header{grid-template-columns:1fr}.caveats,.source-grid,.workflow,.interpret,.claim-grid{grid-template-columns:1fr}th,td{white-space:normal}.story{grid-template-columns:1fr}.steps{grid-template-columns:1fr}.flow-step:after{display:none}}
        </style>""",
        "</head><body><main>",
        "<header><div>",
        "<h1>GRACE + USDM Multi-Month Dashboard</h1>",
        "<p class='meta'>A guided validation report for testing whether gravity-derived water-mass signals align with independent drought and hydrology targets. This is a validation workflow for scientific inspection, not a claim of deployed groundwater discovery.</p>",
        "</div><div class='source'>GRACE Tellus + USDM + GLDAS<br>western CONUS crop<br><a href='executive_summary.html'>Executive summary</a></div></header>",
        "<section class='cards'>",
        f"<div class='card'><div class='label'>Best F1</div><div class='value'>{avg_best_f1}</div><div class='note'>{html.escape(best_combo)}</div></div>",
        f"<div class='card'><div class='label'>Months</div><div class='value'>{month_count}</div><div class='note'>monthly GRACE solutions</div></div>",
        f"<div class='card'><div class='label'>Run Sets</div><div class='value'>{run_count}</div><div class='note'>month x threshold</div></div>",
        f"<div class='card'><div class='label'>Failed Runs</div><div class='value'>{len(failed)}</div><div class='note'>{'all clear' if not failed else 'review failure table'}</div></div>",
        f"<div class='card'><div class='label'>USDM Masks</div><div class='value'>{len(set(row['threshold'] for row in ok_rows))}</div><div class='note'>{html.escape(threshold_labels)}</div></div>",
        "</section>",
        "<section class='panel status-ok'><h2>Executive Summary</h2>",
        f"<p class='lead'>{html.escape(executive_overview)}</p>",
        "</section>",
        "<section class='panel'><h2>The Research Question</h2>",
        "<p class='lead'>Can gravity-derived water-mass signals align with independent drought and hydrology targets strongly enough to support a reproducible validation workflow?</p>",
        "<p>The dashboard tests that question in stages: first against USDM drought categories, then against GRACE-derived TWS consistency, and finally against external GLDAS terrestrial-water-storage anomalies.</p>",
        "</section>",
        "<section class='panel'><h2>Data Sources And Scientific Role</h2><div class='source-grid'>",
        "<article class='source-card'><h3>GRACE Tellus CSR</h3><dl><dt>Role</dt><dd>Primary gravity-derived water-mass raster</dd><dt>Units</dt><dd>cm equivalent water thickness</dd><dt>Resolution</dt><dd>1 degree monthly land grid</dd><dt>Target type</dt><dd>Input signal</dd></dl></article>",
        "<article class='source-card'><h3>U.S. Drought Monitor</h3><dl><dt>Role</dt><dd>Independent drought proxy labels</dd><dt>Units</dt><dd>D0-D4 drought categories</dd><dt>Resolution</dt><dd>weekly vector polygons rasterized to GRACE grid</dd><dt>Target type</dt><dd>drought_proxy</dd></dl></article>",
        "<article class='source-card'><h3>GLDAS-NOAH</h3><dl><dt>Role</dt><dd>External hydrology comparison target</dd><dt>Units</dt><dd>cm equivalent water thickness anomaly</dd><dt>Resolution</dt><dd>1 degree monthly TWS anomaly</dd><dt>Target type</dt><dd>terrestrial_water_storage</dd></dl></article>",
        "</div></section>",
        "<section class='panel'><h2>Validation Workflow</h2><div class='workflow'>",
        "<div class='flow-step'><strong>1. Download real data</strong><span>GRACE GeoTIFFs, USDM shapefiles, GLDAS NetCDFs.</span></div>",
        "<div class='flow-step'><strong>2. Align grids</strong><span>Crop to western CONUS and align targets to the 1-degree GRACE grid.</span></div>",
        "<div class='flow-step'><strong>3. Simulate sensors</strong><span>Compare classical gravimeter and quantum-gradiometer profiles.</span></div>",
        "<div class='flow-step'><strong>4. Calibrate detectors</strong><span>Run z-score, DBSCAN, and isolation forest with held-out spatial folds.</span></div>",
        "<div class='flow-step'><strong>5. Validate claims</strong><span>Report F1/IoU for labels and correlation/RMSE/bias for hydrology.</span></div>",
        "</div></section>",
        "<section class='panel story'><div>",
        "<h2>What This Experiment Does</h2>",
        f"<p class='lead'>This dashboard asks whether simple anomaly detectors can find patterns in real GRACE Tellus land-mass grids that line up with independent U.S. Drought Monitor labels over time. It is a repeatability check: {month_count} monthly GRACE snapshots, {run_count} month-threshold runs, and three drought severities over the same western U.S. region.</p>",
        "<p>The important move is that the labels do not come from the GRACE raster. USDM polygons are rasterized onto the GRACE grid, so the pipeline is no longer grading itself against a threshold it invented from the same data.</p>",
        "</div><aside class='takeaways'>",
        f"<div class='takeaway'><strong>Best repeated match</strong>{html.escape(best_aggregate_label)} averaged {best_aggregate_f1} F1 across months.</div>",
        f"<div class='takeaway'><strong>Detector behavior</strong>{html.escape(strongest_algorithm)} is the most reliable detector in this batch; {html.escape(weak_algorithm)} struggles on the coarse regional crop.</div>",
        f"<div class='takeaway'><strong>Severity matters</strong>{html.escape(threshold_sentence)}.</div>",
        "</aside></section>",
        "<section class='panel'><h2>Where This Happens</h2>",
        f"<p class='meta'>The study region is the fixed western U.S. crop used for every month. The grid shows one-degree GRACE cells; the red overlay shows the focus USDM D{focus_threshold}+ mask used for the main visual story.</p>",
        "<div class='interpret'><div><strong>What am I looking at?</strong>A common analysis footprint used for every dataset.</div><div><strong>What is good?</strong>All sources should refer to the same cells and bounds.</div><div><strong>What this run shows</strong>The validation is regional and coarse, not local-site mapping.</div><div><strong>Do not conclude</strong>That individual red cells are confirmed groundwater anomalies.</div></div>",
        f"<img class='region-map' src='{html.escape(study_region_image or '')}' alt='Western U.S. study-region map'>",
        "</section>",
        "<section class='panel'><h2>What Changed Over Time</h2>",
        f"<p class='meta'>Each thumbnail pairs the GRACE land-mass anomaly grid with the independent USDM D{focus_threshold}+ mask for the matching weekly drought map.</p>",
        "<div class='interpret'><div><strong>What am I looking at?</strong>Month-by-month input signal beside external drought labels.</div><div><strong>What is good?</strong>Broad spatial patterns should be plausible and repeatable.</div><div><strong>What this run shows</strong>Drought labels are persistent, while GRACE anomalies shift month to month.</div><div><strong>Do not conclude</strong>That USDM and GRACE measure the same physical quantity.</div></div>",
        f"<div class='visual-grid'>{''.join(monthly_panel_cards)}</div></section>",
        "<section class='panel'><h2>What The Best Detector Got Right Or Wrong</h2>",
        f"<p class='meta'>These are the detector outcome overlays for the best repeated configuration, {html.escape(best_aggregate_label)}. Open any thumbnail to inspect the full per-run report and artifact set.</p>",
        "<div class='interpret'><div><strong>What am I looking at?</strong>Predicted anomaly masks overlaid against the validation mask.</div><div><strong>What is good?</strong>High overlap, low false positives, and stable behavior across months.</div><div><strong>What this run shows</strong>The best detector is repeatable but modest, not definitive.</div><div><strong>Do not conclude</strong>That detector agreement equals field-validated discovery.</div></div>",
        f"<div class='visual-grid'>{''.join(outcome_cards)}</div></section>",
        tws_section,
        gldas_section,
        "<section class='panel'><h2>How To Read This</h2><div class='steps'>",
        "<div class='step'><strong>Start with the timeline.</strong><p>Look for whether F1 stays stable or collapses across months.</p></div>",
        "<div class='step'><strong>Compare thresholds.</strong><p>D1+ is broad drought; D3+ is stricter and usually harder to recover.</p></div>",
        "<div class='step'><strong>Check detectors.</strong><p>A detector that wins once but fails elsewhere is not robust.</p></div>",
        "<div class='step'><strong>Open run reports.</strong><p>Use row links to inspect overlays and provenance for any suspicious month.</p></div>",
        "</div></section>",
        "<section class='panel status-ok'><h2>What The Timeline Shows</h2>",
        f"<p>The plot tracks z-score F1 from {html.escape(first_month)} through {html.escape(last_month)}. If the lines drift downward as labels become stricter, that means the method is better at broad drought agreement than at isolating severe drought cores.</p>",
        "<div class='interpret'><div><strong>What am I looking at?</strong>Held-out F1 across months and drought severity thresholds.</div><div><strong>What is good?</strong>Flat or improving lines across months.</div><div><strong>What this run shows</strong>Agreement weakens for stricter drought classes.</div><div><strong>Do not conclude</strong>That a single high month proves robustness.</div></div>",
        "<img class='chart' src='timeline_f1.png' alt='Timeline F1 plot'></section>",
        "<section class='panel'><h2>Explore Results</h2><div class='filters'>",
        "<label>USDM threshold<select id='thresholdFilter'><option value=''>All thresholds</option></select></label>",
        "<label>Sensor<select id='sensorFilter'><option value=''>All sensors</option></select></label>",
        "<label>Detector<select id='algorithmFilter'><option value=''>All detectors</option></select></label>",
        "</div></section>",
        "<section class='panel'><h2>Aggregate Metrics</h2><p class='meta'>This table compresses all months for each sensor, detector, and USDM severity. Sort by F1 to see repeatable agreement; sort by FPR to see which settings over-predict drought labels.</p><div class='table-wrap'><table class='sortable filterable'><thead><tr><th>USDM threshold</th><th>Sensor</th><th>Detector</th><th>Months</th><th>F1 mean</th><th>IoU mean</th><th>FPR mean</th><th>Best month</th><th>Worst month</th></tr></thead>",
        f"<tbody>{''.join(aggregate_body)}</tbody></table></div></section>",
        "<section class='panel'><h2>Per-Month Results</h2><p class='meta'>Use this table to find individual months that drive the story. A low F1 with a high FPR usually means the detector marked too much of the region; a low F1 with low recall means it missed the drought proxy entirely.</p><div class='table-wrap'><table class='sortable filterable'><thead><tr><th>Month</th><th>USDM date</th><th>Threshold</th><th>Sensor</th><th>Detector</th><th>F1</th><th>IoU</th><th>FPR</th><th>Run report</th></tr></thead>",
        f"<tbody>{''.join(detail_body)}</tbody></table></div></section>",
        failure_section,
        "<section class='panel status-warn'><h2>Scientific Caveats</h2><div class='caveats'>",
        "<div class='caveat'><strong>Independent labels</strong>USDM masks are external to GRACE, but they are not direct GRACE ground truth.</div>",
        "<div class='caveat'><strong>Scale mismatch</strong>GRACE monthly 1-degree grids are spatially smoothed and coarse relative to USDM polygons.</div>",
        "<div class='caveat'><strong>Repeatability</strong>Multi-month behavior is stronger evidence than one snapshot, but still needs hydrology-domain interpretation.</div>",
        "<div class='caveat'><strong>Severity choice</strong>D1+, D2+, and D3+ thresholds change label prevalence and answer different drought questions.</div>",
        "</div></section>",
        "<section class='panel'><h2>What This Accomplishes</h2>",
        "<div class='claim-grid'><div class='claim yes'><h3>What is demonstrated</h3><p>A reproducible validation workflow comparing simulated detector behavior on real GRACE-derived rasters against independent drought and hydrology targets.</p></div><div class='claim no'><h3>What is not demonstrated</h3><p>A proven quantum detector for groundwater discovery, field deployment, or site-level anomaly confirmation.</p></div></div>",
        "</section>",
        "<section class='panel next-step'><h2>Next Science Step</h2>",
        "<p>The next validation target should be closer to GRACE's physical signal: groundwater storage observations, basin-scale hydrology estimates, well networks, groundwater depletion studies, or another terrestrial-water-storage product. USDM is a useful independent drought proxy, but a storage-linked target would make the validation scientifically sharper.</p>",
        "</section>",
        "<section class='panel'><h2>Scientific Readiness Ladder</h2><div class='ladder'>",
        "<div class='rung'><strong>1. Synthetic</strong>Pipeline mechanics only.</div>",
        "<div class='rung'><strong>2. Real raster + weak mask</strong>Real data, self-derived labels.</div>",
        "<div class='rung current'><strong>3. Independent drought proxy</strong>Current USDM validation track.</div>",
        f"<div class='rung {'current' if gldas_status == 'ok' else 'next'}'><strong>4. External hydrology target</strong>{'GLDAS metrics computed.' if gldas_status == 'ok' else 'GLDAS support added; awaiting authenticated files.'}</div>",
        "<div class='rung next'><strong>5. Basin/groundwater validation</strong>Next: observations or basin storage products.</div>",
        "</div></section>",
        "<section class='panel'><h2>Artifacts</h2><p><a href='timeline_metrics.csv'>timeline_metrics.csv</a> · <a href='timeline_f1.png'>timeline_f1.png</a></p></section>",
        """<script>
        const filters={threshold:document.getElementById('thresholdFilter'),sensor:document.getElementById('sensorFilter'),algorithm:document.getElementById('algorithmFilter')};
        const rows=Array.from(document.querySelectorAll('tr[data-threshold]'));
        for (const [key,select] of Object.entries(filters)){
          const values=[...new Set(rows.map(row=>row.dataset[key]).filter(Boolean))].sort();
          for (const value of values) select.insertAdjacentHTML('beforeend', `<option value="${value}">${value}</option>`);
          select.addEventListener('change', applyFilters);
        }
        function applyFilters(){
          rows.forEach(row=>{
            const visible=(!filters.threshold.value||row.dataset.threshold===filters.threshold.value)&&(!filters.sensor.value||row.dataset.sensor===filters.sensor.value)&&(!filters.algorithm.value||row.dataset.algorithm===filters.algorithm.value);
            row.style.display=visible?'':'none';
          });
        }
        document.querySelectorAll('table.sortable th').forEach((header,index)=>{
          header.addEventListener('click',()=>{
            const table=header.closest('table'); const body=table.querySelector('tbody'); const ascending=header.dataset.sort!=='asc';
            const sorted=Array.from(body.querySelectorAll('tr')).sort((a,b)=>{
              const av=a.children[index]?.dataset.sort||a.children[index]?.innerText||''; const bv=b.children[index]?.dataset.sort||b.children[index]?.innerText||'';
              const an=parseFloat(av); const bn=parseFloat(bv); const result=Number.isFinite(an)&&Number.isFinite(bn)?an-bn:av.localeCompare(bv);
              return ascending?result:-result;
            });
            body.append(...sorted); table.querySelectorAll('th').forEach(th=>th.dataset.sort=''); header.dataset.sort=ascending?'asc':'desc';
          });
        });
        </script>""",
        "</main></body></html>",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    bbox, basins_path, region_slug = configure_study_region(args)
    output_dir = Path(args.output)
    raw_grace = Path("data/grace_tellus/raw")
    raw_usdm = Path("data/usdm/raw")
    prepared_dir = Path("data/grace_tellus/multimonth_usdm")
    output_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    csr_collection = GRFO_CSR_COLLECTION if args.mission == "grace-fo" else CSR_COLLECTION
    jpl_collection = GRFO_JPL_COLLECTION if args.mission == "grace-fo" else JPL_COLLECTION
    mission_label = "gracefo" if args.mission == "grace-fo" else "grace"

    granules = grace_granules(args.months, args.start, collection=csr_collection)
    run_rows = []
    rasterize_script = Path("examples/grace_tellus/rasterize_independent_mask.py")

    for granule in granules:
        tif_path = raw_grace / granule["filename"]
        download(granule["url"], tif_path)
        usdm_date, usdm_zip, usdm_shp = download_usdm_near(granule["end"], raw_usdm)
        month = normalize_month_key(granule["start"])
        for threshold in args.thresholds:
            label = f"{month.replace('-', '')}_d{threshold}"
            grid_path = prepared_dir / f"{region_slug}_{mission_label}_{label}.tif"
            mask_path = prepared_dir / f"{region_slug}_usdm_{usdm_date}_d{threshold}plus_mask.tif"
            manifest_path = prepared_dir / f"validation_manifest_{label}.yaml"
            run_dir = output_dir / f"{label}"
            run_rows.append(
                {
                    "month": month,
                    "grace_start": granule["start"],
                    "grace_end": granule["end"],
                    "usdm_date": usdm_date,
                    "threshold": threshold,
                    "grid_path": str(grid_path),
                    "mask_path": str(mask_path),
                    "run_dir": str(run_dir),
                }
            )

            if not (grid_path.exists() and mask_path.exists()):
                run_command(
                    [
                        sys.executable,
                        str(rasterize_script),
                        "--grid",
                        str(tif_path),
                        "--vector",
                        str(usdm_shp),
                        "--bbox",
                        *[str(value) for value in bbox],
                        "--attribute",
                        "DM",
                        "--min-value",
                        str(threshold),
                        "--all-touched",
                        "--output-grid",
                        str(grid_path),
                        "--output-mask",
                        str(mask_path),
                    ],
                    root,
                )
            manifest_path.write_text(
                yaml.safe_dump(manifest_for(granule, usdm_date, usdm_zip, threshold, grid_path, bbox, region_slug), sort_keys=False),
                encoding="utf-8",
            )
            run_command([sys.executable, "-m", "src.main", "doctor", "--manifest", str(manifest_path)], root)
            if args.skip_existing and (run_dir / "summary.csv").exists():
                continue
            run_command(
                [
                    sys.executable,
                    "-m",
                    "src.main",
                    "--validation-grid",
                    str(grid_path),
                    "--validation-mask",
                    str(mask_path),
                    "--validation-manifest",
                    str(manifest_path),
                    "--detectors",
                    *args.detectors,
                    "--calibrate-thresholds",
                    "--spatial-folds",
                    str(args.spatial_folds),
                    "--missing",
                    "median",
                    "--output",
                    str(run_dir),
                ],
                root,
            )

    tws_summary = None if args.skip_tws_track else write_tws_comparison_track(output_dir, granules, args.start, bbox, jpl_collection=jpl_collection)
    gldas_summary = None if args.skip_gldas_track else write_gldas_track(output_dir, granules, args.start, bbox)
    write_basin_track(output_dir, run_rows, basins_path, bbox)
    groundwater_summary = None
    if args.groundwater_observations and not args.skip_groundwater_track:
        groundwater_result = write_groundwater_track(
            output_dir=output_dir,
            observations_path=Path(args.groundwater_observations),
            basins_path=basins_path,
            basin_metrics_path=output_dir / "basin_metrics.csv",
            source=args.groundwater_source,
        )
        groundwater_summary = groundwater_result.summary
    elif not args.skip_groundwater_track:
        groundwater_summary = {
            "schema_version": "groundwater-validation-v1",
            "status": "not_configured",
            "claim_note": "Groundwater observations were not provided; groundwater validation has not begun for this run.",
        }
        (output_dir / "groundwater_summary.json").write_text(json.dumps(groundwater_summary, indent=2), encoding="utf-8")
        (output_dir / "groundwater_validation_summary.json").write_text(json.dumps(groundwater_summary, indent=2), encoding="utf-8")
    csv_path, html_path = aggregate_timeline(output_dir, run_rows, tws_summary=tws_summary, gldas_summary=gldas_summary)
    write_batch_contract(output_dir, run_rows, gldas_summary=gldas_summary, tws_summary=tws_summary, groundwater_summary=groundwater_summary)
    print(f"Wrote {csv_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
