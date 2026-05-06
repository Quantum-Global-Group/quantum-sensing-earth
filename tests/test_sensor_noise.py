import numpy as np
from src.sensors.noise_models import apply_gaussian_sensor_noise

def test_apply_gaussian_sensor_noise_shape():
    grid = np.zeros((16, 16))
    measured = apply_gaussian_sensor_noise(grid, noise_std=0.1, seed=1)
    assert measured.shape == grid.shape

def test_apply_gaussian_sensor_noise_drift_increases_down_track():
    grid = np.zeros((16, 16))
    measured = apply_gaussian_sensor_noise(grid, noise_std=0.0, drift=0.2, seed=1)
    assert measured[-1, 0] > measured[0, 0]
