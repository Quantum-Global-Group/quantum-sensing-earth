# Milestones

## Milestone Summary

| Milestone | Name | Planned Sprint | Claim Level Enabled | Status |
| --- | --- | --- | --- | --- |
| M1 | Project Control Baseline | Sprint 1 | Level 1 | Planned |
| M2 | Trustworthy Coverage Layer | Sprint 2 | Level 3/4 support | Planned |
| M3 | External Hydrology Hardening | Sprint 3 | Level 4 | Planned |
| M4 | Authoritative Basin Validation | Sprint 4 | Level 4/5 support | Planned |
| M5 | Groundwater/Storage Target | Sprint 5 | Level 5 | Planned |
| M6 | Release Candidate | Sprint 6 | Final selected level | Planned |

## M1: Project Control Baseline

### Goal

Make the project manageable and release-trackable.

### Deliverables

- PM plan
- sprint plan
- product backlog
- milestone list
- risk/dependency register
- changelog
- artifact manifest generation

### Exit Criteria

- Docs are linked from README.
- Standard runs export artifact manifests.
- CI passes.

## M2: Trustworthy Coverage Layer

### Goal

Make month coverage impossible to misunderstand.

### Deliverables

- normalized month keys
- `coverage_summary.json`
- `month_alignment.csv`
- dashboard coverage timeline
- dashboard month-alignment table
- missing/extra month tests

### Exit Criteria

- Dashboard shows coverage by target.
- Missing months are visible.
- Hydrology metrics are marked partial when coverage is incomplete.

## M3: External Hydrology Hardening

### Goal

Make GLDAS/TWS validation reliable enough for external hydrology claims.

### Deliverables

- GLDAS/TWS doctor command
- NetCDF fixture tests
- variable and unit validation
- resampling metadata
- updated data-source docs

### Exit Criteria

- Doctor catches bad hydrology inputs.
- Reports show hydrology source, units, and resampling method.

## M4: Authoritative Basin Validation

### Goal

Evaluate over named scientific regions instead of a rectangular crop or fixture geometry.

### Deliverables

- authoritative basin/aquifer/HUC source decision
- conversion and rasterization workflow
- basin provenance
- basin tests
- basin map
- basin time series

### Exit Criteria

- Basin outputs cite their boundary source.
- Dashboard shows basin metrics and interpretation.

## M5: Groundwater/Storage Target

### Goal

Add the target needed before making groundwater-related validation claims.

### Deliverables

- selected groundwater/storage source
- observation schema
- observation loader
- basin/month alignment
- validation metrics
- dashboard panel
- caveat language

### Exit Criteria

- At least one basin has multimonth groundwater/storage validation.
- Dashboard distinguishes direct/near-direct target from drought proxy.

## M6: Release Candidate

### Goal

Ship a coherent, claim-safe release.

### Deliverables

- final dashboard pass
- executive summary
- report bundle manifest
- final 6-12 month run
- final docs
- release notes
- release tag

### Exit Criteria

- CI passes.
- Final release gate passes.
- README, dashboard, final report, and docs agree on the supported claim level.

