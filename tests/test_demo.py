from pathlib import Path

from quantum_sensing_earth.demo import main


def test_download_free_demo_generates_review_artifacts(monkeypatch, tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)

    result = main(["--output", str(tmp_path / "demo"), "--detectors", "z_score", "--spatial-folds", "2"])

    assert Path(result["report_html"]).exists()
    assert Path(result["results_json"]).exists()
    assert (tmp_path / "demo" / "inputs" / "pseudo_real_gravity_grid.csv").exists()
