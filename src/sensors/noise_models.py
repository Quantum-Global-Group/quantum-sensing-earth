import numpy as np

def box_blur(grid, radius):
    if radius <= 0:
        return grid
    blurred = np.zeros_like(grid, dtype=float)
    count = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            blurred += np.roll(np.roll(grid, dy, axis=0), dx, axis=1)
            count += 1
    return blurred / count

def apply_gaussian_sensor_noise(
    field,
    noise_std,
    drift=0.0,
    seed=42,
    bias=0.0,
    resolution_blur_radius=0,
    correlated_noise_radius=0,
):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, 1.0, field.shape[0], dtype=float)[:, None]
    drift_plane = drift * y
    random_noise = rng.normal(0.0, noise_std, size=field.shape)
    random_noise = box_blur(random_noise, int(correlated_noise_radius))
    measured = field + random_noise + drift_plane + bias
    return box_blur(measured, int(resolution_blur_radius))
