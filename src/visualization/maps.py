from pathlib import Path
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

def save_grid_image(grid, path, title):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(); plt.imshow(grid); plt.title(title); plt.colorbar(); plt.tight_layout(); plt.savefig(path); plt.close()

def save_mask_overlay(grid, true_mask, pred_mask, path, title):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    true_only = true_mask.astype(bool) & ~pred_mask.astype(bool)
    pred_only = pred_mask.astype(bool) & ~true_mask.astype(bool)
    overlap = true_mask.astype(bool) & pred_mask.astype(bool)

    overlay = np.zeros((*grid.shape, 4), dtype=float)
    overlay[true_only] = [0.1, 0.4, 1.0, 0.55]
    overlay[pred_only] = [1.0, 0.2, 0.1, 0.55]
    overlay[overlap] = [0.1, 0.8, 0.25, 0.65]

    plt.figure(figsize=(7, 6))
    plt.imshow(grid, cmap="viridis")
    plt.imshow(overlay)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def save_region_split_map(train_region, evaluation_region, path, title):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.zeros((*train_region.shape, 3), dtype=float)
    image[train_region.astype(bool)] = [0.18, 0.43, 0.72]
    image[evaluation_region.astype(bool)] = [0.25, 0.62, 0.34]
    image[train_region.astype(bool) & evaluation_region.astype(bool)] = [0.45, 0.45, 0.45]

    plt.figure(figsize=(7, 5))
    plt.imshow(image)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def save_detection_quality_comparison(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    aggregate = {}
    for row in rows:
        key = (row["sensor_profile"], row.get("variant", row["algorithm"]))
        aggregate.setdefault(key, []).append(row["f1"])

    labels = [f"{sensor}\n{algorithm}" for sensor, algorithm in aggregate]
    values = [float(np.mean(scores)) for scores in aggregate.values()]
    colors = ["#4c78a8" if "classical" in label else "#54a24b" for label in labels]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, values, color=colors)
    plt.ylabel("Mean F1 across seeds")
    plt.ylim(0, 1)
    plt.title("Classical vs Quantum Detection Quality")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def save_uncertainty_plot(summary, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = ["f1", "iou", "rmse", "snr"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    labels = [f"{row['sensor_profile']}\n{row['variant']}" for row in summary]
    x = np.arange(len(summary))

    for axis, metric in zip(axes.ravel(), metrics):
        means = np.array([row.get(metric) or 0.0 for row in summary], dtype=float)
        lows = np.array([row.get(f"{metric}_ci95_low") if row.get(f"{metric}_ci95_low") is not None else row.get(metric) or 0.0 for row in summary], dtype=float)
        highs = np.array([row.get(f"{metric}_ci95_high") if row.get(f"{metric}_ci95_high") is not None else row.get(metric) or 0.0 for row in summary], dtype=float)
        yerr = np.vstack([means - lows, highs - means])
        axis.errorbar(x, means, yerr=yerr, fmt="o", capsize=4, color="#2f6f95")
        axis.set_title(metric.upper())
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
        if metric in {"f1", "iou"}:
            axis.set_ylim(0, 1)

    fig.suptitle("Metric Uncertainty Across Detector Variants")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
