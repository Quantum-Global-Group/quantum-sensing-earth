# Contributing

Thanks for helping improve Quantum Sensing Earth. The project is research software, so contributions should keep scientific claims narrower than the evidence.

## Development Setup

```bash
python -m pip install -e .[dev,dashboard]
python -m pytest -q
```

Install geospatial extras when working on GeoTIFF, NetCDF, shapefile, or raster-alignment features:

```bash
python -m pip install -e .[dev,dashboard,geo]
```

## Pull Request Checklist

- Keep generated `data/` and `outputs/` artifacts out of git.
- Add or update tests for CLI, metric, dashboard-import, or data-loader changes.
- Document any new data source with units, CRS/resolution, date range, citation, preprocessing, and mask provenance.
- Label weak-label or proxy datasets clearly. Do not imply groundwater truth from USDM or GLDAS alone.
- Run `python -m pytest -q` before opening a PR.

## Scientific Claim Boundary

Acceptable: "This workflow compares GRACE/GRACE-FO water-mass rasters against drought and hydrology targets."

Not acceptable without stronger evidence: "This proves quantum groundwater detection."
