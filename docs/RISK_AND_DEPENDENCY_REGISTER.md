# Risk and Dependency Register

## Risk Ratings

Likelihood and impact are scored from 1 to 5.

Risk score = likelihood x impact.

| Score | Severity |
| --- | --- |
| 1-5 | Low |
| 6-12 | Medium |
| 13-25 | High |

## Risks

| ID | Risk | Likelihood | Impact | Score | Owner | Mitigation | Trigger |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Groundwater target is hard to source or align | 4 | 5 | 20 | Scientific Lead | Start with documented manual workflow and one basin | Sprint 5 cannot identify source |
| R2 | USDM is overinterpreted as groundwater truth | 3 | 5 | 15 | Project Owner | Keep claim-boundary warnings in docs/dashboard | Reviewer confusion or marketing misuse |
| R3 | GLDAS/TWS month coverage remains incomplete | 4 | 4 | 16 | Data Engineer | Coverage timeline and partial-evidence labels | Coverage below final threshold |
| R4 | Authoritative basin boundaries have licensing constraints | 3 | 4 | 12 | Data Engineer | Pick open public-domain or clearly licensed source | Cannot redistribute boundary file |
| R5 | GRACE/GRACE-FO latest data availability lags current date | 4 | 3 | 12 | Data Engineer | Report latest available month explicitly | Recent run misses requested months |
| R6 | Dashboard becomes visually polished but scientifically unclear | 3 | 4 | 12 | Dashboard Engineer | Require "what this shows / do not conclude" captions | First-screen review fails |
| R7 | Quantum-inspired claims outrun evidence | 3 | 5 | 15 | Scientific Lead | Require uncertainty and repeated comparison before claims | Any release text says quantum advantage prematurely |
| R8 | Earthdata credentials or tokens leak into repo | 2 | 5 | 10 | QA/Release | Secret scans, `.gitignore`, docs use placeholders | Secret scan hit |
| R9 | CI becomes slow or flaky with geospatial dependencies | 3 | 3 | 9 | QA/Release | Use generated fixtures and optional geo tests | CI exceeds acceptable runtime |
| R10 | Real-data workflows are too manual for reviewers | 3 | 3 | 9 | Project Owner | Provide one documented recipe and one demo path | Reviewer cannot reproduce run |

## Dependencies

| ID | Dependency | Needed For | Owner | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| D1 | GRACE/GRACE-FO public monthly rasters | Real raster validation | Data Engineer | Available with workflow | Availability may lag current month |
| D2 | USDM shapefiles or masks | Drought proxy validation | Data Engineer | Available with workflow | Proxy only, not groundwater truth |
| D3 | GLDAS/TWS NetCDF files | External hydrology validation | Data Engineer | Partial | Requires authenticated/manual download path |
| D4 | Authoritative basin/aquifer boundaries | Basin validation | Scientific Lead | Not selected | Must resolve citation/license |
| D5 | Groundwater/storage observations | Groundwater validation | Scientific Lead | Not selected | Biggest scientific dependency |
| D6 | rasterio/netCDF4 optional deps | Geo workflows | QA/Release | Optional | Need tests that handle missing extras |
| D7 | GitHub Actions | Release confidence | QA/Release | Active | Passing currently, watch dependency changes |

## Blocker Escalation Rules

Escalate immediately if:

- no groundwater/storage target is selected by the end of Sprint 4;
- authoritative basin boundaries cannot be used or cited;
- hydrology coverage is below the agreed minimum for final release;
- dashboard or docs imply groundwater or quantum advantage before evidence exists;
- CI fails on main;
- a secret or credential appears in git status, diff, logs, or committed files.

## Claim Safety Controls

Required controls:

- README claim boundary.
- Dashboard claim-boundary panel.
- Scientific claims guide.
- Report caveat section.
- Manifest weak-label field.
- Hydrology coverage warning.
- Release checklist item confirming supported claim level.

