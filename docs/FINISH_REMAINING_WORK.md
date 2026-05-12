# Finish Remaining Work

## Purpose

This is the comprehensive finish inventory for Quantum Sensing Earth. It lists what must still be completed before the project can be called a credible first release, what is already done, what is blocked on real data, and what should remain explicitly out of scope.

The target release is not a generic anomaly-detection demo. The target release is a reproducible GRACE/GRACE-FO Central Valley basin-scale hydrology and groundwater-validation workflow with transparent detector comparison.

## Final Supported Claim

The finished project may say:

> This project validates a reproducible basin-scale hydrology and groundwater workflow using GRACE/GRACE-FO, DWR basin boundaries, DWR/USGS well data, GLDAS/TWS, and detector comparison.

The finished project may not say:

> This proves a field-ready quantum groundwater detector or quantum advantage.

## Current Release Position

| Area | Current Status | Finish Meaning |
| --- | --- | --- |
| Package, CLI, demo, CI | Mostly done | Repo is reviewable and CI is passing. |
| GRACE/GRACE-FO + USDM workflow | Mostly done | Multimonth drought-proxy workflow works and is dashboard-ready. |
| GLDAS/TWS hydrology track | Partial | Metrics exist; doctor/download hardening and metadata checks still need work. |
| Central Valley basin workflow | Scaffold done | B118 prep exists; final release must use live authoritative basin output locally. |
| DWR groundwater workflow | Scaffold done | Downloader/prep exists; final release needs real normalized DWR observations and basin coverage. |
| Basin/groundwater metrics | Scaffold done | Metrics exist; final release needs valid real basin/month coverage. |
| Streamlit dashboard | Review design mostly done | Hierarchy, claim boundary, coverage, map, hydrology, basin, and groundwater sections exist. |
| Final evidence bundle | Not done | Needs a real 6-12 month Central Valley run and release artifact review. |
| Quantum advantage evidence | Not started | Keep out of v1 claim unless sensitivity analysis supports it later. |

## P0 Finish Tasks

These are required before tagging the first credible Central Valley validation release.

### 1. Real DWR Basin And Groundwater Data

- [ ] Run live DWR Bulletin 118 basin prep.
- [ ] Confirm `data/central_valley/basins/central_valley_b118_basins.geojson` exists locally.
- [ ] Confirm `data/central_valley/basins/central_valley_basin_manifest.yaml` records source URL, download date, CRS, citation, filter method, and limitations.
- [ ] Download official DWR Periodic Groundwater Level Measurements using the prep command or manually supplied files.
- [ ] Normalize DWR observations into `data/central_valley/groundwater/dwr_groundwater_clean.csv`.
- [ ] Verify site coordinates, dates, units, measurement type, raw values, and source URL are preserved.
- [ ] Verify wells join to DWR B118 basins by point-in-polygon when basin fields are missing.
- [ ] Confirm at least one Central Valley basin has three or more valid groundwater months.
- [ ] Document if groundwater values are depth-to-water, groundwater elevation, or mixed.

### 2. Final 6-12 Month Central Valley Run

- [ ] Run a minimum six-month GRACE-FO Central Valley validation.
- [ ] Prefer twelve recent GRACE-FO months if data coverage allows.
- [ ] Include USDM thresholds D1+, D2+, and D3+.
- [ ] Include z-score, DBSCAN, and isolation forest.
- [ ] Include four spatial folds.
- [ ] Include DWR B118 basins.
- [ ] Include DWR groundwater observations.
- [ ] Include GLDAS/TWS where available.
- [ ] Export `timeline_metrics.csv`.
- [ ] Export `coverage_summary.json`.
- [ ] Export `month_alignment.csv`.
- [ ] Export `artifact_manifest.json`.
- [ ] Export `basin_metrics.csv`.
- [ ] Export `basin_summary.csv` and `basin_summary.json`.
- [ ] Export `groundwater_observations.csv`.
- [ ] Export `groundwater_basin_monthly.csv`.
- [ ] Export `groundwater_validation_metrics.csv`.
- [ ] Export `groundwater_validation_summary.csv` and `.json`.
- [ ] Export `executive_summary.md`.

### 3. Coverage And Claim Integrity

- [ ] Show month coverage for GRACE, USDM, GLDAS, TWS, basin, and groundwater.
- [ ] Make missing hydrology or groundwater months visible in `month_alignment.csv`.
- [ ] Make missing months visible in the dashboard top screen.
- [ ] Ensure partial hydrology coverage cannot be summarized as complete evidence.
- [ ] Ensure groundwater rows with fewer than three valid months are marked `insufficient_months`.
- [ ] Ensure `insufficient_months` rows are not ranked as strongest evidence.
- [ ] Confirm README, dashboard, docs, and executive summary all use the same claim level.

### 4. Dashboard Final Review

- [ ] Open Streamlit on the final Central Valley output.
- [ ] Confirm first screen states the current defensible claim.
- [ ] Confirm claim boundary says groundwater discovery is not proven.
- [ ] Confirm quantum advantage is not claimed.
- [ ] Confirm coverage timeline appears before performance interpretation.
- [ ] Confirm basin map uses Central Valley/DWR basin geography.
- [ ] Confirm basin selector works when groundwater artifacts exist.
- [ ] Confirm GRACE-vs-groundwater time series renders.
- [ ] Confirm lagged correlation chart renders.
- [ ] Confirm observation coverage warnings render.
- [ ] Confirm detector charts remain secondary to basin/hydrology validation.
- [ ] Confirm no chart mixes incompatible units on one axis without faceting.
- [ ] Confirm no missing-image dead ends appear in the main review path.

### 5. Release Verification

- [ ] `python -m pytest -q` passes.
- [ ] `python -m quantum_sensing_earth.demo --output outputs/demo` passes.
- [ ] GitHub Actions passes on `main`.
- [ ] Final Central Valley dashboard opens locally.
- [ ] `data/` and `outputs/` remain untracked.
- [ ] No Earthdata tokens, DWR downloads, `.netrc`, API keys, or local credentials are committed.
- [ ] Release notes summarize what is validated and what is not validated.
- [ ] Release checklist is completed.
- [ ] First release tag is created only after the final evidence bundle is reviewed.

## P1 Strong-Release Tasks

These are not strictly required for a first credible release, but they materially improve scientific trust.

### GLDAS/TWS Hardening

- [ ] Add GLDAS/TWS doctor command.
- [ ] Validate expected NetCDF variables.
- [ ] Validate units and month metadata.
- [ ] Validate file readability.
- [ ] Validate CRS/grid shape where available.
- [ ] Record resampling method in metadata and dashboard.
- [ ] Add generated NetCDF fixture tests.
- [ ] Add bad-variable-name tests.
- [ ] Add missing-units warnings.
- [ ] Update GRACE Tellus docs with exact GLDAS/TWS manual and authenticated download steps.

### Artifact Contract

- [ ] Add checksums for important input artifacts.
- [ ] Add command replay metadata for final output folders.
- [ ] Add report/dashboard schema version fields.
- [ ] Add machine-readable validation-status summary.
- [ ] Add optional compressed review bundle generation.
- [ ] Add a run-folder doctor command that checks expected artifacts.

### Basin/Groundwater Science

- [ ] Add basin rasterization tests against a generated polygon fixture.
- [ ] Add observation-count and site-count warnings to dashboard callouts.
- [ ] Add confidence notes for small sample sizes.
- [ ] Add basin ranking by valid groundwater correlation only.
- [ ] Add lagged correlation interpretation text.
- [ ] Add a clearer measurement-type sign convention panel for depth-to-water versus groundwater elevation.
- [ ] Add USGS groundwater API fallback using the same canonical schema.

### Dashboard Polish

- [ ] Add a Central Valley-specific map treatment when B118 artifacts are present.
- [ ] Add small multiples for basin groundwater evidence.
- [ ] Add compact “why this matters” annotations beside each major chart.
- [ ] Add table row links to source artifacts where possible.
- [ ] Add exportable dashboard snapshot or summary card image.
- [ ] Add Streamlit AppTest smoke if practical.

## P2 After-Release Enhancements

These can wait until after the first release.

- [ ] Hosted public dashboard deployment.
- [ ] Public sample output bundle with redacted/small artifacts.
- [ ] More study regions such as High Plains Aquifer, Amazon basin, Greenland, or Colorado River Basin.
- [ ] More hydrology targets beyond GLDAS/TWS.
- [ ] Groundwater depletion study ingestion workflow.
- [ ] Basin storage product ingestion workflow.
- [ ] Better uncertainty propagation from sensor simulation to detector metrics.
- [ ] Statistical significance tests for sensor-profile comparison.
- [ ] Bootstrap confidence intervals for basin correlations.
- [ ] Multi-year seasonal analysis.
- [ ] Automated latest-month discovery and scheduled data-refresh workflow.

## Quantum/Detector Finish Criteria

The detector layer is useful, but it should not lead the scientific claim.

To finish the detector comparison for v1:

- [ ] Keep z-score, DBSCAN, and isolation forest in all release runs.
- [ ] Report winner, failure mode, and why.
- [ ] Show F1, IoU, FPR, FNR, RMSE, and SNR.
- [ ] Keep detector metrics separate from hydrology and groundwater metrics.
- [ ] Explain that USDM mask overlap is proxy validation, not groundwater truth.

To claim quantum-inspired advantage later:

- [ ] Add sensor-noise sensitivity analysis.
- [ ] Add matched classical versus quantum-inspired baselines.
- [ ] Add repeated basin/month evaluation.
- [ ] Add uncertainty intervals.
- [ ] Show consistent benefit across multiple basins and months.
- [ ] Document physical assumptions clearly.

Until then, the allowed language is:

> The project includes quantum-sensing-inspired simulation as one comparison layer.

The disallowed language is:

> The project proves quantum advantage or a deployable quantum groundwater detector.

## Documentation To Finish

- [ ] Update README with final Central Valley release command after the real run works.
- [ ] Update `docs/DATA_SOURCES.md` with actual DWR file/resource names used in the release.
- [ ] Update `docs/SCIENTIFIC_CLAIMS.md` with final claim level.
- [ ] Update `docs/DASHBOARD_GUIDE.md` with final dashboard screenshots and reviewer path.
- [ ] Update `docs/RELEASE_CHECKLIST.md` with final checked items.
- [ ] Add final release notes to `CHANGELOG.md`.
- [ ] Add citation guidance for DWR B118, DWR groundwater measurements, GRACE/GRACE-FO, USDM, and GLDAS/TWS.

## Final Release Commands

Expected local release path:

```bash
python examples/central_valley/prepare_central_valley_basins.py
python examples/central_valley/prepare_dwr_groundwater.py --download-dwr-periodic --download-resource stations-measurements --basins data/central_valley/basins/central_valley_b118_basins.geojson --output data/central_valley/groundwater/dwr_groundwater_clean.csv --drop-unassigned
python examples/grace_tellus/run_multimonth_usdm.py --mission grace-fo --study-region central-valley --months 12 --thresholds 1 2 3 --spatial-folds 4 --groundwater-observations data/central_valley/groundwater/dwr_groundwater_clean.csv --groundwater-source dwr-periodic --output outputs/central_valley_groundwater_release
python -m streamlit run src/dashboard/app.py -- --output outputs/central_valley_groundwater_release
```

Minimum verification:

```bash
python -m pytest -q
python -m quantum_sensing_earth.demo --output outputs/demo
```

## Release Decision

The project is finished for v1 when all P0 tasks are complete and the final output supports the allowed release claim.

If real DWR groundwater coverage is insufficient, the project can still ship as:

> A reproducible Central Valley GRACE/GRACE-FO hydrology-validation workflow with groundwater-ingestion support, but without a completed groundwater-validation result.

If real DWR groundwater coverage is sufficient, the project can ship as:

> A reproducible Central Valley GRACE/GRACE-FO basin-scale hydrology and groundwater-validation workflow with transparent detector comparison.

In both cases, the project must still say:

> Groundwater discovery is not proven, and quantum advantage is not claimed.
