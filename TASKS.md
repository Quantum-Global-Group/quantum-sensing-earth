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

## Finish-Line Actions

### Data Credibility

- [ ] Harden month matching across GRACE, USDM, GLDAS, and TWS.
- [ ] Add hydrology coverage timeline and month-alignment table.
- [ ] Add robust GLDAS/TWS doctor checks.
- [ ] Add formal manifest schema version.
- [ ] Add importer tests for malformed GeoTIFF, NetCDF, nodata, missing CRS, and mismatched masks.

### Basin Validation

- [ ] Replace basin fixture with authoritative basin, aquifer, HUC, or groundwater-management boundaries.
- [ ] Record basin source, license, citation, and date.
- [ ] Add basin rasterization tests.
- [ ] Add basin map with labels and overlays.
- [ ] Add basin time-series dashboard panel.

### Groundwater or Basin-Storage Validation

- [ ] Choose one direct or near-direct validation target: wells, basin storage, aquifer observations, or groundwater study data.
- [ ] Document source, access, units, date range, citation, limitations, and preprocessing.
- [ ] Define observation CSV schema.
- [ ] Add loader for observation data.
- [ ] Add basin/month alignment to GRACE/GRACE-FO.
- [ ] Add groundwater/storage dashboard panel.

### Detector and Sensor Evidence

- [ ] Add repeated 6-12 month GRACE-FO validation run.
- [ ] Add detector failure taxonomy.
- [ ] Add baseline threshold comparator.
- [ ] Add sensor-profile sensitivity analysis.
- [ ] Add uncertainty/statistical comparison between classical and quantum-inspired profiles.

### Dashboard and Reports

- [ ] Redesign dashboard visual hierarchy for reviewer-grade polish.
- [ ] Add coverage timeline.
- [ ] Add month-alignment table.
- [ ] Add hydrology agreement panel.
- [ ] Add detector confusion overlays with false-positive and false-negative explanations.
- [ ] Add exportable executive summary.
- [ ] Add `artifact_manifest.json` for every run.
- [ ] Add command replay script for each output folder.

### Release Readiness

- [ ] Link finish-line docs from README.
- [ ] Add `CHANGELOG.md`.
- [ ] Add `docs/DATA_SOURCES.md`.
- [ ] Add `docs/SCIENTIFIC_CLAIMS.md`.
- [ ] Add `docs/DASHBOARD_GUIDE.md`.
- [ ] Add release checklist and first version tag.

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
