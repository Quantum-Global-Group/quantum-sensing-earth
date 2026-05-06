import numpy as np
from src.models.anomaly_detector import detect_z_score

def test_detect_z_score_returns_mask():
    grid=np.zeros((16,16)); grid[8,8]=10; mask=detect_z_score(grid, threshold=2.5)
    assert mask.shape == grid.shape
    assert mask[8,8]
