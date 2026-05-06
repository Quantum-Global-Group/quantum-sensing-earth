# Real Gravity Data Import

The MVP accepts validation grids through `--validation-grid` and optional anomaly masks through `--validation-mask`.

## Supported Formats

- Rectangular `.csv`: one row per grid row, one gravity value per column.
- Long-form `.csv`: columns named `x`, `y`, and `gravity`; the loader pivots these into a grid.
- `.npy`: a NumPy array saved with `numpy.save`.
- `.tif` / `.tiff`: optional GeoTIFF support when `rasterio` is installed.

The optional mask must have the same shape as the gravity grid. Nonzero values are treated as anomaly pixels.

## GeoTIFF and Raster Data

GeoTIFF loading is optional so the baseline MVP stays lightweight.

Install optional raster dependencies:

```bash
python -m pip install -e .[geo]
```

Then run:

```bash
python -m src.main --validation-grid gravity_anomaly.tif --validation-mask anomaly_mask.tif --validation-manifest validation_manifest.yaml --output outputs/real_validation
```

When loaded through `rasterio`, the report metadata preserves CRS, bounds, transform, pixel resolution, nodata, and shape.

You can also convert rasters to `.npy` or `.csv` before running the MVP.

Example conversion with `rasterio` in a separate environment:

```python
import numpy as np
import rasterio

with rasterio.open("gravity_anomaly.tif") as src:
    grid = src.read(1)

np.save("gravity_anomaly.npy", grid)
```

Then run:

```bash
python -m src.main --validation-grid gravity_anomaly.npy --validation-mask anomaly_mask.npy --output outputs/real_validation
```

## Ground Truth Masks

For real validation, mask quality matters more than file format. Document how each mask was created, including:

- Groundwater or mass-change reference source
- Thresholding method
- Spatial resolution
- Any reprojection or resampling
- Time window relative to the gravity observation

## Concrete Public Dataset Recipe: GRACE Tellus

A practical first public validation target is NASA/JPL GRACE Tellus monthly mass grids:

- Source: GRACE Tellus Monthly Mass Grids and JPL Global Mascons.
- Official overview: https://grace.jpl.nasa.gov/data/monthly-mass-grids/
- JPL mascon data portal: https://grace.jpl.nasa.gov/data/get-data/jpl_global_mascons/
- NASA Open Data citation example: https://data.nasa.gov/dataset/jpl-tellus-grace-level-3-monthly-land-water-equivalent-thickness-surface-mass-anomaly-rele

Why this dataset fits the MVP:

- It is gravity-derived surface mass anomaly data.
- JPL documents units as centimeters of equivalent water thickness for data and error grids.
- JPL documents 0.5 degree global grids for the mascon product.
- NASA Open Data lists GeoTIFF among the available formats for the Level-3 monthly land water-equivalent-thickness product.

Suggested workflow:

1. Download one monthly GeoTIFF or netCDF grid for a region and month of interest from GRACE Tellus.
2. If needed, convert netCDF to GeoTIFF with GDAL or rasterio, preserving CRS and transform.
3. Crop to a regional bounding box so detector runs remain fast.
4. Save the gravity/mass anomaly raster as `validation_grid.tif`.
5. Create `validation_manifest.yaml` with source URL, product version, month/date range, units, preprocessing, citation, and limitations.
6. Build a conservative `validation_mask.tif` from an independently justified threshold or external hydrogeology reference. Do not treat the GRACE anomaly itself as ground truth without documenting that circularity.
7. Run:

```bash
python -m src.main --validation-grid validation_grid.tif --validation-mask validation_mask.tif --validation-manifest validation_manifest.yaml --detectors z_score dbscan isolation_forest --calibrate-thresholds --spatial-folds 4 --output outputs/grace_validation
```

Mask strategy options:

- Threshold negative equivalent-water-thickness anomalies only as a weak label, and document it as heuristic.
- Use independent drought, groundwater, or basin-boundary data to constrain the mask.
- Compare multiple masks and cite the provenance of each.

Citation format:

```yaml
dataset:
  name: JPL Tellus GRACE/GRACE-FO Monthly Mass Grid subset
  source: https://grace.jpl.nasa.gov/data/get-data/jpl_global_mascons/
  date_range: YYYY-MM
  units: centimeters equivalent water thickness
  citation: "Felix Landerer, PO.DAAC, JPL TELLUS GRACE Level-3 Monthly Land Water-Equivalent-Thickness Surface Mass Anomaly Release 6.0 version 04, https://grace.jpl.nasa.gov/data/get-data/monthly-mass-grids-land/"
mask:
  method: Describe threshold or independent source here.
  provenance: Describe who/what generated the mask and why it is valid.
limitations:
  - GRACE products are coarse and represent broad mass changes, not small local targets.
  - Equivalent water thickness is not identical to local gravity anomaly in mGal.
  - A threshold-derived mask is a weak label unless supported by independent evidence.
```

See `examples/grace_tellus/` for a runnable scaffold:

- `README.md` describes the manual workflow.
- `validation_manifest.template.yaml` captures required provenance.
- `convert_grace_input.py` copies GeoTIFFs or converts netCDF inputs when optional dependencies are installed.
- `make_weak_label_mask.py` creates threshold masks with explicit weak-label warnings.
