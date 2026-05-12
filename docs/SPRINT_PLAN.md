# Sprint Plan

## Sprint Structure

Sprint length: 2 weeks.

Planning assumption: one small team or one agentic development lane. If more engineers join, split each sprint into parallel data, dashboard, and QA tracks.

## Current Release Snapshot

As of 2026-05-12, the project has moved from scaffold work into release validation:

- Live DWR Bulletin 118 Central Valley basin prep has been run locally and produced 35 basin/subbasin features.
- Official DWR Periodic Groundwater Level Measurements station and measurement CSVs have been downloaded locally.
- DWR observations have been normalized into `data/central_valley/groundwater/dwr_groundwater_clean.csv` with 221,192 rows, 17 months, and 35 basins.
- A six-month GRACE-FO Central Valley evidence bundle exists at `outputs/central_valley_groundwater_release`.
- That bundle reports 6/6 coverage for GRACE, USDM, GLDAS, TWS, basin, and groundwater targets.
- Local tests, demo smoke, Streamlit smoke, and GitHub CI have passed for the latest P0 checkpoint.

The remaining release focus is no longer basic capability. It is final review quality: claim consistency, dashboard visual review, twelve-month preferred run if coverage allows, and release tagging.

## Sprint 1: Project Control and Data Credibility Baseline

### Sprint Goal

Turn the current finish-line plan into an executable project system and close the obvious release-readiness gaps.

### Why This Sprint Matters

The project has strong technical pieces, but it needs PM control, traceable artifacts, and clearer data-governance rules before deeper science work starts.

### User Stories

- As a reviewer, I want to know what claim level this project currently supports so I do not overinterpret the results.
- As a developer, I want a structured backlog so I know what to build next.
- As a release owner, I want every run to have an artifact manifest so outputs are easier to audit.

### Committed Work

- [x] Link `docs/WHAT_THIS_PROJECT_DOES.md` and `docs/FINISH_LINE_PLAN.md` from README.
- [x] Add `docs/PROJECT_MANAGEMENT_PLAN.md`.
- [x] Add `docs/SPRINT_PLAN.md`.
- [x] Add `docs/PRODUCT_BACKLOG.md`.
- [x] Add `docs/MILESTONES.md`.
- [x] Add `docs/RISK_AND_DEPENDENCY_REGISTER.md`.
- [x] Add `CHANGELOG.md`.
- [x] Add `artifact_manifest.json` generation for standard CLI runs.
- [x] Add test for artifact manifest generation.
- [x] Add release checklist section to docs.

### Acceptance Criteria

- PM docs exist and are internally consistent.
- README links to project explainer and finish-line plan.
- A standard output folder includes an artifact manifest.
- CI passes.

### Demo

Run:

```bash
python -m quantum_sensing_earth.demo --output outputs/demo
python -m pytest -q
```

Show:

- artifact manifest;
- updated docs;
- passing tests.

## Sprint 2: Hydrology Coverage and Month Alignment

### Sprint Goal

Make GRACE, USDM, GLDAS, and TWS coverage alignment trustworthy and visible.

### Why This Sprint Matters

A reviewer should never think hydrology metrics cover all detector months if they do not. Partial evidence must be explicit.

### User Stories

- As a reviewer, I want to see which months have GRACE, USDM, GLDAS, and TWS coverage.
- As a scientist, I want hydrology metrics separated from incomplete target coverage.
- As a developer, I want tests that catch missing or mismatched month keys.

### Committed Work

- [x] Normalize month keys across GRACE, USDM, GLDAS, and TWS.
- [x] Add `coverage_summary.json`.
- [x] Add `month_alignment.csv`.
- [x] Add dashboard coverage timeline.
- [x] Add dashboard month-alignment table.
- [x] Add tests for missing GLDAS month.
- [x] Add tests for extra GLDAS/TWS month.
- [x] Add tests for inconsistent month formatting.
- [x] Add clearer warning text in reports and dashboard.

### Acceptance Criteria

- Dashboard displays `N/M` coverage for each target.
- Missing months are listed by month.
- Hydrology summary metrics display coverage next to every aggregate.
- Tests fail when month matching is wrong.

### Demo

Run a multimonth workflow and show:

- coverage timeline;
- month-alignment table;
- warnings when a target is missing.

## Sprint 3: GLDAS/TWS Hardening

### Sprint Goal

Make external hydrology validation reliable enough to support claim level 4.

### Why This Sprint Matters

USDM is only a drought proxy. GLDAS/TWS is closer to terrestrial water storage and gives the project a stronger validation track.

### User Stories

- As a user, I want a doctor command that tells me whether my GLDAS/TWS files are usable.
- As a reviewer, I want units, variable names, resampling method, and coverage visible.
- As a developer, I want NetCDF edge cases covered by tests.

### Committed Work

- [ ] Add GLDAS/TWS doctor command.
- [ ] Validate expected NetCDF variables.
- [ ] Validate units and month metadata.
- [ ] Record resampling method in metadata.
- [ ] Add generated temporary NetCDF fixture test.
- [ ] Add bad-variable-name test.
- [ ] Add missing-units warning.
- [ ] Update GRACE Tellus README with GLDAS/TWS steps.
- [x] Confirm GLDAS/TWS are month-aligned in the six-month Central Valley release bundle.
- [x] Show GLDAS/TWS target coverage in `coverage_summary.json`, `month_alignment.csv`, and the dashboard.

### Acceptance Criteria

- Doctor catches missing files, unreadable files, missing variables, and missing units.
- Hydrology metrics include resampling metadata.
- Dashboard provenance panel shows GLDAS/TWS source, units, and method.

### Demo

Show:

- successful GLDAS/TWS doctor;
- failed doctor with actionable error;
- dashboard hydrology provenance.

## Sprint 4: Authoritative Basin Validation

### Sprint Goal

Replace fixture basin validation with authoritative, cited basin or aquifer boundaries.

### Why This Sprint Matters

GRACE/GRACE-FO is coarse. Basin-scale validation is more honest than pixel-level interpretation.

### User Stories

- As a scientist, I want validation summarized over named hydrologic regions.
- As a reviewer, I want to know exactly where basin boundaries came from.
- As a dashboard user, I want basin maps and time series.

### Committed Work

- [x] Select authoritative basin, aquifer, HUC, or groundwater-management boundary source.
- [x] Add data-source documentation and citation.
- [x] Add boundary conversion/rasterization workflow.
- [x] Add basin-source manifest fields.
- [ ] Add basin rasterization tests.
- [x] Add basin map with labels.
- [x] Add basin time-series panel.
- [x] Add strongest/weakest basin callouts.
- [x] Run live DWR Bulletin 118 Central Valley basin prep locally.
- [x] Produce `data/central_valley/basins/central_valley_b118_basins.geojson`.
- [x] Produce `data/central_valley/basins/central_valley_basin_manifest.yaml`.

### Acceptance Criteria

- Basin results are traceable to a named source.
- Basin metrics include GRACE mean, GLDAS mean, USDM coverage, correlation, lagged correlation, and trend agreement.
- Dashboard has a basin map and basin comparison table.

### Demo

Show:

- authoritative basin source;
- basin map;
- basin metrics table;
- strongest/weakest basin explanation.

## Sprint 5: Groundwater or Basin-Storage Target

### Sprint Goal

Add the first direct or near-direct groundwater/storage validation target.

### Why This Sprint Matters

This is the key transition from workflow validation to groundwater-relevant validation.

### User Stories

- As a scientist, I want a validation target closer to groundwater truth than USDM or GLDAS.
- As a reviewer, I want the source, units, uncertainty, and limitations documented.
- As a dashboard user, I want to compare GRACE/GRACE-FO basin signals against observed groundwater/storage behavior.

### Committed Work

- [x] Select first groundwater/storage target.
- [x] Document access, units, date range, citation, limitations.
- [x] Define observation CSV schema.
- [x] Add observation loader.
- [x] Add DWR groundwater prep command for bulk ZIP and station/measurement CSV inputs.
- [x] Add official DWR Stations and Measurements discovery/download support.
- [x] Add chunked month-window filtering for large DWR measurement CSVs.
- [x] Normalize DWR `gwe` as groundwater elevation in feet.
- [x] Preserve raw value/date/source audit fields.
- [x] Restrict existing groundwater basin codes to the supplied B118 basin file.
- [x] Add basin/month alignment.
- [x] Add groundwater/storage metrics.
- [x] Add dashboard groundwater/storage panel.
- [x] Add readiness badge upgrade logic.
- [x] Add tests for observation schema.
- [x] Generate local DWR clean groundwater CSV for Central Valley release validation.

### Acceptance Criteria

- At least one basin has multimonth groundwater/storage observations. Current local result: 35 basins across 17 DWR months.
- Dashboard distinguishes groundwater/storage validation from drought and GLDAS validation.
- Project can truthfully say it has begun groundwater or basin-storage validation.

### Demo

Show:

- observation input;
- aligned basin/month table;
- groundwater/storage metrics;
- dashboard panel and caveats.

## Sprint 6: Reviewer-Grade Dashboard and Final Release Candidate

### Sprint Goal

Make the project shippable as a finished workflow-validation or early groundwater-validation release, depending on Sprint 5 evidence.

### Why This Sprint Matters

The final release must be readable, defensible, and hard to overclaim.

### User Stories

- As a reviewer, I want the first screen to tell me what was validated and what was not.
- As a project owner, I want a final release checklist and claim-level decision.
- As a user, I want an executive summary I can share.

### Committed Work

- [x] Redesign dashboard information hierarchy.
- [x] Add executive summary export.
- [x] Add final reviewer verdict panel.
- [ ] Add detector confusion overlays.
- [x] Add report bundle manifest.
- [x] Add `docs/SCIENTIFIC_CLAIMS.md`.
- [x] Add `docs/DATA_SOURCES.md`.
- [x] Add `docs/DASHBOARD_GUIDE.md`.
- [x] Run minimum six-month Central Valley validation.
- [ ] Run preferred twelve-month Central Valley validation if coverage allows.
- [ ] Complete final dashboard visual review.
- [ ] Confirm README, dashboard, docs, and executive summary agree on claim level.
- [ ] Complete release checklist.
- [ ] Tag first release.

### Acceptance Criteria

- Dashboard clearly states supported claim level.
- Final report and README agree with dashboard.
- CI passes.
- Final validation run is archived with artifacts.
- Release checklist is complete.

### Demo

Show:

- final dashboard;
- final report;
- final claim level;
- release tag;
- evidence bundle.

## Sprint 7: Release Closure

### Sprint Goal

Turn the completed six-month Central Valley evidence path into a first tagged release.

### Why This Sprint Matters

Most P0 capability now exists. The release should only be tagged after a reviewer can open the dashboard, understand the claim boundary immediately, and reproduce the release path without hidden local assumptions.

### User Stories

- As a reviewer, I want the dashboard, README, docs, and executive summary to say the same thing about what is and is not proven.
- As a release owner, I want the final output folder to pass artifact, coverage, and dashboard checks.
- As a scientist, I want the strongest groundwater result to be presented with sample-size and caveat context.

### Committed Work

- [ ] Run the preferred twelve-month GRACE-FO Central Valley validation, or document why six months is the release scope.
- [ ] Review the Streamlit dashboard visually against `outputs/central_valley_groundwater_release`.
- [ ] Confirm the first screen shows validation status, readiness ladder, month coverage, strongest/weakest basin, and claim boundary.
- [ ] Confirm the groundwater section shows basin selector, GRACE-vs-groundwater time series, lag/correlation panel, and observation coverage warnings.
- [ ] Confirm detector visuals stay secondary to hydrology and groundwater validation.
- [ ] Update release notes with validated/not-validated language.
- [ ] Complete `docs/RELEASE_CHECKLIST.md`.
- [ ] Tag the first release after CI is green.

### Acceptance Criteria

- `python -m pytest -q` passes.
- `python -m quantum_sensing_earth.demo --output outputs/demo` passes.
- GitHub Actions passes.
- Final Central Valley dashboard opens locally.
- No `data/`, `outputs/`, credentials, or tokens are committed.
- Release tag is created only after the claim-level review is complete.

### Demo

Show:

- final Central Valley dashboard;
- `coverage_summary.json` with target coverage;
- `executive_summary.md`;
- completed release checklist;
- release tag.
