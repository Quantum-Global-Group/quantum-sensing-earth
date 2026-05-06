import numpy as np

def standardize_grid(grid):
    std=float(np.std(grid))
    return grid-float(np.mean(grid)) if std==0 else (grid-float(np.mean(grid)))/std

def preprocess_grid(grid, missing="median", detrend=False, normalize=None, clip=None):
    processed = np.array(grid, dtype=float, copy=True)
    steps = []

    if missing not in {"none", "zero", "median", "mean"}:
        raise ValueError("missing must be one of: none, zero, median, mean")
    missing_mask = ~np.isfinite(processed)
    if missing_mask.any() and missing != "none":
        finite = processed[np.isfinite(processed)]
        if missing == "zero" or finite.size == 0:
            fill_value = 0.0
        elif missing == "mean":
            fill_value = float(np.mean(finite))
        else:
            fill_value = float(np.median(finite))
        processed[missing_mask] = fill_value
        steps.append({"operation": "fill_missing", "method": missing, "value": fill_value})

    if detrend:
        y, x = np.mgrid[0:processed.shape[0], 0:processed.shape[1]]
        design = np.column_stack([x.ravel(), y.ravel(), np.ones(processed.size)])
        coefficients, *_ = np.linalg.lstsq(design, processed.ravel(), rcond=None)
        trend = (design @ coefficients).reshape(processed.shape)
        processed = processed - trend
        steps.append({"operation": "detrend_plane", "coefficients": [float(value) for value in coefficients]})

    if clip is not None:
        low, high = clip
        processed = np.clip(processed, low, high)
        steps.append({"operation": "clip", "low": float(low), "high": float(high)})

    if normalize in {"zscore", "standardize"}:
        mean = float(np.mean(processed))
        std = float(np.std(processed)) or 1.0
        processed = (processed - mean) / std
        steps.append({"operation": "normalize", "method": "zscore", "mean": mean, "std": std})
    elif normalize == "minmax":
        min_value = float(np.min(processed))
        max_value = float(np.max(processed))
        span = max_value - min_value or 1.0
        processed = (processed - min_value) / span
        steps.append({"operation": "normalize", "method": "minmax", "min": min_value, "max": max_value})
    elif normalize not in {None, "none"}:
        raise ValueError("normalize must be one of: none, zscore, standardize, minmax")

    return processed, steps
