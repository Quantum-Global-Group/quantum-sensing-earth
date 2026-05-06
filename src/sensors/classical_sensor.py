from src.sensors.noise_models import apply_gaussian_sensor_noise

def measure_with_classical_profile(field, seed=42, noise_std=0.08, drift=0.02, bias=0.0, resolution_blur_radius=0, correlated_noise_radius=0):
    return apply_gaussian_sensor_noise(
        field,
        noise_std=noise_std,
        drift=drift,
        seed=seed,
        bias=bias,
        resolution_blur_radius=resolution_blur_radius,
        correlated_noise_radius=correlated_noise_radius,
    )
