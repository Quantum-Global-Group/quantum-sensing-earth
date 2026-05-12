from pathlib import Path

import pandas as pd

from src.data.groundwater import (
    aggregate_groundwater_monthly,
    assign_observations_to_basins,
    geometry_contains_point,
    groundwater_validation_metrics,
    normalize_groundwater_observations,
    validate_groundwater_observations,
    write_groundwater_track,
)
from src.data.groundwater import normalize_groundwater_dataframe


FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "central_valley"


def test_point_in_polygon_assigns_tiny_basin():
    geometry = {
        "type": "Polygon",
        "coordinates": [[[-122.5, 38.0], [-121.0, 38.0], [-121.0, 40.0], [-122.5, 40.0], [-122.5, 38.0]]],
    }

    assert geometry_contains_point(geometry, -121.8, 39.1)
    assert not geometry_contains_point(geometry, -120.0, 36.0)


def test_assign_observations_restricts_existing_codes_to_supplied_basins():
    observations = pd.DataFrame(
        [
            {
                "site_id": "outside",
                "latitude": 34.0,
                "longitude": -118.0,
                "basin_id": "9-999",
                "basin_name": "Not In Fixture",
            },
            {
                "site_id": "inside",
                "latitude": 39.1,
                "longitude": -121.8,
                "basin_id": "",
                "basin_name": "",
            },
        ]
    )

    assigned = assign_observations_to_basins(observations, FIXTURES / "tiny_b118_basins.geojson")

    outside = assigned[assigned["site_id"].eq("outside")].iloc[0]
    inside = assigned[assigned["site_id"].eq("inside")].iloc[0]
    assert pd.isna(outside["basin_id"])
    assert inside["basin_id"] == "5-022.01"


def test_groundwater_observations_normalize_and_assign_to_basins():
    observations = normalize_groundwater_observations(FIXTURES / "tiny_groundwater_observations.csv", source="fixture")
    assigned = assign_observations_to_basins(observations, FIXTURES / "tiny_b118_basins.geojson")
    validation = validate_groundwater_observations(assigned)

    assert validation["errors"] == []
    assert set(assigned["basin_id"].dropna()) == {"5-022.01", "5-022.15"}
    assert set(assigned["month"].dropna()) == {"2025-01", "2025-02", "2025-03"}


def test_dwr_gwe_normalizes_as_groundwater_elevation_feet():
    frame = pd.DataFrame(
        [
            {
                "site_code": "DWR-1",
                "msmt_date": "2026-03-19 00:00:00",
                "gwe": 536.68,
                "latitude": 36.5,
                "longitude": -121.7,
                "basin_code": "5-022.01",
                "basin_name": "Example Basin",
            },
            {
                "site_code": "DWR-2",
                "msmt_date": "2026-03-20",
                "gwe": 535.10,
                "latitude": 36.6,
                "longitude": -121.8,
                "basin_code": "5-022.01",
                "basin_name": "Example Basin",
            },
        ]
    )

    normalized = normalize_groundwater_dataframe(frame, source="dwr-periodic")

    assert normalized["value"].iloc[0] == 536.68
    assert normalized["value_units"].iloc[0] == "feet"
    assert normalized["measurement_type"].iloc[0] == "groundwater_elevation"
    assert normalized["basin_id"].iloc[0] == "5-022.01"
    assert set(normalized["month"]) == {"2026-03"}


def test_groundwater_monthly_anomaly_flips_depth_to_water_sign():
    observations = normalize_groundwater_observations(FIXTURES / "tiny_groundwater_observations.csv", source="fixture")
    assigned = assign_observations_to_basins(observations, FIXTURES / "tiny_b118_basins.geojson")
    monthly = aggregate_groundwater_monthly(assigned)
    san_joaquin = monthly[monthly["basin_id"].eq("5-022.15")].sort_values("month")

    assert len(monthly) == 6
    assert san_joaquin["measurement_type"].iloc[0] == "depth_to_water"
    assert san_joaquin["groundwater_level_anomaly"].iloc[0] > san_joaquin["groundwater_level_anomaly"].iloc[-1]


def test_groundwater_metrics_mark_insufficient_months():
    basin_metrics = pd.DataFrame(
        [
            {"month": "2025-01", "threshold": 1, "basin_id": "5-022.01", "basin_name": "Sacramento", "grace_mean_cm": 1.0, "gldas_mean_cm": 0.9, "usdm_drought_coverage_pct": 10.0},
            {"month": "2025-02", "threshold": 1, "basin_id": "5-022.01", "basin_name": "Sacramento", "grace_mean_cm": 2.0, "gldas_mean_cm": 1.8, "usdm_drought_coverage_pct": 20.0},
        ]
    )
    groundwater = pd.DataFrame(
        [
            {"month": "2025-01", "basin_id": "5-022.01", "basin_name": "Sacramento", "groundwater_monthly_mean": 41.0, "groundwater_level_anomaly": -0.5, "observation_count": 1, "site_count": 1, "value_units": "ft", "measurement_type": "groundwater_elevation"},
            {"month": "2025-02", "basin_id": "5-022.01", "basin_name": "Sacramento", "groundwater_monthly_mean": 42.0, "groundwater_level_anomaly": 0.5, "observation_count": 1, "site_count": 1, "value_units": "ft", "measurement_type": "groundwater_elevation"},
        ]
    )

    metrics = groundwater_validation_metrics(basin_metrics, groundwater)

    assert metrics.iloc[0]["status"] == "insufficient_months"
    assert pd.isna(metrics.iloc[0]["grace_groundwater_correlation"])


def test_write_groundwater_track_exports_contract_files(tmp_path):
    basin_metrics = pd.DataFrame(
        [
            {"month": "2025-01", "threshold": 1, "basin_id": "5-022.01", "basin_name": "Sacramento Valley - Tiny Test", "grace_mean_cm": 1.0, "gldas_mean_cm": 0.8, "usdm_drought_coverage_pct": 10.0},
            {"month": "2025-02", "threshold": 1, "basin_id": "5-022.01", "basin_name": "Sacramento Valley - Tiny Test", "grace_mean_cm": 0.2, "gldas_mean_cm": 0.1, "usdm_drought_coverage_pct": 20.0},
            {"month": "2025-03", "threshold": 1, "basin_id": "5-022.01", "basin_name": "Sacramento Valley - Tiny Test", "grace_mean_cm": -0.5, "gldas_mean_cm": -0.4, "usdm_drought_coverage_pct": 30.0},
        ]
    )
    basin_metrics_path = tmp_path / "basin_metrics.csv"
    basin_metrics.to_csv(basin_metrics_path, index=False)

    result = write_groundwater_track(
        tmp_path,
        FIXTURES / "tiny_groundwater_observations.csv",
        FIXTURES / "tiny_b118_basins.geojson",
        basin_metrics_path,
        source="fixture",
    )

    assert result.summary["status"] == "ok"
    assert (tmp_path / "groundwater_observations.csv").exists()
    assert (tmp_path / "groundwater_basin_monthly.csv").exists()
    assert (tmp_path / "groundwater_validation_metrics.csv").exists()
    assert (tmp_path / "groundwater_validation_summary.json").exists()
    assert (tmp_path / "groundwater_summary.json").exists()
