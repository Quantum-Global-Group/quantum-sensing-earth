"""Create a weak-label mask from a GRACE-like raster threshold.

WARNING: A mask derived from the same raster being evaluated is not independent
ground truth. Use this only to exercise the software workflow or as a clearly
documented weak label.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


WARNING = (
    "WEAK LABEL WARNING: this mask is threshold-derived from the validation grid. "
    "It is not independent ground truth and should not be used as scientific proof."
)


def make_mask(input_path: Path, output_path: Path, threshold: float, mode: str) -> None:
    import rasterio

    with rasterio.open(input_path) as src:
        grid = src.read(1)
        profile = src.profile.copy()
        nodata = src.nodata

    valid = np.ones(grid.shape, dtype=bool)
    if nodata is not None:
        valid &= grid != nodata
    valid &= np.isfinite(grid)
    if mode == "below":
        mask = valid & (grid <= threshold)
    elif mode == "above":
        mask = valid & (grid >= threshold)
    else:
        mask = valid & (np.abs(grid) >= abs(threshold))

    profile.update(dtype="uint8", nodata=0, count=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(mask.astype(np.uint8), 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a weak-label anomaly mask from a GRACE raster threshold.")
    parser.add_argument("--input", required=True, help="Input validation raster.")
    parser.add_argument("--output", required=True, help="Output mask GeoTIFF.")
    parser.add_argument("--threshold", required=True, type=float, help="Threshold in raster units, usually cm equivalent water thickness.")
    parser.add_argument("--mode", choices=["below", "above", "absolute"], default="below", help="Threshold direction.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(WARNING)
    make_mask(Path(args.input), Path(args.output), args.threshold, args.mode)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
