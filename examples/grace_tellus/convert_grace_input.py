"""Convert a GRACE Tellus GeoTIFF or netCDF input into an MVP validation raster.

This script is intentionally conservative. It copies GeoTIFFs while preserving
metadata, and provides a small netCDF path when optional xarray/rasterio support
is available. Real runs should record every crop, reprojection, and scaling
choice in validation_manifest.yaml.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def copy_geotiff(input_path: Path, output_path: Path) -> None:
    import rasterio

    with rasterio.open(input_path) as src:
        profile = src.profile.copy()
        data = src.read(1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data, 1)


def convert_netcdf(input_path: Path, output_path: Path, variable: str | None) -> None:
    try:
        import rasterio
        from rasterio.transform import from_origin
        import xarray as xr
    except ImportError as exc:
        raise SystemExit(
            "netCDF conversion requires optional packages xarray and rasterio. "
            "Install them in your analysis environment before converting GRACE netCDF files."
        ) from exc

    dataset = xr.open_dataset(input_path)
    variable_name = variable or next(iter(dataset.data_vars))
    array = dataset[variable_name]
    if array.ndim == 3:
        array = array.isel({array.dims[0]: 0})
    grid = np.asarray(array.values, dtype=np.float32)

    lon_name = "lon" if "lon" in array.coords else "longitude"
    lat_name = "lat" if "lat" in array.coords else "latitude"
    lon = np.asarray(array.coords[lon_name].values, dtype=float)
    lat = np.asarray(array.coords[lat_name].values, dtype=float)
    x_res = float(abs(lon[1] - lon[0])) if lon.size > 1 else 1.0
    y_res = float(abs(lat[1] - lat[0])) if lat.size > 1 else 1.0
    west = float(np.min(lon) - x_res / 2.0)
    north = float(np.max(lat) + y_res / 2.0)
    transform = from_origin(west, north, x_res, y_res)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype=grid.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(grid, 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert GRACE Tellus input data for MVP validation.")
    parser.add_argument("--input", required=True, help="Input GRACE Tellus .tif/.tiff or .nc/.netcdf file.")
    parser.add_argument("--output", required=True, help="Output validation GeoTIFF path.")
    parser.add_argument("--variable", help="netCDF variable name. Defaults to the first data variable.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    suffix = input_path.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        copy_geotiff(input_path, output_path)
    elif suffix in {".nc", ".netcdf"}:
        convert_netcdf(input_path, output_path, args.variable)
    else:
        raise SystemExit("Unsupported input format. Use .tif, .tiff, .nc, or .netcdf.")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
