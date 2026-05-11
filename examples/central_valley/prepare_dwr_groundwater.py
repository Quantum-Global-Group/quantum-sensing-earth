"""Prepare California DWR groundwater well observations for basin validation."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from src.data.groundwater import (
    assign_observations_to_basins,
    column_lookup,
    normalize_groundwater_dataframe,
    validate_groundwater_observations,
)


DWR_PERIODIC_SOURCE = "https://lab.data.ca.gov/dataset/periodic-groundwater-level-measurements"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize DWR Periodic Groundwater Level Measurements for QSE.")
    parser.add_argument("--input", help="DWR bulk ZIP export or a single canonical/combined CSV.")
    parser.add_argument("--stations", help="DWR stations/wells CSV when measurements are supplied separately.")
    parser.add_argument("--measurements", help="DWR groundwater measurements CSV when stations are supplied separately.")
    parser.add_argument("--basins", required=True, help="DWR B118 basin GeoJSON used for point-in-polygon assignment.")
    parser.add_argument("--output", default="data/central_valley/groundwater/dwr_groundwater_clean.csv")
    parser.add_argument("--manifest", help="Output provenance manifest. Defaults to <output stem>_manifest.yaml.")
    parser.add_argument("--drop-unassigned", action="store_true", help="Drop observations outside the supplied basin polygons.")
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def zip_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return [name for name in archive.namelist() if name.lower().endswith(".csv")]


def pick_member(members: list[str], role: str) -> str | None:
    role_tokens = {
        "stations": ("station", "site", "well"),
        "measurements": ("measurement", "periodic", "level", "water"),
    }[role]
    ranked = [name for name in members if any(token in Path(name).name.lower() for token in role_tokens)]
    if ranked:
        return sorted(ranked, key=lambda item: (len(Path(item).name), Path(item).name))[0]
    return None


def read_zip_csv(path: Path, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as fh:
            return pd.read_csv(fh)


def merge_station_measurements(stations: pd.DataFrame, measurements: pd.DataFrame) -> pd.DataFrame:
    station_lookup = column_lookup(list(stations.columns))
    measurement_lookup = column_lookup(list(measurements.columns))
    station_key = station_lookup.get("site_id")
    measurement_key = measurement_lookup.get("site_id")
    if not station_key or not measurement_key:
        raise ValueError("Could not identify a site_id column in both stations and measurements CSVs.")
    merged = measurements.merge(
        stations,
        left_on=measurement_key,
        right_on=station_key,
        how="left",
        suffixes=("", "_station"),
    )
    return merged


def load_input(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    metadata: dict = {"source_mode": None, "source_files": []}
    if args.stations and args.measurements:
        stations_path = Path(args.stations)
        measurements_path = Path(args.measurements)
        metadata.update({"source_mode": "stations_measurements_csv", "source_files": [str(stations_path), str(measurements_path)]})
        return merge_station_measurements(read_csv(stations_path), read_csv(measurements_path)), metadata

    if not args.input:
        raise SystemExit("Pass --input, or pass both --stations and --measurements.")

    input_path = Path(args.input)
    if input_path.suffix.lower() == ".zip":
        members = zip_members(input_path)
        station_member = pick_member(members, "stations")
        measurement_member = pick_member(members, "measurements")
        metadata.update({"source_mode": "zip", "source_files": [str(input_path)], "zip_members": members})
        if station_member and measurement_member and station_member != measurement_member:
            metadata["station_member"] = station_member
            metadata["measurement_member"] = measurement_member
            return merge_station_measurements(read_zip_csv(input_path, station_member), read_zip_csv(input_path, measurement_member)), metadata
        if len(members) == 1:
            metadata["combined_member"] = members[0]
            return read_zip_csv(input_path, members[0]), metadata
        raise SystemExit("ZIP input must contain either one combined CSV or identifiable station and measurement CSVs.")

    metadata.update({"source_mode": "combined_csv", "source_files": [str(input_path)]})
    return read_csv(input_path), metadata


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict:
    args = parse_args() if argv is None else build_parser().parse_args(argv)
    raw, metadata = load_input(args)
    normalized = normalize_groundwater_dataframe(
        raw,
        source="dwr-periodic",
        source_url=DWR_PERIODIC_SOURCE,
        source_file=", ".join(metadata.get("source_files", [])),
    )
    assigned = assign_observations_to_basins(normalized, Path(args.basins))
    if args.drop_unassigned:
        assigned = assigned[assigned["basin_id"].notna() & assigned["basin_id"].astype(str).str.strip().ne("")]

    validation = validate_groundwater_observations(assigned)
    if validation["errors"]:
        raise SystemExit("DWR groundwater preparation failed: " + "; ".join(validation["errors"]))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    assigned.to_csv(output, index=False)
    manifest_path = Path(args.manifest) if args.manifest else output.with_name(f"{output.stem}_manifest.yaml")
    manifest = {
        "schema_version": "dwr-groundwater-prep-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "California DWR Periodic Groundwater Level Measurements",
            "url": DWR_PERIODIC_SOURCE,
            "mode": metadata.get("source_mode"),
            "files": metadata.get("source_files", []),
            "zip_members": metadata.get("zip_members", []),
        },
        "basins": str(args.basins),
        "output": str(output),
        "rows": int(len(assigned)),
        "basin_assigned_rows": int(assigned["basin_id"].notna().sum()),
        "months": sorted(assigned["month"].dropna().astype(str).unique().tolist()),
        "validation": validation,
        "value_handling": "Canonical value is numeric. Raw value/date/units/type/source columns are preserved for audit.",
        "claim_note": "Prepared well observations support basin-scale groundwater validation, not groundwater discovery or quantum advantage.",
    }
    write_manifest(manifest_path, manifest)
    result = {"output": str(output), "manifest": str(manifest_path), "rows": int(len(assigned)), "basin_assigned_rows": int(assigned["basin_id"].notna().sum())}
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()
