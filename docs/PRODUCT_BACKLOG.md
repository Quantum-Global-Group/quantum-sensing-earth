# Product Backlog

## Backlog Status Definitions

| Status | Meaning |
| --- | --- |
| Todo | Not started |
| Ready | Defined enough to pull into sprint |
| In Progress | Actively being built |
| Blocked | Waiting on decision, data, access, or dependency |
| Review | Built and awaiting review |
| Done | Merged, tested, and documented |

## Priority Definitions

| Priority | Meaning |
| --- | --- |
| P0 | Required for project finish |
| P1 | Required for strong release |
| P2 | Valuable improvement |
| P3 | Nice to have |

## Backlog Items

| ID | Epic | Item | Priority | Status | Target Sprint | Acceptance Criteria |
| --- | --- | --- | --- | --- | --- | --- |
| QSE-001 | Project Control | Link finish-line docs from README | P1 | Done | Sprint 1 | README links to project explainer, finish plan, sprint plan |
| QSE-002 | Project Control | Add changelog | P1 | Done | Sprint 1 | `CHANGELOG.md` exists with initial unreleased section |
| QSE-003 | Reporting | Generate `artifact_manifest.json` | P0 | Done | Sprint 1 | Every standard run lists key artifacts and paths |
| QSE-004 | Reporting | Add artifact manifest test | P0 | Done | Sprint 1 | Test confirms manifest exists after CLI run |
| QSE-005 | Data Credibility | Normalize month keys across targets | P0 | Done | Sprint 2 | GRACE, USDM, GLDAS, TWS use common month keys |
| QSE-006 | Data Credibility | Export `coverage_summary.json` | P0 | Done | Sprint 2 | Summary lists available and missing months by target |
| QSE-007 | Data Credibility | Export `month_alignment.csv` | P0 | Done | Sprint 2 | CSV has one row per month with target availability flags |
| QSE-008 | Dashboard | Add coverage timeline | P0 | Done | Sprint 2 | Dashboard shows target availability over time |
| QSE-009 | Dashboard | Add month-alignment table | P0 | Done | Sprint 2 | Dashboard table lists missing months and target status |
| QSE-010 | Tests | Add month-alignment tests | P0 | Done | Sprint 2 | Missing/extra/inconsistent month tests pass |
| QSE-011 | Hydrology | Add GLDAS/TWS doctor command | P0 | Todo | Sprint 3 | Doctor validates files, variables, units, and month metadata |
| QSE-012 | Hydrology | Add generated NetCDF fixture tests | P1 | Todo | Sprint 3 | CI tests NetCDF read and bad variable handling |
| QSE-013 | Hydrology | Record resampling method metadata | P0 | Todo | Sprint 3 | Metadata and dashboard show resampling method |
| QSE-014 | Docs | Update GLDAS/TWS manual workflow | P1 | Todo | Sprint 3 | README or data-source docs include exact steps |
| QSE-015 | Basin | Select authoritative basin boundary source | P0 | Done | Sprint 4 | Decision documented with citation and license |
| QSE-016 | Basin | Add basin conversion/rasterization workflow | P0 | Done | Sprint 4 | Boundaries align to GRACE grid |
| QSE-017 | Basin | Add basin rasterization tests | P1 | Todo | Sprint 4 | Generated or fixture polygons rasterize correctly |
| QSE-018 | Dashboard | Add basin map and labels | P0 | Done | Sprint 4 | Dashboard displays named basin boundaries |
| QSE-019 | Dashboard | Add basin time-series panel | P1 | Done | Sprint 4 | GRACE/GLDAS/USDM shown by basin/month |
| QSE-020 | Science | Select groundwater/storage validation target | P0 | Done | Sprint 5 | Target source and claim rationale documented |
| QSE-021 | Data | Define observation CSV schema | P0 | Done | Sprint 5 | Schema supports basin, month, value, units, source, uncertainty |
| QSE-022 | Data | Add groundwater/storage observation loader | P0 | Done | Sprint 5 | Loader reads observations and validates schema |
| QSE-023 | Science | Add basin/month observation metrics | P0 | Done | Sprint 5 | Correlation, lagged correlation, trend, sign agreement exported |
| QSE-024 | Dashboard | Add groundwater/storage panel | P0 | Done | Sprint 5 | Dashboard separates groundwater/storage from drought proxy |
| QSE-025 | Dashboard | Redesign final dashboard hierarchy | P0 | Done | Sprint 6 | First screen explains status, claim boundary, and evidence |
| QSE-026 | Reporting | Add executive summary export | P1 | Done | Sprint 6 | Markdown or HTML summary generated from run artifacts |
| QSE-027 | Reporting | Add report bundle manifest | P1 | Done | Sprint 6 | Final bundle lists dashboard-review artifacts |
| QSE-028 | Docs | Add scientific claims guide | P0 | Done | Sprint 6 | Claim levels and allowed language documented |
| QSE-029 | Docs | Add data sources guide | P1 | Done | Sprint 6 | Sources, units, citations, licenses documented |
| QSE-030 | Docs | Add dashboard guide | P1 | Done | Sprint 6 | Reviewer can understand dashboard sections |
| QSE-031 | Release | Run minimum six-month Central Valley validation | P0 | Done | Sprint 6 | `outputs/central_valley_groundwater_release` exists with dashboard-ready artifacts |
| QSE-032 | Release | Complete release checklist and tag | P0 | In Progress | Sprint 7 | CI green, release notes written, tag created |
| QSE-033 | Data | Add DWR groundwater prep command | P0 | Done | Sprint 5 | Bulk ZIP, station/measurement CSVs, and canonical CSVs normalize to the groundwater schema |
| QSE-034 | Data | Run live DWR B118 Central Valley basin prep | P0 | Done | Sprint 4 | Local B118 GeoJSON and basin manifest exist with 35 Central Valley basin/subbasin features |
| QSE-035 | Data | Download official DWR groundwater station and measurement CSVs | P0 | Done | Sprint 5 | Official DWR files are downloaded locally under `data/central_valley/groundwater/raw/` and remain untracked |
| QSE-036 | Data | Normalize real DWR groundwater observations | P0 | Done | Sprint 5 | Canonical CSV has 221,192 rows, 17 months, 35 basins, preserved raw audit fields |
| QSE-037 | Data | Add chunked month-window filtering for DWR measurements | P0 | Done | Sprint 5 | Large DWR measurement CSV can be filtered by `--start-month` and `--end-month` without full-history loading |
| QSE-038 | Data Quality | Restrict DWR basin codes to supplied B118 basins | P0 | Done | Sprint 5 | Statewide DWR rows outside supplied Central Valley basins do not leak into release outputs |
| QSE-039 | Release | Confirm full target coverage in Central Valley bundle | P0 | Done | Sprint 6 | `coverage_summary.json` reports 6/6 for GRACE, USDM, GLDAS, TWS, basin, and groundwater |
| QSE-040 | Release | Run preferred twelve-month Central Valley validation | P0 | Ready | Sprint 7 | Twelve-month output exists, or release docs explicitly justify six-month scope |
| QSE-041 | Dashboard | Complete final visual dashboard review | P0 | Ready | Sprint 7 | First screen, basin map, groundwater time series, lag panel, coverage warnings, and claim boundary pass review |
| QSE-042 | Docs | Confirm claim consistency across release surfaces | P0 | Ready | Sprint 7 | README, dashboard, docs, and executive summary agree on workflow validation, groundwater begun, discovery not proven, quantum advantage not claimed |
| QSE-043 | Release | Update final release notes | P0 | Ready | Sprint 7 | Changelog/release notes summarize what is validated and explicitly not validated |
| QSE-044 | Release | Tag first release | P0 | Todo | Sprint 7 | Release tag is created only after CI, dashboard review, claim review, and checklist completion |

## Icebox

| ID | Item | Reason Deferred |
| --- | --- | --- |
| QSE-I01 | Hosted public dashboard deployment | Not needed for first scientific/reviewer release |
| QSE-I02 | Automated global monitoring | Too broad before basin/groundwater validation |
| QSE-I03 | Hardware-specific quantum sensor model | Needs domain inputs and evidence beyond current software scope |
| QSE-I04 | Commercial user management | Out of scope for research validation platform |
