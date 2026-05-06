from src.models.anomaly_detector import detect_z_score, detect_isolation_forest, detect_dbscan
BASELINES={"z_score":detect_z_score,"isolation_forest":detect_isolation_forest,"dbscan":detect_dbscan}
