# Project Management Plan

## Project Name

Quantum Sensing Earth

## Project Objective

Deliver a reproducible GRACE/GRACE-FO hydrology validation platform that compares gravity-derived water-mass signals, classical and quantum-sensing-inspired sensor profiles, and multiple anomaly detectors against independent drought, hydrology, basin-storage, or groundwater-observation targets.

## Final Outcome

The project is complete when an outside reviewer can:

- clone and install the repository;
- run a download-free demo;
- run or inspect a documented real-data validation workflow;
- open the dashboard and understand what was validated;
- trace every conclusion to artifacts and provenance;
- see clear warnings for missing months, weak labels, and unsupported claims;
- evaluate basin-scale and groundwater/storage validation evidence;
- agree that the stated claim level is supported by the data.

## Current Project Phase

Current phase: late MVP / early validation platform.

The software foundation is strong. The remaining work is mostly about scientific credibility, evidence quality, dashboard storytelling, and release maturity.

## Claim-Level Roadmap

| Claim Level | Claim | Status | Required To Complete |
| --- | --- | --- | --- |
| 1 | Reproducible software workflow | Reached | Keep CI green and docs aligned |
| 2 | Real GRACE/GRACE-FO raster validation | Mostly reached | Harden import tests and provenance |
| 3 | Independent drought-proxy validation | Reached | Improve month coverage and dashboard clarity |
| 4 | External hydrology validation | Partial | Complete GLDAS/TWS alignment and coverage reporting |
| 5 | Basin/groundwater validation | Not reached | Add authoritative basins and groundwater/storage target |
| 6 | Quantum-inspired advantage | Not reached | Add repeated sensor-profile uncertainty analysis |

## Delivery Strategy

Use six two-week sprints. Each sprint ends with a working artifact, not just analysis.

Sprint themes:

1. Project control and data credibility
2. Hydrology coverage and GLDAS/TWS hardening
3. Authoritative basin validation
4. Groundwater/storage target workflow
5. Reviewer-grade dashboard and report polish
6. Release candidate, evidence audit, and final claim gate

## Milestones

| Milestone | Target Sprint | Exit Criteria |
| --- | --- | --- |
| M1: Project control baseline | Sprint 1 | Backlog, milestones, risk register, artifact contract, docs linked |
| M2: Hydrology coverage trustworthy | Sprint 2 | Month alignment, GLDAS/TWS doctor, coverage timeline, tests |
| M3: Basin validation credible | Sprint 3 | Authoritative basin source, basin metrics, basin dashboard panel |
| M4: Groundwater/storage target present | Sprint 4 | Observation schema, loader, example target, basin/month metrics |
| M5: Dashboard reviewer-ready | Sprint 5 | Storytelling redesign, executive summary, report bundle manifest |
| M6: Finished-release candidate | Sprint 6 | CI green, final run complete, docs aligned, release checklist passed |

## Workstreams

| Workstream | Purpose | Main Outputs |
| --- | --- | --- |
| Data Engineering | Ingest and align GRACE, USDM, GLDAS/TWS, basins, and observations | loaders, doctors, metadata, tests |
| Scientific Validation | Define defensible metrics and claim boundaries | evaluation methods, readiness levels, caveats |
| Dashboard/Product | Make evidence understandable to reviewers | Streamlit sections, charts, executive summary |
| DevOps/Release | Make project installable, testable, and releasable | CI, release checklist, changelog, tags |
| Documentation | Make the project explainable | README, data sources, dashboard guide, claims guide |

## Project Roles

| Role | Responsibility |
| --- | --- |
| Project Owner | Defines final claim level and release priorities |
| Scientific Lead | Approves validation targets, metrics, and caveats |
| Data Engineer | Builds loaders, alignment, rasterization, and provenance |
| ML/Detection Engineer | Maintains detectors, calibration, and sensor-profile comparisons |
| Dashboard Engineer | Builds reviewer-facing Streamlit and report UX |
| QA/Release Engineer | Owns CI, smoke tests, release checklist, and artifact verification |

## RACI Matrix

| Deliverable | Project Owner | Scientific Lead | Data Engineer | ML Engineer | Dashboard Engineer | QA/Release |
| --- | --- | --- | --- | --- | --- | --- |
| Final claim level | A | R | C | C | C | C |
| Data source selection | C | A/R | R | C | C | C |
| Manifest schema | C | A | R | C | C | C |
| GRACE/USDM alignment | C | C | A/R | C | C | C |
| GLDAS/TWS validation | C | A | R | C | C | C |
| Basin validation | C | A | R | C | C | C |
| Groundwater target workflow | C | A/R | R | C | C | C |
| Detector calibration | C | C | C | A/R | C | C |
| Dashboard story | A | C | C | C | R | C |
| CI and release | C | C | C | C | C | A/R |

Legend: R = Responsible, A = Accountable, C = Consulted.

## Decision Log Needed

Create or update decisions for:

- final claim level for first finished release;
- authoritative basin boundary source;
- first groundwater or basin-storage target;
- supported data-source versions;
- minimum month count for final validation;
- dashboard audience and tone;
- release artifact format.

## Success Metrics

### Product Metrics

- Demo runs from a clean install.
- Dashboard opens without missing-main-path images.
- First screen explains validation status without scrolling.
- Every output folder includes metadata and artifact manifest.
- Docs explain supported and unsupported claims.

### Scientific Metrics

- At least 6-12 months of GRACE-FO validation.
- Complete or explicitly partial USDM, GLDAS, and TWS coverage.
- At least one authoritative basin boundary set.
- At least one groundwater or basin-storage observation target.
- Basin-level metrics exported and visualized.
- Detector and sensor-profile comparisons include uncertainty or repeated evidence.

### Engineering Metrics

- GitHub Actions pass.
- Test suite includes data-loader, manifest, dashboard, demo, and metric coverage.
- No secrets or generated data committed.
- CLI exits correctly.
- All release commands are documented.

## Project Cadence

Suggested cadence:

- Sprint length: 2 weeks.
- Planning: first day of sprint.
- Mid-sprint evidence review: day 5 or 6.
- Demo and retrospective: final day.
- Release gate review: end of Sprint 6.

## Reporting Template

Weekly PM status should include:

- Overall status: green, yellow, or red.
- What shipped this week.
- Evidence produced.
- Current blockers.
- Scientific claim level currently supported.
- CI/release health.
- Risks that changed.
- Next-week priorities.

## Scope Control

In scope:

- reproducible data workflows;
- detector comparison;
- hydrology and basin validation;
- dashboard/report evidence;
- documentation and release readiness.

Out of scope for the first finished release:

- physical quantum hardware validation;
- operational groundwater discovery product;
- automated global production monitoring;
- commercial SaaS deployment;
- field deployment claims.

## Final Release Gate

The project cannot be called finished until this gate passes:

- tests pass locally;
- GitHub Actions pass;
- download-free demo succeeds;
- final GRACE-FO validation run exists;
- dashboard opens on final run;
- manifest doctor passes or warnings are explained;
- hydrology coverage is complete or explicitly partial;
- authoritative basin boundaries are used or limitations are explicit;
- groundwater/storage target is present for groundwater claims;
- final docs, dashboard, and report state the same claim level.

