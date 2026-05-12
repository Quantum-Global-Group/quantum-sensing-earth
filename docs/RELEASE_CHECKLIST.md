# Release Checklist

Use this checklist before tagging the first Central Valley groundwater-validation release.

## Required Gates

- [x] `python -m pytest -q` passes.
- [x] `python -m quantum_sensing_earth.demo --output outputs/demo` passes.
- [ ] CI passes on GitHub.
- [ ] Current scaffold and release commits are pushed to `origin/main` and `quantum-global/main`.
- [x] Live DWR Bulletin 118 basin prep has produced local `data/central_valley/basins/central_valley_b118_basins.geojson`.
- [x] DWR groundwater observations have been normalized into local `data/central_valley/groundwater/dwr_groundwater_clean.csv`.
- [x] A 6-12 month GRACE-FO Central Valley run exists locally.
- [x] The final run exports `coverage_summary.json`, `month_alignment.csv`, `artifact_manifest.json`, and `executive_summary.md`.
- [x] The Streamlit dashboard opens on the final run output.
- [x] At least one basin has valid groundwater coverage, or the release explicitly says groundwater validation was not achieved.
- [ ] README, dashboard, `docs/SCIENTIFIC_CLAIMS.md`, and the final executive summary agree on claim level.
- [x] No credentials, Earthdata tokens, downloaded `data/`, or generated `outputs/` are committed.

## Claim Gate

Allowed release claim:

> A reproducible Central Valley GRACE/GRACE-FO basin-scale hydrology and groundwater-validation dashboard with transparent detector comparison.

Disallowed release claim:

> A field-ready quantum groundwater detector or proven quantum advantage.
