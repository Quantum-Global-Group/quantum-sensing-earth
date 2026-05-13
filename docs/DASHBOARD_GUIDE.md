# Dashboard Guide

The Streamlit dashboard is the primary review surface for multimonth validation bundles.

## Launch

```bash
python -m pip install -e .[dashboard,geo]
python -m streamlit run src/dashboard/app.py -- --output outputs/grace_multimonth_usdm
```

## Required Core Artifacts

- `timeline_metrics.csv`
- `coverage_summary.json`
- `month_alignment.csv`
- `artifact_manifest.json`
- `executive_summary.md`

## Optional Evidence Tracks

- `gldas_hydrology_metrics.csv`
- `gldas_hydrology_summary.json`
- `tws_comparison_metrics.csv`
- `tws_comparison_summary.json`
- `basin_metrics.csv`
- `basin_summary.csv`
- `basin_summary.json`
- `groundwater_observations.csv`
- `groundwater_basin_monthly.csv`
- `groundwater_validation_metrics.csv`
- `groundwater_validation_summary.csv`
- `groundwater_summary.json`

## Reading Order

1. **Validation Status**: identifies the current readiness level and the boundary of the claim.
2. **Month Coverage**: checks whether GRACE, USDM, GLDAS, TWS, basin, and groundwater targets align by `YYYY-MM`.
3. **Evidence Trail**: explains how raw data becomes metrics.
4. **Study Region**: shows the coordinate-aware raster/mask footprint.
5. **Basin Validation**: aggregates GRACE, GLDAS, and USDM by named basins.
6. **Groundwater Validation**: appears when DWR/USGS well observations are present.
7. **Hydrology Target**: compares GRACE to GLDAS/TWS.
8. **Detection Results**: reviews detector quality and failure modes.
9. **Limits and Next Step**: states what can and cannot be concluded.

## Interactive Review Views

- Use the coverage heatmap to check whether target evidence is complete before reading performance metrics.
- Use the study-region raster map to inspect GRACE values, USDM mask overlay, CRS, bounds, and grid resolution.
- Use the study-region basin color control to switch the California map between GRACE, GLDAS, USDM, and groundwater values for the selected month.
- Hover over colored basins to see the current basin data point, including GRACE mean, GLDAS mean, USDM coverage, groundwater anomaly, observation count, and site count.
- Use the basin map color control in Basin Validation to switch between correlation, lagged correlation, trend agreement, drought coverage, or other basin-review metrics.
- Use the GRACE-vs-groundwater scatter plot to inspect whether selected basin months move together; bubble size shows observation count.
- Use the detector performance matrix to compare F1, IoU, false-positive rate, false-negative rate, and month count by sensor, detector, and drought threshold.
- Use the groundwater basin ranking chart instead of raw all-basin bars when comparing basin-level correlation, lagged correlation, trend agreement, or sign agreement.
- Use table sorting and sidebar filters to narrow evidence by threshold, detector, sensor profile, month, and basin.

## Reviewer Rules

- Treat missing month coverage as partial evidence.
- Treat `insufficient_months` groundwater rows as non-evidence for strong claims.
- Prefer basin-scale trends over single-month detector screenshots.
- Do not use USDM or GLDAS agreement as direct groundwater truth.
- Do not claim quantum advantage from this dashboard alone.
