# Central Valley Groundwater Validation

This folder contains download-free fixtures and a preparation script for the first release target: California Central Valley basin-scale groundwater validation.

## Prepare DWR Bulletin 118 Basins

```bash
python examples/central_valley/prepare_central_valley_basins.py
```

The script reads the official California DWR Bulletin 118 ArcGIS GeoJSON service, filters Central Valley-relevant groundwater basins/subbasins, writes:

- `data/central_valley/basins/central_valley_b118_basins.geojson`
- `data/central_valley/basins/central_valley_basin_manifest.yaml`

The manifest records source URL, download date, CRS, terms note, citation, filter method, and limitations.

## Prepare DWR Groundwater Observations

The primary v1 target is California DWR Periodic Groundwater Level Measurements. Normalize a DWR bulk ZIP, separate stations/measurements CSVs, or a combined canonical CSV:

```bash
python examples/central_valley/prepare_dwr_groundwater.py ^
  --input path\to\dwr_bulk.zip ^
  --basins data\central_valley\basins\central_valley_b118_basins.geojson ^
  --output data\central_valley\groundwater\dwr_groundwater_clean.csv ^
  --drop-unassigned
```

For separate station and measurement exports:

```bash
python examples/central_valley/prepare_dwr_groundwater.py ^
  --stations path\to\stations.csv ^
  --measurements path\to\measurements.csv ^
  --basins data\central_valley\basins\central_valley_b118_basins.geojson ^
  --output data\central_valley\groundwater\dwr_groundwater_clean.csv ^
  --drop-unassigned
```

The output uses the canonical schema below and also preserves raw audit fields such as `raw_value`, `raw_value_column`, `raw_date`, `raw_measurement_type`, `raw_units`, and `raw_source_file`:

- `site_id`
- `site_name`
- `source`
- `latitude`
- `longitude`
- `basin_id`
- `basin_name`
- `date`
- `month`
- `value`
- `value_units`
- `measurement_type`
- `quality_flag`
- `source_url`

If `basin_id` is missing, the runner assigns wells to B118 basins by point-in-polygon using latitude/longitude.

## Central Valley Runner Example

```bash
python examples/grace_tellus/run_multimonth_usdm.py ^
  --mission grace-fo ^
  --study-region central-valley ^
  --start 2025-01-01 ^
  --months 6 ^
  --thresholds 1 2 3 ^
  --spatial-folds 4 ^
  --groundwater-observations path\to\dwr_periodic_groundwater_levels.csv ^
  --groundwater-source dwr-periodic ^
  --output outputs\central_valley_groundwater_001
```

This begins groundwater validation. It does not prove groundwater discovery or quantum advantage.
