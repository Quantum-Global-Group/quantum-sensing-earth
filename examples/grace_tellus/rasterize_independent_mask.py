"""Crop a GRACE GeoTIFF and rasterize an independent vector mask onto it.

This script is intentionally small and dependency-light: it uses rasterio for
GeoTIFF I/O and pyshp for shapefile reading. It is meant for documented
validation workflows where the mask provenance is independent of the GRACE
grid, such as U.S. Drought Monitor drought classes or basin polygons.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop a GRACE raster and rasterize an independent vector label.")
    parser.add_argument("--grid", required=True, help="Input GRACE GeoTIFF.")
    parser.add_argument("--vector", required=True, help="Input shapefile in the same CRS as the grid.")
    parser.add_argument("--output-grid", required=True, help="Cropped GRACE GeoTIFF output.")
    parser.add_argument("--output-mask", required=True, help="Rasterized uint8 mask GeoTIFF output.")
    parser.add_argument(
        "--bbox",
        required=True,
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Crop bounds in grid coordinates.",
    )
    parser.add_argument("--attribute", default="DM", help="Vector attribute used for thresholding.")
    parser.add_argument("--min-value", type=float, default=1.0, help="Minimum attribute value to include in the mask.")
    parser.add_argument("--all-touched", action="store_true", help="Include pixels touched by a vector polygon.")
    return parser.parse_args()


def matching_geometries(vector_path: Path, attribute: str, min_value: float):
    try:
        import shapefile
    except ImportError as exc:
        raise ImportError("This workflow requires pyshp. Install with `pip install -e .[geo]`.") from exc

    reader = shapefile.Reader(str(vector_path))
    names = [field[0] for field in reader.fields[1:]]
    if attribute not in names:
        raise ValueError(f"Attribute {attribute!r} not found in {vector_path}. Available fields: {names}")
    attr_index = names.index(attribute)

    geometries = []
    for shape_record in reader.iterShapeRecords():
        value = shape_record.record[attr_index]
        if value is not None and float(value) >= min_value:
            geometries.append(shape_record.shape.__geo_interface__)
    if not geometries:
        raise ValueError(f"No vector geometries matched {attribute} >= {min_value}")
    return geometries


def crop_and_rasterize(args: argparse.Namespace) -> None:
    try:
        import rasterio
        from rasterio.features import rasterize
        from rasterio.windows import from_bounds
    except ImportError as exc:
        raise ImportError("This workflow requires rasterio. Install with `pip install -e .[geo]`.") from exc

    grid_path = Path(args.grid)
    vector_path = Path(args.vector)
    output_grid = Path(args.output_grid)
    output_mask = Path(args.output_mask)
    output_grid.parent.mkdir(parents=True, exist_ok=True)
    output_mask.parent.mkdir(parents=True, exist_ok=True)

    min_lon, min_lat, max_lon, max_lat = args.bbox
    geometries = matching_geometries(vector_path, args.attribute, args.min_value)

    with rasterio.open(grid_path) as src:
        window = from_bounds(min_lon, min_lat, max_lon, max_lat, src.transform).round_offsets().round_lengths()
        grid = src.read(1, window=window)
        transform = src.window_transform(window)
        profile = src.profile.copy()
        profile.update(height=grid.shape[0], width=grid.shape[1], transform=transform, count=1)
        if profile.get("nodata") is None:
            profile.update(nodata=-99999.0)

        mask = rasterize(
            [(geometry, 1) for geometry in geometries],
            out_shape=grid.shape,
            transform=transform,
            fill=0,
            dtype="uint8",
            all_touched=args.all_touched,
        )

    with rasterio.open(output_grid, "w", **profile) as dst:
        dst.write(grid, 1)

    mask_profile = profile.copy()
    mask_profile.update(dtype="uint8", nodata=0)
    with rasterio.open(output_mask, "w", **mask_profile) as dst:
        dst.write(mask.astype(np.uint8), 1)

    print(f"Wrote cropped grid: {output_grid}")
    print(f"Wrote independent mask: {output_mask}")
    print(f"Mask pixels: {int(mask.sum())} / {mask.size}")


def main() -> None:
    crop_and_rasterize(parse_args())


if __name__ == "__main__":
    main()
