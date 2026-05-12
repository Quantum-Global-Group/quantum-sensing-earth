# Changelog

## Unreleased

- Added artifact manifest generation for standard experiment outputs and multimonth validation bundles.
- Added normalized `YYYY-MM` month coverage artifacts: `coverage_summary.json` and `month_alignment.csv`.
- Added Central Valley study-region support to the GRACE/USDM runner.
- Added DWR Bulletin 118 basin preparation scaffold and download-free Central Valley fixtures.
- Added DWR Periodic Groundwater Level Measurements preparation command for bulk ZIP, station/measurement CSVs, and canonical CSVs.
- Added official DWR Periodic Groundwater Level Measurements discovery/download support through the CNRA CKAN API.
- Refined the Streamlit dashboard hierarchy, scientific chart styling, coverage timeline, unit-aware hydrology plots, and map color semantics.
- Added groundwater observation ingestion, basin assignment, monthly aggregation, and GRACE-groundwater metrics.
- Added Streamlit dashboard groundwater validation and coverage sections.
- Added final-run `executive_summary.md` export for multimonth validation bundles.
- Added tests for month normalization, artifact manifests, coverage summaries, groundwater schema handling, basin assignment, and insufficient-month guardrails.
