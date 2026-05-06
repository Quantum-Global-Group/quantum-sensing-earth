from __future__ import annotations
import numpy as np

def _box_blur(grid, radius):
    if radius <= 0:
        return grid
    blurred = np.zeros_like(grid, dtype=float)
    count = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            blurred += np.roll(np.roll(grid, dy, axis=0), dx, axis=1)
            count += 1
    return blurred / count

def generate_synthetic_gravity_field(
    grid_size=(128, 128),
    anomaly_count=4,
    intensity_range=(-1.0, -0.2),
    sigma_range=(4.0, 12.0),
    seed=42,
    background_std=0.01,
    terrain_gradient=0.0,
    correlated_noise_radius=0,
    anomaly_depth_range=(1.0, 1.0),
    anomaly_size_scale=1.0,
    density_contrast_range=(-1.0, -1.0),
    sensor_altitude=1.0,
    return_metadata=False,
):
    """Generate a synthetic gravity anomaly field using procedural Gaussian field synthesis."""
    rng = np.random.default_rng(seed)
    h, w = grid_size
    margin = max(3, min(h, w) // 12)
    y, x = np.mgrid[0:h, 0:w]
    background = rng.normal(0.0, background_std, size=(h, w))
    if correlated_noise_radius:
        background = _box_blur(background, int(correlated_noise_radius))
    field = background
    if terrain_gradient:
        field += terrain_gradient * (x / max(1, w - 1) + y / max(1, h - 1))
    mask = np.zeros((h, w), dtype=bool)
    anomalies = []
    for index in range(anomaly_count):
        cx = rng.integers(margin, max(margin + 1, w - margin))
        cy = rng.integers(margin, max(margin + 1, h - margin))
        depth = rng.uniform(*anomaly_depth_range)
        density_contrast = rng.uniform(*density_contrast_range)
        effective_depth = depth + max(0.0, sensor_altitude)
        sigma = rng.uniform(*sigma_range) * anomaly_size_scale * np.sqrt(effective_depth)
        mass_scale = abs(density_contrast)
        intensity = rng.uniform(*intensity_range) * mass_scale / max(effective_depth ** 2, 1e-6)
        blob = intensity * np.exp(-(((x-cx)**2 + (y-cy)**2)/(2*sigma**2)))
        anomaly_mask = np.abs(blob) > abs(intensity) * 0.35
        field += blob
        mask |= anomaly_mask
        anomalies.append(
            {
                "id": f"anomaly_{index + 1}",
                "center_x": int(cx),
                "center_y": int(cy),
                "sigma": float(sigma),
                "depth": float(depth),
                "density_contrast": float(density_contrast),
                "sensor_altitude": float(sensor_altitude),
                "effective_depth": float(effective_depth),
                "intensity": float(intensity),
                "area_pixels": int(np.sum(anomaly_mask)),
            }
        )
    if return_metadata:
        return field, mask, anomalies
    return field, mask
