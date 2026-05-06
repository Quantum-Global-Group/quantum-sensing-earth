import numpy as np
from src.models.evaluation import (
    classification_metrics,
    localization_error,
    per_anomaly_metadata_metrics,
    per_anomaly_localization_error,
    rmse,
)

def test_classification_metrics():
    m = classification_metrics(np.array([True, True, False]), np.array([True, False, True]))
    assert "precision" in m and "recall" in m and "f1" in m
    assert m["tp"] == 1
    assert m["fp"] == 1
    assert m["fn"] == 1
    assert m["tn"] == 0
    assert m["iou"] == 1 / 3
    assert m["false_negative_rate"] == 0.5

def test_rmse_zero():
    x = np.array([1, 2, 3])
    assert rmse(x, x) == 0.0

def test_localization_error_none_without_prediction():
    true = np.zeros((4, 4), dtype=bool)
    pred = np.zeros((4, 4), dtype=bool)
    true[1, 1] = True
    assert localization_error(true, pred) is None

def test_per_anomaly_localization_error():
    true = np.zeros((6, 6), dtype=bool)
    pred = np.zeros((6, 6), dtype=bool)
    true[1, 1] = True
    true[4, 4] = True
    pred[1, 2] = True
    pred[5, 4] = True
    errors = per_anomaly_localization_error(true, pred)
    assert errors == [1.0, 1.0]

def test_per_anomaly_metadata_metrics_detects_nearby_prediction():
    pred = np.zeros((8, 8), dtype=bool)
    pred[2, 3] = True
    anomalies = [{"id": "a1", "center_x": 2, "center_y": 2, "sigma": 2.0, "depth": 1.0, "intensity": -0.5, "area_pixels": 4}]
    metrics = per_anomaly_metadata_metrics(anomalies, pred)
    assert metrics[0]["detected"]
    assert metrics[0]["localization_error"] == 1.0
