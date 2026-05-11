import zipfile
from pathlib import Path

import pandas as pd

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
