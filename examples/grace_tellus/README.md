# GRACE Tellus Validation Example

This folder is a manual, documented starting point for running the MVP on public GRACE Tellus gravity-derived mass anomaly products.

## Data Source

Recommended first source:

- GRACE Tellus Monthly Mass Grids: https://grace.jpl.nasa.gov/data/monthly-mass-grids/
- GRACE Tellus Land grids: https://grace.jpl.nasa.gov/data/get-data/monthly-mass-grids-land/
- JPL Global Mascons: https://grace.jpl.nasa.gov/data/get-data/jpl_global_mascons/

GRACE Tellus land products are monthly surface mass anomalies derived from GRACE/GRACE-FO time-variable gravity observations. JPL documents the data and error grid units as centimeters of equivalent water thickness, with GeoTIFF and netCDF options available for Level-3 products.

## Files In This Example

- `validation_manifest.template.yaml`: provenance template to copy for a real GRACE run.
- `convert_grace_input.py`: conversion skeleton for GeoTIFF or netCDF inputs.
- `make_weak_label_mask.py`: creates a threshold mask with prominent weak-label warnings.
- `rasterize_independent_mask.py`: crops a GRACE GeoTIFF and rasterizes an independent shapefile attribute onto the GRACE grid.

## Manual Workflow

1. Download a monthly GRACE Tellus land GeoTIFF or netCDF file.
2. Copy `validation_manifest.template.yaml` to your run folder and fill in product, month, URL, units, citation, preprocessing, and limitations.
3. Convert or crop the input:

```bash
python examples/grace_tellus/convert_grace_input.py --input path/to/grace_input.tif --output validation_grid.tif
```

4. Create a weak-label mask only if you do not have an independent mask:

```bash
python examples/grace_tellus/make_weak_label_mask.py --input validation_grid.tif --output validation_mask.tif --threshold -5 --mode below
```

5. Run the MVP with spatial held-out calibration:

```bash
python -m src.main --validation-grid validation_grid.tif --validation-mask validation_mask.tif --validation-manifest validation_manifest.yaml --detectors z_score dbscan isolation_forest --calibrate-thresholds --spatial-folds 4 --output outputs/grace_tellus_validation
```

## Independent Drought Mask Workflow

For a stronger workflow test, use an external drought or basin mask instead of a threshold from the GRACE raster. For example, U.S. Drought Monitor (USDM) weekly shapefiles can be rasterized to the 1-degree GRACE grid:

```bash
python examples/grace_tellus/rasterize_independent_mask.py \
  --grid data/grace_tellus/raw/GRD-3_2002095-2002120_GRAC_UTCSR_BA01_0600_LND_v04.tif \
  --vector data/usdm/raw/USDM_20020430_M/USDM_20020430.shp \
  --bbox -125 31 -102 49 \
  --attribute DM \
  --min-value 2 \
  --all-touched \
  --output-grid data/grace_tellus/western_us_grace_200204.tif \
  --output-mask data/grace_tellus/western_us_usdm_d2plus_20020430_mask.tif
```

This example crops to the western conterminous U.S. and labels USDM D2-D4 drought areas as the independent mask. The mask is independent of the GRACE raster, but it is still a hydrologic drought proxy rather than direct groundwater truth; record that distinction in the manifest.

## GLDAS Hydrology Track

The multi-month dashboard can also compare GRACE CSR terrestrial-water-storage anomalies against the external GLDAS-NOAH 3.3 TWS anomaly product:

- Product: https://podaac.jpl.nasa.gov/dataset/TELLUS_GLDAS-NOAH-3.3_TWS-ANOMALY_MONTHLY
- Target type: `terrestrial_water_storage`
- Resampling: GLDAS 1-degree monthly TWS anomaly is cropped/aligned to the same western U.S. 1-degree GRACE grid.
- Metrics: pixel correlation, RMSE, bias, basin-mean trend agreement, and anomaly sign agreement.

GLDAS NetCDF granules are Earthdata-authenticated. The runner supports either `~/.netrc` or environment variables.

`.netrc` example:

```text
machine urs.earthdata.nasa.gov
  login YOUR_EARTHDATA_USERNAME
  password YOUR_EARTHDATA_PASSWORD
```

Environment variable example:

```bash
export EARTHDATA_USERNAME=YOUR_EARTHDATA_USERNAME
export EARTHDATA_PASSWORD=YOUR_EARTHDATA_PASSWORD
```

Windows PowerShell:

```powershell
$env:EARTHDATA_USERNAME="YOUR_EARTHDATA_USERNAME"
$env:EARTHDATA_PASSWORD="YOUR_EARTHDATA_PASSWORD"
```

Then rerun the dashboard workflow:

```bash
python examples/grace_tellus/run_multimonth_usdm.py --months 3 --thresholds 1 2 3 --spatial-folds 4 --output outputs/grace_multimonth_usdm --skip-existing
```

If automatic download still fails, manually download the `.nc` files listed in `outputs/grace_multimonth_usdm/gldas_hydrology_metrics.csv` and place them in `data/gldas/raw/`, preserving filenames. Rerun the same command. The GLDAS doctor writes `outputs/grace_multimonth_usdm/gldas_doctor.json` and must show readable NetCDF files with a TWS-like numeric variable before hydrology metrics are promoted in the readiness ladder.

## Mask Warning

A threshold mask created from the same GRACE raster is a weak label. It is useful for checking software mechanics, but it is not independent evidence of groundwater anomalies. For scientific validation, prefer masks from independent basin boundaries, drought records, groundwater observations, hydrology products, or expert-labeled regions, and document their provenance in the manifest.

## Citation Note

Use the exact product citation from JPL, PO.DAAC, or NASA Open Data for the file you download. The manifest template includes a placeholder citation line that must be replaced before treating a run as a real-data validation.
