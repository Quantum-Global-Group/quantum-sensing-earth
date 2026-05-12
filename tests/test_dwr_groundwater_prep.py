import zipfile
from pathlib import Path

import pandas as pd

import examples.central_valley.prepare_dwr_groundwater as dwr_prep
from examples.central_valley.prepare_dwr_groundwater import main as prepare_dwr_groundwater


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "central_valley"


def test_prepare_dwr_groundwater_merges_station_measurement_csvs(tmp_path):
    output = tmp_path / "dwr_groundwater_clean.csv"
    manifest = tmp_path / "dwr_groundwater_manifest.yaml"

    result = prepare_dwr_groundwater(
        [
            "--stations",
            str(FIXTURES / "tiny_dwr_stations.csv"),
            "--measurements",
            str(FIXTURES / "tiny_dwr_measurements.csv"),
            "--basins",
            str(FIXTURES / "tiny_b118_basins.geojson"),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--drop-unassigned",
        ]
    )

    frame = pd.read_csv(output)
    assert result["rows"] == 6
    assert result["basin_assigned_rows"] == 6
    assert set(frame["basin_id"]) == {"5-022.01", "5-022.15"}
    assert {"raw_value", "raw_value_column", "raw_source_file"}.issubset(frame.columns)
    assert manifest.exists()


def test_prepare_dwr_groundwater_reads_zip_export(tmp_path):
    archive = tmp_path / "dwr_bulk.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(FIXTURES / "tiny_dwr_stations.csv", arcname="stations.csv")
        zf.write(FIXTURES / "tiny_dwr_measurements.csv", arcname="periodic_groundwater_measurements.csv")
    output = tmp_path / "from_zip.csv"

    prepare_dwr_groundwater(
        [
            "--input",
            str(archive),
            "--basins",
            str(FIXTURES / "tiny_b118_basins.geojson"),
            "--output",
            str(output),
            "--drop-unassigned",
        ]
    )

    frame = pd.read_csv(output)
    assert len(frame) == 6
    assert set(frame["month"]) == {"2025-01", "2025-02", "2025-03"}


def test_prepare_dwr_groundwater_filters_measurement_months(tmp_path):
    output = tmp_path / "filtered.csv"
    manifest = tmp_path / "filtered_manifest.yaml"

    prepare_dwr_groundwater(
        [
            "--stations",
            str(FIXTURES / "tiny_dwr_stations.csv"),
            "--measurements",
            str(FIXTURES / "tiny_dwr_measurements.csv"),
            "--basins",
            str(FIXTURES / "tiny_b118_basins.geojson"),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--start-month",
            "2025-02",
            "--end-month",
            "2025-02",
            "--drop-unassigned",
        ]
    )

    frame = pd.read_csv(output)
    assert len(frame) == 2
    assert set(frame["month"]) == {"2025-02"}


def test_prepare_dwr_groundwater_download_only_uses_official_manifest(tmp_path, monkeypatch):
    download_dir = tmp_path / "raw"

    def fake_download_dwr_periodic(path, resource_mode):
        path.mkdir(parents=True, exist_ok=True)
        stations = path / "stations.csv"
        measurements = path / "measurements.csv"
        stations.write_text("site_id\nA\n", encoding="utf-8")
        measurements.write_text("site_id,date,value\nA,2025-01-01,10\n", encoding="utf-8")
        manifest = {
            "resources": {
                "stations": {"path": str(stations), "url": "https://data.cnra.ca.gov/stations.csv"},
                "measurements": {"path": str(measurements), "url": "https://data.cnra.ca.gov/measurements.csv"},
            }
        }
        return {"stations": stations, "measurements": measurements}, manifest

    monkeypatch.setattr(dwr_prep, "download_dwr_periodic", fake_download_dwr_periodic)
    result = prepare_dwr_groundwater(["--download-dwr-periodic", "--download-only", "--download-dir", str(download_dir)])

    assert result["download_dir"] == str(download_dir)
    assert "stations" in result["resources"]
    assert "measurements" in result["resources"]


def test_discover_dwr_resources_extracts_expected_ckan_entries(monkeypatch):
    payload = {
        "success": True,
        "result": {
            "resources": [
                {"name": "Stations", "format": "CSV", "url": "https://example.test/stations.csv"},
                {"name": "Measurements", "format": "CSV", "url": "https://example.test/measurements.csv"},
                {"name": "Bulk Data Download", "format": "ZIP", "url": "https://example.test/bulk.zip"},
                {"name": "Change Log", "format": "TXT", "url": "https://example.test/changelog.txt"},
            ]
        },
    }

    monkeypatch.setattr(dwr_prep, "fetch_json", lambda _url: payload)
    resources = dwr_prep.discover_dwr_resources()

    assert set(resources) == {"stations", "measurements", "bulk_zip"}
    assert resources["bulk_zip"]["filename"] == "bulk_data_download.zip"
