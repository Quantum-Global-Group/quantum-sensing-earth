from src.data.generate_synthetic_gravity import generate_synthetic_gravity_field

def test_generate_synthetic_gravity_field_shapes():
    field, mask = generate_synthetic_gravity_field(grid_size=(32,32), seed=1)
    assert field.shape == (32,32)
    assert mask.shape == (32,32)
    assert mask.any()

def test_generate_synthetic_gravity_field_metadata():
    field, mask, anomalies = generate_synthetic_gravity_field(grid_size=(32,32), anomaly_count=2, seed=1, return_metadata=True)
    assert field.shape == (32,32)
    assert mask.any()
    assert len(anomalies) == 2
    assert {"center_x", "center_y", "sigma", "depth", "intensity"}.issubset(anomalies[0])
