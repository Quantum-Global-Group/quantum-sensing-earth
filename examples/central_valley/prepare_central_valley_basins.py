"""Prepare DWR Bulletin 118 Central Valley groundwater basin boundaries.

The script downloads GeoJSON from the official DWR ArcGIS Bulletin 118 service,
filters to Central Valley-relevant basins/subbasins, normalizes feature
properties for the validation runner, and writes a provenance manifest.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


B118_QUERY_URL = "https://gis.data.cnra.ca.gov/api/download/v1/items/49807a1fbc584631bdf88d9ca71dd083/geojson?layers=0"
B118_ARCGIS_SERVICE = (
    "https://gis.water.ca.gov/arcgis/rest/services/Geoscientific/"
    "i08_B118_CA_GroundwaterBasins/FeatureServer/0"
)

CENTRAL_VALLEY_NAMES = (
    "sacramento valley",
    "san joaquin valley",
    "tulare lake",
    "central valley",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare DWR B118 Central Valley basin GeoJSON.")
    parser.add_argument("--source", default=B118_QUERY_URL, help="DWR B118 GeoJSON URL or local GeoJSON path.")
    parser.add_argument(
        "--output",
        default="data/central_valley/basins/central_valley_b118_basins.geojson",
        help="Normalized Central Valley basin GeoJSON.",
    )
    parser.add_argument(
        "--manifest",
        default="data/central_valley/basins/central_valley_basin_manifest.yaml",
        help="Basin provenance manifest.",
    )
    return parser.parse_args()


def load_geojson(source: str) -> dict:
    path = Path(source)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    request = urllib.request.Request(source, headers={"User-Agent": "quantum-sensing-earth/0.1"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not read DWR B118 GeoJSON from {source}: {last_error}") from last_error


def feature_text(feature: dict) -> str:
    props = feature.get("properties") or {}
    return " ".join(str(value).lower() for value in props.values() if value is not None)


def is_central_valley(feature: dict) -> bool:
    text = feature_text(feature)
    return any(name in text for name in CENTRAL_VALLEY_NAMES)


def normalize_feature(feature: dict, index: int) -> dict:
    props = feature.get("properties") or {}
    basin_number = props.get("Basin_Subbasin_Number") or props.get("Basin_Number") or f"b118_{index}"
    basin_name = props.get("Basin_Subbasin_Name") or props.get("Basin_Name") or f"B118 Basin {index}"
    normalized_props = {
        "basin_id": str(basin_number),
        "name": str(basin_name),
        "basin_name": str(basin_name),
        "source_basin_number": props.get("Basin_Number"),
        "source_basin_subbasin_number": props.get("Basin_Subbasin_Number"),
        "source_basin_name": props.get("Basin_Name"),
        "source_basin_subbasin_name": props.get("Basin_Subbasin_Name"),
        "target_relevance": "groundwater_observation",
        "notes": "California DWR Bulletin 118 groundwater basin/subbasin boundary.",
    }
    return {"type": "Feature", "properties": normalized_props, "geometry": feature.get("geometry")}


def main() -> dict:
    args = parse_args()
    payload = load_geojson(args.source)
    features = [normalize_feature(feature, index) for index, feature in enumerate(payload.get("features", []), start=1) if is_central_valley(feature)]
    if not features:
        raise SystemExit("No Central Valley basin features matched. Inspect source fields or pass a prefiltered GeoJSON.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = {"type": "FeatureCollection", "name": "central_valley_b118_basins", "features": features}
    output.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

    manifest = {
        "source": {
            "name": "California DWR Bulletin 118 Groundwater Basins",
            "url": args.source,
            "arcgis_service": B118_ARCGIS_SERVICE,
            "download_date_utc": datetime.now(timezone.utc).isoformat(),
            "crs": "EPSG:4326",
            "license_or_terms_note": (
                "California DWR enterprise GIS data. DWR makes no warranties or guarantees as to completeness, "
                "accuracy, or correctness; cite DWR and review official terms before publication."
            ),
            "citation": "California Department of Water Resources, Bulletin 118 Groundwater Basin Boundaries.",
        },
        "filter": {
            "method": "Feature properties containing Central Valley, Sacramento Valley, San Joaquin Valley, or Tulare Lake.",
            "matched_features": len(features),
        },
        "outputs": {"geojson": str(output)},
        "limitations": [
            "Boundaries define groundwater basin/subbasin geography, not groundwater level observations.",
            "GRACE/GRACE-FO cells are coarse relative to many subbasins; aggregate metrics must report coverage.",
        ],
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(json.dumps({"features": len(features), "geojson": str(output), "manifest": str(manifest_path)}, indent=2))
    return manifest


if __name__ == "__main__":
    main()
