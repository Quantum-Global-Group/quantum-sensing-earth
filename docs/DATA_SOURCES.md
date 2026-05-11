# Data Sources

This project separates data-source credibility from detector performance. Every real-data run should record source, units, CRS, resolution, preprocessing, mask provenance, citation, and limitations in manifests and output metadata.

## Primary Gravity Signal

**GRACE / GRACE-FO Tellus land water-equivalent-thickness grids**

- Role: primary water-mass anomaly raster.
- Typical units: centimeters equivalent water thickness.
- Typical cadence: monthly.
- Validation use: input signal for detector and basin aggregation workflows.
- Current claim level: real satellite-derived hydrology signal, not local groundwater truth.

## Drought Proxy Target

**U.S. Drought Monitor weekly shapefiles**

- Role: independent drought proxy mask.
- Typical units: categorical D0-D4 drought severity.
- Validation use: rasterized D1+, D2+, and D3+ masks on the GRACE grid.
- Scientific caveat: USDM is independent of the GRACE raster but is not a direct measurement of terrestrial water storage or groundwater.

## External Hydrology Target

**GLDAS-NOAH 3.3 TWS anomaly monthly**

- Role: external hydrology comparison target closer to water storage than drought severity.
- Typical units: centimeters equivalent water thickness anomaly.
- Validation use: month-aligned GRACE-vs-GLDAS correlation, RMSE, bias, trend agreement, and anomaly sign agreement.
- Scientific caveat: GLDAS is model-assimilated hydrology, not groundwater truth.

## Groundwater Basin Geometry

**California DWR Bulletin 118 groundwater basins/subbasins**

- Role: authoritative Central Valley groundwater basin/subbasin boundaries.
- Preparation command: `python examples/central_valley/prepare_central_valley_basins.py`
- Output: `data/central_valley/basins/central_valley_b118_basins.geojson`
- Manifest: `data/central_valley/basins/central_valley_basin_manifest.yaml`
- Access path: CA Open Data GeoJSON download, with the DWR ArcGIS FeatureServer recorded in the manifest.
- Scientific caveat: basin boundaries define geography; they do not provide observations by themselves.

## Groundwater Observation Target

**California DWR Periodic Groundwater Level Measurements**

- Role: primary v1 groundwater validation target.
- Typical contents: well locations, measurement dates, groundwater depth/elevation values, quality information.
- Validation use: wells are joined to DWR B118 basins, aggregated to monthly basin values, converted into basin groundwater-level anomalies, then compared against GRACE basin means.
- Preparation command: `python examples/central_valley/prepare_dwr_groundwater.py --input path/to/dwr_bulk.zip --basins data/central_valley/basins/central_valley_b118_basins.geojson --output data/central_valley/groundwater/dwr_groundwater_clean.csv --drop-unassigned`
- Minimum evidence rule: metrics with fewer than three valid basin/month pairs are marked `insufficient_months`.

## Supplemental Groundwater Target

**USGS groundwater levels service**

- Role: fallback or supplemental well observations.
- Validation use: should be converted into the same groundwater observation schema as DWR data.
- Scientific caveat: site selection, measurement cadence, and screened interval differences must be documented before interpretation.
