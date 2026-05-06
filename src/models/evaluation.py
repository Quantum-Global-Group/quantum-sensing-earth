import numpy as np

def classification_metrics(y_true, y_pred):
    yt = y_true.astype(bool).ravel()
    yp = y_pred.astype(bool).ravel()
    tp = int(np.sum(yt & yp))
    fp = int(np.sum(~yt & yp))
    fn = int(np.sum(yt & ~yp))
    tn = int(np.sum(~yt & ~yp))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    union = tp + fp + fn
    iou = tp / union if union else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) else 0.0
    false_negative_rate = fn / (fn + tp) if (fn + tp) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": iou,
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }

def rmse(reference, observed, region=None):
    if region is not None:
        reference = reference[region]
        observed = observed[region]
    return float(np.sqrt(np.mean((reference - observed) ** 2)))

def snr(reference, observed, region=None):
    if region is not None:
        reference = reference[region]
        observed = observed[region]
    signal_power = float(np.mean(reference ** 2))
    noise_power = float(np.mean((reference - observed) ** 2))
    return float("inf") if noise_power == 0 else signal_power / noise_power

def localization_error(true_mask, pred_mask):
    true_points = np.argwhere(true_mask.astype(bool))
    pred_points = np.argwhere(pred_mask.astype(bool))
    if len(true_points) == 0 or len(pred_points) == 0:
        return None
    true_center = true_points.mean(axis=0)
    pred_center = pred_points.mean(axis=0)
    return float(np.linalg.norm(true_center - pred_center))

def connected_components(mask):
    mask = mask.astype(bool)
    visited = np.zeros_like(mask, dtype=bool)
    components = []
    height, width = mask.shape
    for row in range(height):
        for col in range(width):
            if not mask[row, col] or visited[row, col]:
                continue
            stack = [(row, col)]
            visited[row, col] = True
            points = []
            while stack:
                y, x = stack.pop()
                points.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            components.append(np.array(points, dtype=float))
    return components

def per_anomaly_localization_error(true_mask, pred_mask):
    true_components = connected_components(true_mask)
    pred_components = connected_components(pred_mask)
    if not true_components:
        return []
    if not pred_components:
        return [None for _ in true_components]

    pred_centroids = np.array([component.mean(axis=0) for component in pred_components])
    errors = []
    for component in true_components:
        true_centroid = component.mean(axis=0)
        distances = np.linalg.norm(pred_centroids - true_centroid, axis=1)
        errors.append(float(np.min(distances)))
    return errors

def per_anomaly_metadata_metrics(anomalies, pred_mask, evaluation_region=None):
    if not anomalies:
        return []
    if evaluation_region is not None:
        anomalies = [
            anomaly
            for anomaly in anomalies
            if evaluation_region[int(anomaly["center_y"]), int(anomaly["center_x"])]
        ]
        if not anomalies:
            return []
    pred_components = connected_components(pred_mask)
    if not pred_components:
        return [
            {
                "id": anomaly["id"],
                "center_x": anomaly["center_x"],
                "center_y": anomaly["center_y"],
                "detected": False,
                "localization_error": None,
            }
            for anomaly in anomalies
        ]

    pred_centroids = np.array([component.mean(axis=0) for component in pred_components])
    metrics = []
    for anomaly in anomalies:
        center_yx = np.array([anomaly["center_y"], anomaly["center_x"]], dtype=float)
        distances = np.linalg.norm(pred_centroids - center_yx, axis=1)
        nearest = float(np.min(distances))
        metrics.append(
            {
                "id": anomaly["id"],
                "center_x": anomaly["center_x"],
                "center_y": anomaly["center_y"],
                "sigma": anomaly["sigma"],
                "depth": anomaly["depth"],
                "intensity": anomaly["intensity"],
                "area_pixels": anomaly["area_pixels"],
                "detected": nearest <= max(1.0, anomaly["sigma"]),
                "localization_error": nearest,
            }
        )
    return metrics

def evaluate(reference, true_mask, observed, pred_mask, anomalies=None, evaluation_region=None):
    if evaluation_region is not None:
        evaluation_region = evaluation_region.astype(bool)
        metric_true_mask = true_mask.astype(bool) & evaluation_region
        metric_pred_mask = pred_mask.astype(bool) & evaluation_region
        out = classification_metrics(true_mask[evaluation_region], pred_mask[evaluation_region])
    else:
        metric_true_mask = true_mask
        metric_pred_mask = pred_mask
        out = classification_metrics(true_mask, pred_mask)
    out["rmse"] = rmse(reference, observed, region=evaluation_region)
    out["snr"] = snr(reference, observed, region=evaluation_region)
    out["localization_error"] = localization_error(metric_true_mask, metric_pred_mask)
    anomaly_errors = per_anomaly_localization_error(metric_true_mask, metric_pred_mask)
    numeric_errors = [value for value in anomaly_errors if value is not None]
    out["per_anomaly_localization_error"] = anomaly_errors
    out["mean_per_anomaly_localization_error"] = (
        float(np.mean(numeric_errors)) if numeric_errors else None
    )
    if anomalies is not None:
        object_metrics = per_anomaly_metadata_metrics(anomalies, metric_pred_mask, evaluation_region=evaluation_region)
        detected_count = sum(1 for item in object_metrics if item["detected"])
        out["anomaly_objects"] = object_metrics
        out["anomaly_object_recall"] = detected_count / len(object_metrics) if object_metrics else 0.0
    return out
