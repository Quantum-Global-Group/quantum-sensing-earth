import numpy as np
import pytest

from src.data.load_geospatial_data import load_gravity_grid, load_validation_anomalies, load_validation_dataset


def test_load_gravity_grid_from_rectangular_csv(tmp_path):
    grid_path = tmp_path / "grid.csv"
    mask_path = tmp_path / "mask.csv"
    grid_path.write_text("1,2\n3,4\n", encoding="utf-8")
    mask_path.write_text("0,1\n0,0\n", encoding="utf-8")

    grid, mask = load_gravity_grid(grid_path, mask_path)

    assert grid.shape == (2, 2)
    assert np.array_equal(mask, np.array([[False, True], [False, False]]))


def test_load_validation_dataset_with_manifest(tmp_path):
    grid_path = tmp_path / "grid.csv"
    manifest_path = tmp_path / "manifest.yaml"
    grid_path.write_text("1,2\n3,4\n", encoding="utf-8")
    manifest_path.write_text("dataset:\n  name: Demo\n  units: mGal\n", encoding="utf-8")

    grid, mask, metadata = load_validation_dataset(grid_path, manifest_path=manifest_path)

    assert grid.shape == (2, 2)
    assert mask.shape == (2, 2)
    assert metadata["manifest"]["dataset"]["name"] == "Demo"


def test_load_validation_dataset_preserves_manifest_coordinates(tmp_path):
    grid_path = tmp_path / "grid.csv"
    manifest_path = tmp_path / "manifest.yaml"
    grid_path.write_text("1,2\n3,4\n", encoding="utf-8")
    manifest_path.write_text(
        "dataset:\n  name: Demo\n  crs: EPSG:32613\n  resolution: 250 m pixels\n",
        encoding="utf-8",
    )

    _, _, metadata = load_validation_dataset(grid_path, manifest_path=manifest_path)

    assert metadata["coordinates"]["crs"] == "EPSG:32613"
    assert metadata["coordinates"]["resolution"] == "250 m pixels"


def test_load_validation_anomalies_from_json(tmp_path):
    path = tmp_path / "anomalies.json"
    path.write_text('[{"id": "a1", "center_x": 1, "center_y": 2, "sigma": 3.0}]', encoding="utf-8")

    anomalies = load_validation_anomalies(path)

    assert anomalies[0]["id"] == "a1"
    assert anomalies[0]["center_y"] == 2


def test_load_validation_dataset_from_geotiff_preserves_raster_metadata(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    tif_path = tmp_path / "grid.tif"
    data = np.array([[1.0, -9999.0], [3.0, 4.0]], dtype=np.float32)
    transform = from_origin(500000.0, 4100000.0, 30.0, 30.0)
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype=data.dtype,
        crs="EPSG:32613",
        transform=transform,
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data, 1)

    grid, _, metadata = load_validation_dataset(tif_path)

    assert np.isnan(grid[0, 1])
    assert metadata["raster"]["crs"] == "EPSG:32613"
    assert metadata["raster"]["bounds"] == {"left": 500000.0, "bottom": 4099940.0, "right": 500060.0, "top": 4100000.0}
    assert metadata["raster"]["resolution"] == {"x": 30.0, "y": 30.0}
    assert metadata["raster"]["nodata"] == -9999.0
    assert metadata["coordinates"]["crs"] == "EPSG:32613"
