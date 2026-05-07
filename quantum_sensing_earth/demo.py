from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
from argparse import Namespace
from pathlib import Path

from src.main import run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible download-free validation demo."
    )
    parser.add_argument(
        "--output",
        default="outputs/demo",
        help="Directory where demo artifacts should be written.",
    )
    parser.add_argument(
        "--detectors",
        nargs="+",
        default=["z_score", "dbscan", "isolation_forest"],
        choices=["z_score", "dbscan", "isolation_forest"],
        help="Detector algorithms to include in the demo.",
    )
    parser.add_argument(
        "--spatial-folds",
        type=int,
        default=3,
        help="Number of spatial folds used for held-out calibration.",
    )
    return parser.parse_args(argv)


def copy_demo_inputs(output_dir: Path) -> dict[str, str]:
    inputs_dir = output_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "grid": EXAMPLES / "pseudo_real_gravity_grid.csv",
        "mask": EXAMPLES / "pseudo_real_validation_mask.csv",
        "manifest": EXAMPLES / "pseudo_real_validation_manifest.yaml",
        "anomalies": EXAMPLES / "pseudo_real_anomalies.json",
    }
    copied: dict[str, str] = {}
    for label, source in files.items():
        destination = inputs_dir / source.name
        shutil.copy2(source, destination)
        copied[label] = str(destination)
    return copied


def build_run_args(output_dir: Path, inputs: dict[str, str], args: argparse.Namespace) -> Namespace:
    return Namespace(
        seeds="1",
        detectors=args.detectors,
        output=str(output_dir / "report"),
        sweep=False,
        no_best_config_rerun=True,
        validation_grid=inputs["grid"],
        validation_mask=inputs["mask"],
        validation_manifest=inputs["manifest"],
        validation_anomalies=inputs["anomalies"],
        missing="median",
        preprocess_detrend=True,
        preprocess_normalize="zscore",
        preprocess_clip=None,
        calibrate_thresholds=True,
        target_fpr=None,
        calibration_split="none",
        spatial_folds=args.spatial_folds,
    )


def main(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = copy_demo_inputs(output_dir)
    with contextlib.redirect_stdout(io.StringIO()):
        results = run(build_run_args(output_dir, inputs, args))
    summary = {
        "output_dir": str(output_dir),
        "report_html": str(output_dir / "report" / "report.html"),
        "results_json": str(output_dir / "report" / "results.json"),
        "inputs": inputs,
        "detectors": args.detectors,
        "spatial_folds": args.spatial_folds,
        "summary_rows": len(results.get("summary", [])),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":  # pragma: no cover
    main()
