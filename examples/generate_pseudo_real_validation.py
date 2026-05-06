from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.generate_synthetic_gravity import generate_synthetic_gravity_field


def main():
    output_dir = Path(__file__).resolve().parent
    grid, mask, anomalies = generate_synthetic_gravity_field(
        grid_size=(96, 96),
        anomaly_count=7,
        intensity_range=(-0.9, -0.15),
        sigma_range=(3.5, 14.0),
        seed=2026,
        background_std=0.025,
        terrain_gradient=0.035,
        correlated_noise_radius=3,
        anomaly_depth_range=(0.7, 1.8),
        anomaly_size_scale=1.1,
        return_metadata=True,
    )
    np.savetxt(output_dir / "pseudo_real_gravity_grid.csv", grid, delimiter=",", fmt="%.6f")
    np.savetxt(output_dir / "pseudo_real_validation_mask.csv", mask.astype(int), delimiter=",", fmt="%d")
    (output_dir / "pseudo_real_anomalies.json").write_text(
        __import__("json").dumps(anomalies, indent=2),
        encoding="utf-8",
    )
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError:
        return

    nodata = -9999.0
    raster_grid = grid.astype(np.float32)
    raster_grid[0, 0] = nodata
    mask_grid = mask.astype(np.uint8)
    transform = from_origin(500000.0, 4100000.0, 250.0, 250.0)
    with rasterio.open(
        output_dir / "pseudo_real_gravity_grid.tif",
        "w",
        driver="GTiff",
        height=raster_grid.shape[0],
        width=raster_grid.shape[1],
        count=1,
        dtype=raster_grid.dtype,
        crs="EPSG:32613",
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(raster_grid, 1)
    with rasterio.open(
        output_dir / "pseudo_real_validation_mask.tif",
        "w",
        driver="GTiff",
        height=mask_grid.shape[0],
        width=mask_grid.shape[1],
        count=1,
        dtype=mask_grid.dtype,
        crs="EPSG:32613",
        transform=transform,
        nodata=0,
    ) as dataset:
        dataset.write(mask_grid, 1)


if __name__ == "__main__":
    main()
