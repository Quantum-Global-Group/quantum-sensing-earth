from pathlib import Path
import json

import numpy as np
import pandas as pd
import yaml


def load_placeholder_geospatial_context():
    return {"mode": "synthetic", "datasets": ["synthetic_gravity"], "future_extensions": ["GRACE-FO", "SMAP", "GLDAS"]}


def load_gravity_grid(path, mask_path=None):
    """Load a validation gravity grid from CSV or NPY.

    CSV files may be rectangular grids or long-form records with columns
    named x, y, and gravity. The optional mask uses the same shape and is
    treated as a boolean anomaly mask.
    """
    grid, _ = _load_grid_with_metadata(path)
    mask = _load_grid(mask_path, apply_nodata=False).astype(bool) if mask_path else np.zeros_like(grid, dtype=bool)
    if grid.shape != mask.shape:
        raise ValueError(f"Grid shape {grid.shape} does not match mask shape {mask.shape}")
    return grid.astype(float), mask


def load_validation_dataset(path, mask_path=None, manifest_path=None):
    grid, raster_metadata = _load_grid_with_metadata(path)
    mask = _load_grid(mask_path, apply_nodata=False).astype(bool) if mask_path else np.zeros_like(grid, dtype=bool)
    if grid.shape != mask.shape:
        raise ValueError(f"Grid shape {grid.shape} does not match mask shape {mask.shape}")

    manifest = load_validation_manifest(manifest_path) if manifest_path else {}
    dataset_manifest = manifest.get("dataset", {})
    coordinate_metadata = {
        "crs": raster_metadata.get("crs") or dataset_manifest.get("crs"),
        "resolution": raster_metadata.get("resolution") or dataset_manifest.get("resolution"),
        "bounds": raster_metadata.get("bounds") or dataset_manifest.get("bounds"),
        "pixel_to_coordinate": raster_metadata.get("pixel_to_coordinate")
        or dataset_manifest.get("pixel_to_coordinate")
        or "No embedded transform; pixel coordinates are row,column indices.",
    }
    metadata = {
        "grid_path": str(Path(path)),
        "mask_path": str(Path(mask_path)) if mask_path else None,
        "shape": [int(grid.shape[0]), int(grid.shape[1])],
        "format": Path(path).suffix.lower().lstrip("."),
        "raster": raster_metadata,
        "coordinates": coordinate_metadata,
        "manifest": manifest,
    }
    return grid.astype(float), mask, metadata


def load_validation_manifest(path):
    with Path(path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_validation_anomalies(path):
    if not path:
        return []
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_grid(path, apply_nodata=True):
    grid, _ = _load_grid_with_metadata(path, apply_nodata=apply_nodata)
    return grid


def _load_grid_with_metadata(path, apply_nodata=True):
    path = Path(path)
    if path.suffix.lower() == ".npy":
        grid = np.load(path)
        return grid, {}
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
        if {"x", "y", "gravity"}.issubset(frame.columns):
            pivot = frame.pivot(index="y", columns="x", values="gravity")
            return pivot.sort_index().sort_index(axis=1).to_numpy(), {}
        return pd.read_csv(path, header=None).to_numpy(), {}
    if path.suffix.lower() in {".tif", ".tiff"}:
        return _load_raster(path, apply_nodata=apply_nodata)
    raise ValueError(f"Unsupported validation grid format: {path.suffix}. Use .csv, .npy, .tif, or .tiff.")


def _load_raster(path, apply_nodata=True):
    try:
        import rasterio
    except ImportError as exc:
        raise ImportError("GeoTIFF support requires optional dependency rasterio. Install with `pip install rasterio`.") from exc

    with rasterio.open(path) as dataset:
        grid = dataset.read(1)
        nodata = dataset.nodata
        if nodata is not None and apply_nodata:
            grid = grid.astype(float)
            grid[grid == nodata] = np.nan
        transform = dataset.transform
        bounds = dataset.bounds
        metadata = {
            "driver": dataset.driver,
            "crs": str(dataset.crs) if dataset.crs else None,
            "transform": list(transform)[:6],
            "bounds": {
                "left": float(bounds.left),
                "bottom": float(bounds.bottom),
                "right": float(bounds.right),
                "top": float(bounds.top),
            },
            "resolution": {"x": float(dataset.res[0]), "y": float(dataset.res[1])},
            "width": int(dataset.width),
            "height": int(dataset.height),
            "nodata": None if nodata is None else float(nodata),
            "pixel_to_coordinate": "Affine transform maps pixel column,row to x,y using rasterio transform.",
        }
    return grid, metadata
