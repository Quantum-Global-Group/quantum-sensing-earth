# Tasks

This is the active finish-line task list. See [docs/FINISH_LINE_PLAN.md](docs/FINISH_LINE_PLAN.md) for the full completion strategy, acceptance criteria, and claim levels. See [docs/SPRINT_PLAN.md](docs/SPRINT_PLAN.md), [docs/PRODUCT_BACKLOG.md](docs/PRODUCT_BACKLOG.md), [docs/MILESTONES.md](docs/MILESTONES.md), and [docs/RISK_AND_DEPENDENCY_REGISTER.md](docs/RISK_AND_DEPENDENCY_REGISTER.md) for project-management tracking.

## Already Completed

- [x] Create project documentation files
- [x] Create YAML/JSON configs
- [x] Create source folders
- [x] Create baseline MVP runner
- [x] Generate synthetic gravity anomaly fields
- [x] Add sensor-specific noise models
- [x] Implement anomaly detectors
- [x] Export results JSON/CSV
- [x] Add parameter sweeps and best-config reruns
- [x] Add detector comparison metrics
- [x] Add IoU, FPR, FNR, and localization metrics
- [x] Add validation CSV fixtures
- [x] Add optional GeoTIFF importer
- [x] Add validation manifest and doctor command
- [x] Add GRACE Tellus workflow scaffolding
- [x] Add multimonth GRACE/USDM runner
- [x] Add GLDAS/TWS hydrology metric path
- [x] Add basin fixture and basin summary outputs
- [x] Add Streamlit technical-review dashboard
- [x] Add download-free demo command
- [x] Add GitHub CI
- [x] Add README, license, contribution guide, citation metadata, and screenshot
- [x] Add comprehensive project explainer
- [x] Add finish-line plan
- [x] Add PM sprint/backlog/milestone docs
- [x] Add artifact manifest generation
- [x] Add month coverage summary and alignment artifacts
- [x] Add Central Valley B118 basin prep scaffold
- [x] Add groundwater observation loader, basin assignment, and metrics
- [x] Add dashboard groundwater validation section
- [x] Add release checklist

## Finish-Line Actions

### Data Credibility

- [x] Harden month matching across GRACE, USDM, GLDAS, and TWS.
- [x] Add hydrology coverage timeline and month-alignment table.
- [ ] Add robust GLDAS/TWS doctor checks.
- [ ] Add formal manifest schema version.
- [ ] Add importer tests for malformed GeoTIFF, NetCDF, nodata, missing CRS, and mismatched masks.

### Basin Validation

- [x] Replace basin fixture with authoritative basin, aquifer, HUC, or groundwater-management boundaries.
- [x] Record basin source, license, citation, and date.
- [ ] Add basin rasterization tests.
- [x] Add basin map with labels and overlays.
- [x] Add basin time-series dashboard panel.

### Groundwater or Basin-Storage Validation

- [x] Choose one direct or near-direct validation target: wells, basin storage, aquifer observations, or groundwater study data.
- [x] Document source, access, units, date range, citation, limitations, and preprocessing.
- [x] Define observation CSV schema.
- [x] Add loader for observation data.
- [x] Add basin/month alignment to GRACE/GRACE-FO.
- [x] Add groundwater/storage dashboard panel.

### Detector and Sensor Evidence

- [ ] Add repeated 6-12 month GRACE-FO validation run.
- [ ] Add detector failure taxonomy.
- [ ] Add baseline threshold comparator.
- [ ] Add sensor-profile sensitivity analysis.
- [ ] Add uncertainty/statistical comparison between classical and quantum-inspired profiles.

### Dashboard and Reports

- [ ] Redesign dashboard visual hierarchy for reviewer-grade polish.
- [x] Add coverage timeline.
- [x] Add month-alignment table.
- [ ] Add hydrology agreement panel.
- [ ] Add detector confusion overlays with false-positive and false-negative explanations.
- [x] Add exportable executive summary.
- [x] Add `artifact_manifest.json` for every run.
- [ ] Add command replay script for each output folder.

### Release Readiness

- [x] Link finish-line docs from README.
- [x] Add `CHANGELOG.md`.
- [x] Add `docs/DATA_SOURCES.md`.
- [x] Add `docs/SCIENTIFIC_CLAIMS.md`.
- [x] Add `docs/DASHBOARD_GUIDE.md`.
- [ ] Tag first version after final validation run.

## Final Release Gate

- [ ] `python -m pytest -q` passes.
- [ ] GitHub Actions passes.
- [ ] `python -m quantum_sensing_earth.demo --output outputs/demo` succeeds.
- [ ] A 6-12 month GRACE-FO run succeeds.
- [ ] Dashboard launches on the final run.
- [ ] Manifest doctor reports no errors.
- [ ] Hydrology coverage is complete or explicitly explained.
- [ ] Basin validation uses authoritative boundaries.
- [ ] Groundwater/storage target is present, or the release explicitly says no groundwater claim is made.
- [ ] README, project explainer, dashboard, and final report all agree on the supported claim level.
