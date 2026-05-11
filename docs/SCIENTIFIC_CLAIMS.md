# Scientific Claims

## Current Honest Claim

Quantum Sensing Earth is a reproducible GRACE/GRACE-FO hydrology validation workflow with detector comparison and quantum-sensing-inspired sensor simulation.

It can compare real satellite-derived water-mass rasters against independent drought proxies, external hydrology targets, named basins, and, when provided, groundwater well observations.

## Claims Supported Now

- The software can run repeatable detector experiments over synthetic, pseudo-real, and real geospatial inputs.
- Real-data artifacts can preserve provenance, CRS, resolution, nodata, units, masks, and citations.
- Detector quality can be compared side by side using F1, IoU, false-positive rate, false-negative rate, localization, and summary statistics.
- Multimonth GRACE/GRACE-FO runs can expose partial coverage instead of hiding missing hydrology or groundwater months.
- Basin-scale validation can begin when DWR B118 boundaries and DWR/USGS groundwater observations are provided.

## Claims Not Supported Yet

- A proven groundwater discovery system.
- A proven quantum hardware advantage.
- Site-level anomaly confirmation.
- Causal linkage between detector masks and aquifer changes.
- Scientific interpretation from runs with weak labels, toy fixtures, stale dates, or insufficient groundwater months.

## Groundwater Claim Gate

The project may say “groundwater validation has begun” when:

- DWR or USGS well observations are present.
- Wells are assigned to named basins.
- Monthly basin groundwater anomalies are exported.
- `groundwater_validation_summary.json` exists.
- At least one basin/threshold has three or more valid months.

The project may not say “groundwater discovery is proven” until independent basin/well evidence is long enough, geographically meaningful, scientifically interpreted, and sensor-sensitivity claims are validated separately.

## Release Claim Target

The first finished release should claim:

> A reproducible Central Valley GRACE/GRACE-FO basin-scale hydrology and groundwater-validation dashboard with transparent detector comparison.

It should explicitly avoid claiming:

> A field-ready quantum groundwater detector.
