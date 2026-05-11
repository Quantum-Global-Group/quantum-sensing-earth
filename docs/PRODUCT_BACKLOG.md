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
| QSE-001 | Project Control | Link finish-line docs from README | P1 | Todo | Sprint 1 | README links to project explainer, finish plan, sprint plan |
| QSE-002 | Project Control | Add changelog | P1 | Todo | Sprint 1 | `CHANGELOG.md` exists with initial unreleased section |
| QSE-003 | Reporting | Generate `artifact_manifest.json` | P0 | Todo | Sprint 1 | Every standard run lists key artifacts and paths |
| QSE-004 | Reporting | Add artifact manifest test | P0 | Todo | Sprint 1 | Test confirms manifest exists after CLI run |
| QSE-005 | Data Credibility | Normalize month keys across targets | P0 | Todo | Sprint 2 | GRACE, USDM, GLDAS, TWS use common month keys |
| QSE-006 | Data Credibility | Export `coverage_summary.json` | P0 | Todo | Sprint 2 | Summary lists available and missing months by target |
| QSE-007 | Data Credibility | Export `month_alignment.csv` | P0 | Todo | Sprint 2 | CSV has one row per month with target availability flags |
| QSE-008 | Dashboard | Add coverage timeline | P0 | Todo | Sprint 2 | Dashboard shows target availability over time |
| QSE-009 | Dashboard | Add month-alignment table | P0 | Todo | Sprint 2 | Dashboard table lists missing months and target status |
| QSE-010 | Tests | Add month-alignment tests | P0 | Todo | Sprint 2 | Missing/extra/inconsistent month tests pass |
| QSE-011 | Hydrology | Add GLDAS/TWS doctor command | P0 | Todo | Sprint 3 | Doctor validates files, variables, units, and month metadata |
| QSE-012 | Hydrology | Add generated NetCDF fixture tests | P1 | Todo | Sprint 3 | CI tests NetCDF read and bad variable handling |
| QSE-013 | Hydrology | Record resampling method metadata | P0 | Todo | Sprint 3 | Metadata and dashboard show resampling method |
| QSE-014 | Docs | Update GLDAS/TWS manual workflow | P1 | Todo | Sprint 3 | README or data-source docs include exact steps |
| QSE-015 | Basin | Select authoritative basin boundary source | P0 | Todo | Sprint 4 | Decision documented with citation and license |
| QSE-016 | Basin | Add basin conversion/rasterization workflow | P0 | Todo | Sprint 4 | Boundaries align to GRACE grid |
| QSE-017 | Basin | Add basin rasterization tests | P0 | Todo | Sprint 4 | Generated or fixture polygons rasterize correctly |
| QSE-018 | Dashboard | Add basin map and labels | P0 | Todo | Sprint 4 | Dashboard displays named basin boundaries |
| QSE-019 | Dashboard | Add basin time-series panel | P1 | Todo | Sprint 4 | GRACE/GLDAS/USDM shown by basin/month |
| QSE-020 | Science | Select groundwater/storage validation target | P0 | Todo | Sprint 5 | Target source and claim rationale documented |
| QSE-021 | Data | Define observation CSV schema | P0 | Todo | Sprint 5 | Schema supports basin, month, value, units, source, uncertainty |
| QSE-022 | Data | Add groundwater/storage observation loader | P0 | Todo | Sprint 5 | Loader reads observations and validates schema |
| QSE-023 | Science | Add basin/month observation metrics | P0 | Todo | Sprint 5 | Correlation, lagged correlation, trend, sign agreement exported |
| QSE-024 | Dashboard | Add groundwater/storage panel | P0 | Todo | Sprint 5 | Dashboard separates groundwater/storage from drought proxy |
| QSE-025 | Dashboard | Redesign final dashboard hierarchy | P0 | Todo | Sprint 6 | First screen explains status, claim boundary, and evidence |
| QSE-026 | Reporting | Add executive summary export | P1 | Todo | Sprint 6 | Markdown or HTML summary generated from run artifacts |
| QSE-027 | Reporting | Add report bundle manifest | P1 | Todo | Sprint 6 | Final bundle lists artifacts, checksums, command replay |
| QSE-028 | Docs | Add scientific claims guide | P0 | Todo | Sprint 6 | Claim levels and allowed language documented |
| QSE-029 | Docs | Add data sources guide | P1 | Todo | Sprint 6 | Sources, units, citations, licenses documented |
| QSE-030 | Docs | Add dashboard guide | P1 | Todo | Sprint 6 | Reviewer can understand dashboard sections |
| QSE-031 | Release | Run final 6-12 month validation | P0 | Todo | Sprint 6 | Final output folder exists with dashboard-ready artifacts |
| QSE-032 | Release | Complete release checklist and tag | P0 | Todo | Sprint 6 | CI green, release notes written, tag created |

## Icebox

| ID | Item | Reason Deferred |
| --- | --- | --- |
| QSE-I01 | Hosted public dashboard deployment | Not needed for first scientific/reviewer release |
| QSE-I02 | Automated global monitoring | Too broad before basin/groundwater validation |
| QSE-I03 | Hardware-specific quantum sensor model | Needs domain inputs and evidence beyond current software scope |
| QSE-I04 | Commercial user management | Out of scope for research validation platform |

