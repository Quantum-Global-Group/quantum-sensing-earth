# Finish Line Plan

## Purpose

This document defines the actions, tasks, and features required before Quantum Sensing Earth can be called "finished" in a responsible way.

The project should not be considered finished merely because it runs, has a dashboard, or produces metrics. It is finished when it can make a clear, evidence-backed claim about gravity-derived hydrology validation, preserve enough provenance for outside review, and avoid overstating the quantum or groundwater implications.

## Finished Project Statement

The target finished-state statement is:

> Quantum Sensing Earth is a reproducible GRACE/GRACE-FO hydrology validation platform that compares gravity-derived water-mass signals, classical and quantum-sensing-inspired measurement profiles, and multiple anomaly detectors against independent drought, hydrology, basin-storage, or groundwater-observation targets over multiple months and named basins.

The project may only claim "groundwater validation" when it includes an independent groundwater or basin-storage target.

The project may only claim "quantum advantage" when the comparison is supported by a clearly documented sensor model, matched baselines, uncertainty analysis, and repeated validation results that show a consistent benefit from the quantum-inspired profile.

## Definition of Done

The project is finished when all of these are true:

- A new user can install the package and run a download-free demo without credentials.
- A reviewer can run a real or documented public-data workflow with clear instructions.
- The dashboard explains the scientific story without requiring the reviewer to inspect raw files first.
- Every major output is traceable to CSV, JSON, raster, manifest, or metadata artifacts.
- Real-data provenance is explicit: source, date range, units, CRS, resolution, preprocessing, mask method, mask independence, and citation.
- Missing months, weak labels, stale data, and incomplete hydrology coverage are reported clearly.
- Detector metrics are separated from hydrology metrics and basin metrics.
- Tuning metrics are separated from held-out evaluation metrics.
- Basin-level validation exists with authoritative or clearly documented basin boundaries.
- At least one groundwater or basin-storage validation target exists, even if the first version is a documented manual workflow.
- CI verifies the CLI, demo, dashboard import, validation fixture generation, and core metrics.
- Documentation states what the project proves and does not prove.

## Current Status

| Area | Status | Meaning |
| --- | --- | --- |
| Synthetic benchmark pipeline | Done | The core experiment machinery works on generated anomaly fields. |
| CSV and pseudo-real validation fixtures | Done | The project can run without private downloads. |
| GeoTIFF/real-raster path | Mostly done | Import support exists; more edge-case tests are needed. |
| GRACE/GRACE-FO + USDM workflow | Mostly done | Real gravity-derived raster and drought-proxy comparison are in place. |
| GLDAS/TWS hydrology track | Partial | Metrics exist, but coverage alignment and automated download/readiness need hardening. |
| Basin aggregation | Partial | Fixture basin summaries exist; authoritative basin boundaries are needed. |
| Groundwater or basin-storage target | Not done | This is the biggest remaining scientific gap. |
| Dashboard story | Partial | Claim boundary exists; visual storytelling and reviewer UX need more polish. |
| CI and packaging | Mostly done | Current smoke tests pass; more data-ingestion tests are needed. |
| Public/reviewer docs | Partial | README and explainer exist; finish-line and real-data recipes need expansion. |

## Completion Epics

### Epic 1: Installation, Packaging, and Demo

Goal: a technical reviewer can clone the repo and run something meaningful in minutes.

Required features:

- Stable package import namespace.
- Installed CLI entrypoint.
- Download-free demo command.
- Streamlit dashboard launch path.
- Clear dependency extras for `dev`, `dashboard`, and `geo`.
- CI coverage for the install path.

Tasks:

- [x] Add `pyproject.toml`.
- [x] Add installed CLI entrypoint.
- [x] Fix installed CLI exit status.
- [x] Add `python -m quantum_sensing_earth.demo --output outputs/demo`.
- [x] Add CI smoke test for the demo.
- [x] Add CI smoke test for dashboard import.
- [ ] Add a release tag workflow.
- [ ] Add package metadata classifiers.
- [ ] Add a `CHANGELOG.md`.
- [ ] Add a minimal sample-output artifact manifest for reviewers.

Acceptance criteria:

- `python -m pip install -e .[dev,dashboard]` succeeds.
- `quantum-sensing-earth --seeds 1 --detectors z_score --output outputs/ci_smoke` exits with code 0.
- `python -m quantum_sensing_earth.demo --output outputs/demo` exits with code 0.
- CI passes on GitHub.

### Epic 2: Data Ingestion and Provenance

Goal: every real or pseudo-real run is scientifically inspectable.

Required features:

- CSV grid loader.
- NumPy array loader.
- GeoTIFF loader with CRS, transform, bounds, resolution, nodata.
- NetCDF/GRACE/GLDAS conversion workflow.
- Validation manifest schema.
- Manifest doctor command.
- Explicit weak-label and missing-provenance warnings.

Tasks:

- [x] Support CSV validation grids.
- [x] Support `.npy` validation grids.
- [x] Support optional GeoTIFF validation grids.
- [x] Preserve CRS, bounds, transform, resolution, and nodata metadata.
- [x] Add `doctor` command for manifest validation.
- [x] Add GRACE Tellus example folder and manifest template.
- [x] Add weak-label warning language.
- [ ] Define a formal manifest schema version.
- [ ] Validate manifests against required and recommended fields.
- [ ] Add stricter tests for nodata, malformed transforms, missing CRS, and mismatched masks.
- [ ] Add NetCDF variable discovery and error messages.
- [ ] Add importer documentation for GLDAS/TWS files.
- [ ] Add a real-data artifact index file for each run.

Acceptance criteria:

- Every real-data run writes `metadata.json` with CLI args, config snapshot, source metadata, preprocessing, and package versions.
- A missing citation, CRS, nodata, date range, or mask-provenance field produces an actionable warning.
- The report shows provenance warnings prominently.

### Epic 3: GRACE/GRACE-FO Workflow

Goal: run repeatable monthly validation against gravity-derived water-mass rasters.

Required features:

- GRACE/GRACE-FO mission selection.
- Month range selection.
- Public-data recipe.
- Regional crop.
- Matching USDM mask generation.
- Threshold variants for D1+, D2+, and D3+.
- Multimonth metrics.
- Timeline artifacts.

Tasks:

- [x] Add multimonth GRACE/USDM runner.
- [x] Add mission and start-month options.
- [x] Add USDM threshold support.
- [x] Add timeline metrics and report artifacts.
- [x] Add stale-data warning in dashboard.
- [ ] Harden month matching across GRACE, USDM, GLDAS, and TWS.
- [ ] Add expected-latest-data checks so the runner explains why a recent month is unavailable.
- [ ] Add retry and cache handling for public data downloads.
- [ ] Add source URLs and download timestamps to metadata.
- [ ] Add a clean "doctor" command for a full GRACE/USDM run folder.

Acceptance criteria:

- A 6-12 month GRACE-FO workflow can be run from documented commands.
- The dashboard reports exactly which months are available for each target.
- Missing months are treated as partial evidence, not hidden.

### Epic 4: GLDAS/TWS Hydrology Validation

Goal: compare GRACE/GRACE-FO signals against targets closer to terrestrial water storage than drought categories.

Required features:

- GLDAS/TWS file discovery.
- Month matching.
- Resampling/alignment to GRACE grid.
- Hydrology metric export.
- Dashboard coverage warning.
- Hydrology agreement panel.

Tasks:

- [x] Add hydrology metrics: correlation, RMSE, bias, trend agreement, sign agreement.
- [x] Add coverage warnings for incomplete hydrology months.
- [x] Add GLDAS/TWS summary artifacts.
- [ ] Add robust Earthdata/PO.DAAC download helper.
- [ ] Support `.netrc` and environment-variable credentials without leaking secrets.
- [ ] Add GLDAS doctor command to validate expected NetCDF variables.
- [ ] Add explicit resampling-method metadata.
- [ ] Add month-alignment table to dashboard.
- [ ] Add hydrology coverage timeline.
- [ ] Add tests for missing GLDAS month, extra GLDAS month, and bad variable name.

Acceptance criteria:

- Dashboard shows `N/M hydrology months available`.
- Hydrology metrics are never summarized without showing coverage.
- GLDAS/TWS data source, units, variable, and resampling method are visible in the report.

### Epic 5: Basin-Scale Validation

Goal: stop relying on rectangular crops and evaluate over meaningful hydrologic regions.

Required features:

- Authoritative basin or aquifer boundaries.
- Rasterization or spatial aggregation onto GRACE grid.
- Basin/month metrics.
- Basin time series.
- Basin map.
- Strongest/weakest basin callouts.

Tasks:

- [x] Add current western U.S. basin fixture.
- [x] Export basin metrics and summaries.
- [ ] Replace fixture geometry with authoritative basin, aquifer, HUC, or groundwater-management boundaries.
- [ ] Record basin boundary source, license, citation, and date.
- [ ] Add basin rasterization tests.
- [ ] Add basin-level GRACE/GLDAS/USDM time series plots.
- [ ] Add lagged correlation and trend agreement by basin.
- [ ] Add basin map with labels and target overlays.
- [ ] Add dashboard filters by basin.

Acceptance criteria:

- Every basin result is traceable to a named polygon source.
- The dashboard can answer which basin performed best, which performed worst, and why.
- Basin metrics are clearly separated from pixel-level detector metrics.

### Epic 6: Groundwater or Basin-Storage Target

Goal: add the validation target needed before making groundwater-related claims.

Required features:

- Direct or near-direct groundwater/storage dataset recipe.
- Importer contract for observations.
- Temporal alignment to GRACE months.
- Spatial alignment to basins.
- Validation metrics against observation time series.
- Dashboard readiness upgrade only when this target is present.

Candidate targets:

- USGS groundwater wells.
- Central Valley groundwater/storage studies.
- High Plains Aquifer observations.
- Basin storage observations.
- Groundwater depletion studies.
- State or water-district groundwater management datasets.

Tasks:

- [ ] Pick one primary groundwater or basin-storage validation target.
- [ ] Document source, access method, units, date range, citation, and limitations.
- [ ] Define observation schema: basin, date/month, value, units, uncertainty, source.
- [ ] Add loader for observation CSV.
- [ ] Add optional vector/basin join.
- [ ] Add temporal aggregation to monthly values.
- [ ] Add basin-level comparison metrics.
- [ ] Add dashboard section for groundwater/storage validation.
- [ ] Add readiness badge for direct groundwater/storage target.
- [ ] Add caveat language for sparse wells and spatial mismatch.

Acceptance criteria:

- At least one basin has a multimonth groundwater/storage comparison.
- The dashboard can show correlation, lagged correlation, trend agreement, and sign agreement against that target.
- The project can honestly say it has begun groundwater or basin-storage validation.

### Epic 7: Detector and Sensor Evidence

Goal: make detector and sensor comparisons credible, repeatable, and modestly stated.

Required features:

- z-score, DBSCAN, and isolation forest comparison.
- Parameter calibration.
- Spatial folds.
- Best-config reruns.
- Per-detector failure explanations.
- Sensor-profile uncertainty and sensitivity analysis.

Tasks:

- [x] Add z-score, DBSCAN, and isolation forest.
- [x] Add detector comparison metrics.
- [x] Add parameter sweeps.
- [x] Add best-config reruns.
- [x] Add k-fold spatial calibration.
- [ ] Add repeated seasonal or annual validation runs.
- [ ] Add sensitivity analysis over sensor noise assumptions.
- [ ] Add uncertainty bands for sensor-profile comparison.
- [ ] Add detector failure taxonomy.
- [ ] Add baseline "no detector" or simple threshold comparator.
- [ ] Add statistical significance or bootstrap comparison for sensor profiles.

Acceptance criteria:

- Detector claims are supported across multiple months and basins.
- The dashboard explains why z-score, DBSCAN, or isolation forest succeeded or failed.
- Quantum-inspired improvement is reported only if it is repeatable across basins/months and survives uncertainty checks.

### Epic 8: Dashboard and Storytelling

Goal: make the dashboard explain the project as a scientific validation story, not an artifact browser.

Required features:

- First-screen validation status.
- Claim boundary.
- Coverage timeline.
- Month-alignment table.
- Basin map.
- Hydrology agreement panel.
- Detector results.
- Failure cases.
- Reviewer verdict.
- Next dataset recommendation.

Tasks:

- [x] Add first-screen claim boundary.
- [x] Add validation status cards.
- [x] Add coverage warnings.
- [x] Add evidence trail.
- [x] Add readiness ladder.
- [ ] Redesign visual hierarchy for reviewer-grade polish.
- [ ] Add coverage timeline.
- [ ] Add month-alignment table.
- [ ] Add basin map with authoritative boundaries.
- [ ] Add basin time-series panel.
- [ ] Add hydrology agreement panel with interpretation text.
- [ ] Add detector confusion overlays with false positive/false negative explanations.
- [ ] Add exportable executive summary.
- [ ] Add downloadable report bundle manifest.

Acceptance criteria:

- A reviewer understands the project, evidence, and limits within the first screen.
- Every major chart answers: what it shows, what good looks like, what this run showed, and what not to conclude.
- The dashboard makes incomplete evidence visually obvious.

### Epic 9: Reporting and Artifact Contract

Goal: every run should produce durable, reviewable evidence.

Required features:

- Static HTML report.
- Streamlit dashboard compatibility.
- CSV and JSON outputs.
- Metadata.
- Summary markdown.
- Artifact manifest.
- Reproducibility bundle.

Tasks:

- [x] Export `results.json`, `results.csv`, `summary.csv`, and `metadata.json`.
- [x] Export `report.html`.
- [x] Export `experiment_summary.md`.
- [x] Export plots and overlays.
- [ ] Add `artifact_manifest.json`.
- [ ] Add machine-readable validation status.
- [ ] Add report version metadata.
- [ ] Add command replay script per output folder.
- [ ] Add checksum list for important inputs.
- [ ] Add optional compressed review bundle.

Acceptance criteria:

- A reviewer can reconstruct what command ran, what data were used, and what artifacts support each conclusion.
- Artifacts are versioned enough that dashboard changes do not silently reinterpret old outputs.

### Epic 10: Testing and CI

Goal: prevent scientific and workflow regressions.

Required features:

- Unit tests.
- Integration tests.
- Demo smoke tests.
- Dashboard import tests.
- Data-loader tests.
- CI on GitHub.

Tasks:

- [x] Add pytest suite.
- [x] Add dashboard import smoke test.
- [x] Add demo artifact generation test.
- [x] Add installed CLI smoke in CI.
- [ ] Add Streamlit AppTest smoke if feasible.
- [ ] Add generated temporary GeoTIFF test in CI without requiring external files.
- [ ] Add generated temporary NetCDF test.
- [ ] Add basin rasterization test.
- [ ] Add coverage-alignment tests.
- [ ] Add manifest schema tests.
- [ ] Add regression fixture for a known multimonth output summary.

Acceptance criteria:

- CI passes on every push.
- CI catches broken CLI, broken demo, broken dashboard import, broken geospatial loaders, and broken metric exports.

### Epic 11: Documentation and Release Readiness

Goal: make the repo understandable and trustworthy to outsiders.

Required features:

- Strong README.
- Comprehensive project explainer.
- Finish-line plan.
- Real-data import docs.
- Contribution guide.
- License.
- Citation metadata.
- Changelog.

Tasks:

- [x] Add README claim boundary.
- [x] Add screenshot.
- [x] Add `LICENSE`.
- [x] Add `CONTRIBUTING.md`.
- [x] Add `CITATION.cff`.
- [x] Add `docs/WHAT_THIS_PROJECT_DOES.md`.
- [x] Add this finish-line plan.
- [ ] Link this plan from README.
- [ ] Add `CHANGELOG.md`.
- [ ] Add `docs/DATA_SOURCES.md`.
- [ ] Add `docs/SCIENTIFIC_CLAIMS.md`.
- [ ] Add `docs/DASHBOARD_GUIDE.md`.
- [ ] Add release checklist.

Acceptance criteria:

- A new reviewer can understand what the project does, what it proves, what it does not prove, how to run it, and what remains.

## Finish-Line Feature Checklist

The project should ship with these user-facing features:

- [ ] One-command download-free demo.
- [ ] One-command recent GRACE-FO/USDM run.
- [ ] Optional authenticated GLDAS/TWS download helper.
- [ ] Manifest doctor.
- [ ] Run-folder doctor.
- [ ] Dashboard for multimonth validation.
- [ ] Static HTML report for every run.
- [ ] Artifact manifest for every run.
- [ ] Basin map and basin time series.
- [ ] Month coverage timeline.
- [ ] Month alignment table.
- [ ] Detector comparison table.
- [ ] Detector failure explanation panel.
- [ ] Hydrology agreement panel.
- [ ] Groundwater/storage validation panel.
- [ ] Scientific readiness badge.
- [ ] Claim-boundary panel.
- [ ] Executive summary export.
- [ ] Reproducibility metadata export.

## Finish-Line Evidence Checklist

The project should have these evidence artifacts before being called finished:

- [ ] At least one 6-12 month GRACE-FO run.
- [ ] Complete USDM alignment for the selected months.
- [ ] Complete or explicitly partial GLDAS/TWS alignment.
- [ ] At least one authoritative basin boundary source.
- [ ] At least one groundwater or basin-storage observation dataset.
- [ ] Basin-level comparison over multiple months.
- [ ] Detector comparison over multiple months and basins.
- [ ] Sensor-profile sensitivity analysis.
- [ ] Documentation of failures and non-results.
- [ ] A final report that states exactly what was validated.

## Final Claim Levels

The project can support different claim levels depending on completed evidence.

### Claim Level 1: Software Workflow

Allowed claim:

> The project provides a reproducible workflow for gravity-derived anomaly detection experiments.

Required evidence:

- synthetic/pseudo-real demo
- CI
- exported metrics
- metadata

Current status: reached.

### Claim Level 2: Real Raster Validation

Allowed claim:

> The project can validate detector behavior on real GRACE/GRACE-FO derived rasters.

Required evidence:

- real raster ingestion
- CRS/nodata/provenance
- real-data manifest
- report artifacts

Current status: mostly reached.

### Claim Level 3: Independent Drought Proxy Validation

Allowed claim:

> The project compares GRACE/GRACE-FO detector outputs against independent drought-proxy labels.

Required evidence:

- USDM masks
- month alignment
- D1/D2/D3 thresholds
- detector metrics

Current status: reached, but needs stronger coverage polish.

### Claim Level 4: External Hydrology Validation

Allowed claim:

> The project compares gravity-derived water-mass signals against external hydrology or TWS targets.

Required evidence:

- GLDAS/TWS data
- month coverage reporting
- hydrology metrics
- resampling metadata

Current status: partial.

### Claim Level 5: Basin/Groundwater Validation

Allowed claim:

> The project evaluates gravity-derived water-mass signals against basin-scale storage or groundwater observations.

Required evidence:

- authoritative basin boundaries
- groundwater/storage observations
- multimonth comparison
- uncertainty/caveat reporting

Current status: not reached.

### Claim Level 6: Quantum-Inspired Advantage

Allowed claim:

> Under documented simulation assumptions, the quantum-inspired sensor profile improves downstream validation metrics compared with the classical profile.

Required evidence:

- repeated multimonth/basin results
- uncertainty analysis
- matched baselines
- sensitivity to sensor parameters
- statistically meaningful comparison

Current status: not reached.

## Recommended Build Order

Build in this order:

1. Link docs and stabilize repo release materials.
2. Harden month alignment and hydrology coverage reporting.
3. Replace fixture basins with authoritative basin boundaries.
4. Add groundwater or basin-storage observation workflow.
5. Redesign dashboard around basin/hydrology validation, not detector spectacle.
6. Add sensor-profile sensitivity analysis.
7. Add final release bundle and final scientific report.

## Final Release Gate

Before tagging a "finished" release, run this gate:

- [ ] `python -m pytest -q` passes.
- [ ] GitHub Actions passes.
- [ ] `python -m quantum_sensing_earth.demo --output outputs/demo` succeeds.
- [ ] A 6-12 month GRACE-FO run succeeds.
- [ ] Dashboard launches on that run.
- [ ] Manifest doctor reports no errors for final real-data run.
- [ ] Hydrology coverage is complete or explicitly explained.
- [ ] Basin validation uses authoritative boundaries.
- [ ] Groundwater/storage target is present or the release explicitly says no groundwater claim is made.
- [ ] README, project explainer, and dashboard all agree on the claim level.
- [ ] Generated reports state what is proved and what is not proved.

## The Real Finish Line

The real finish line is not "the app looks good" or "the detectors run." The finish line is that an outside reviewer can open the repository, run the demo, inspect a real-data validation run, understand the provenance, see the evidence, see the gaps, and agree that the stated claim is supported by the artifacts.

If the final claim is only workflow validation, the project can finish sooner.

If the final claim is groundwater validation, the project is not finished until independent groundwater or basin-storage observations are included.

If the final claim is quantum advantage, the project is not finished until the quantum-inspired profile beats the classical profile repeatedly under documented assumptions and uncertainty checks.
