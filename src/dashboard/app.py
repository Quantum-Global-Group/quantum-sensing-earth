from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover - optional dashboard dependency
    px = None
    go = None

try:
    import rasterio
except ImportError:  # pragma: no cover - optional geo dependency
    rasterio = None


DEFAULT_OUTPUT = Path("outputs/grace_multimonth_usdm")
BLUE = "#1f6aa5"
RED = "#c93f3f"
GREEN = "#2f7d55"
AMBER = "#b7791f"
INK = "#14212f"
MUTED = "#5b6f82"
SOFT_BORDER = "#d9e2ea"
WATER_DIVERGING = [[0.0, "#b45f06"], [0.5, "#f7f7f7"], [1.0, BLUE]]
DETECTOR_COLORS = {
    "Z Score": BLUE,
    "Dbscan": AMBER,
    "Isolation Forest": GREEN,
}
SCIENCE_COLORSCALE = [[0.0, RED], [0.5, "#f7f7f7"], [1.0, BLUE]]


st.set_page_config(
    page_title="Quantum Sensing Earth",
    page_icon="QSE",
    layout="wide",
    initial_sidebar_state="expanded",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_known_args()[0]


@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def read_raster(path: str) -> dict[str, Any]:
    if rasterio is None:
        return {"error": "Install the geo extra to render GeoTIFF maps: python -m pip install -e .[dashboard,geo]"}
    with rasterio.open(path) as src:
        array = src.read(1, masked=True)
        values = np.ma.asarray(array, dtype=float)
        if src.nodata is not None:
            values = np.ma.masked_where(np.isclose(values, float(src.nodata)), values)
        values = values.filled(np.nan)
        bounds = src.bounds
        return {
            "array": np.asarray(values, dtype=float),
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "crs": str(src.crs) if src.crs else "unknown",
            "resolution": src.res,
            "nodata": src.nodata,
            "shape": src.shape,
        }


def maybe_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return read_csv(str(path))
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def maybe_json(path: Path) -> dict[str, Any]:
    return read_json(str(path)) if path.exists() else {}


def fmt(value: Any, digits: int = 3, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "n/a"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def labelize(value: Any) -> str:
    return str(value).replace("_", " ").replace("-", " ").title()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def rgba(hex_color: str, alpha: float) -> str:
    red, green, blue = hex_to_rgb(hex_color)
    return f"rgba({red},{green},{blue},{alpha})"


def interpolate_hex(left: str, right: str, fraction: float) -> str:
    fraction = float(np.clip(fraction, 0, 1))
    left_rgb = hex_to_rgb(left)
    right_rgb = hex_to_rgb(right)
    mixed = tuple(round(a + (b - a) * fraction) for a, b in zip(left_rgb, right_rgb))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def value_color(value: Any, vmin: float, vmax: float, alpha: float = 0.66) -> str:
    if value is None or pd.isna(value) or pd.isna(vmin) or pd.isna(vmax) or vmin == vmax:
        return rgba("#aab7c4", alpha)
    value = float(np.clip(float(value), vmin, vmax))
    if vmin < 0 < vmax:
        if value < 0:
            fraction = (value - vmin) / (0 - vmin)
            return rgba(interpolate_hex(RED, "#f7f7f7", fraction), alpha)
        fraction = value / vmax
        return rgba(interpolate_hex("#f7f7f7", BLUE, fraction), alpha)
    fraction = (value - vmin) / (vmax - vmin)
    return rgba(interpolate_hex("#eff6fb", BLUE, fraction), alpha)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --qse-ink: #14212f;
            --qse-muted: #5b6f82;
            --qse-border: #d9e2ea;
            --qse-soft: #f7f9fb;
            --qse-blue: #1f6aa5;
            --qse-red: #c93f3f;
            --qse-green: #2f7d55;
            --qse-amber: #b7791f;
        }
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }
        .stApp {
            background: #fbfcfd;
        }
        h1, h2, h3 {
            letter-spacing: 0;
            color: var(--qse-ink);
        }
        div[data-testid="stSidebar"] {
            border-right: 1px solid var(--qse-border);
        }
        .qse-kicker {
            color: var(--qse-blue);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: .06em;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }
        .qse-title {
            padding-bottom: 1rem;
            margin-bottom: 1.2rem;
        }
        .qse-title h1 {
            font-size: 2.2rem;
            line-height: 1.15;
            margin: 0 0 .45rem 0;
        }
        .qse-title p {
            color: var(--qse-muted);
            font-size: 1.04rem;
            max-width: 74rem;
            margin: 0;
        }
        .qse-section {
            padding-top: 1.35rem;
            margin-top: 1.8rem;
        }
        .qse-section-title {
            max-width: 58rem;
            margin-bottom: .75rem;
        }
        .qse-section-title .eyebrow {
            color: var(--qse-blue);
            font-size: .72rem;
            font-weight: 850;
            letter-spacing: .06em;
            text-transform: uppercase;
            margin-bottom: .25rem;
        }
        .qse-section-title h2 {
            font-size: 1.55rem;
            margin: 0 0 .25rem 0;
            line-height: 1.2;
        }
        .qse-section-title p {
            color: var(--qse-muted);
            font-size: .98rem;
            margin: 0;
            line-height: 1.4;
        }
        .qse-review-grid {
            display: grid;
            grid-template-columns: minmax(280px, 1.05fr) minmax(360px, 1.45fr) minmax(250px, .9fr);
            gap: .9rem;
            align-items: stretch;
            margin-bottom: .9rem;
        }
        .qse-primary-insight {
            border: 1px solid #9cc3df;
            border-left: 6px solid var(--qse-blue);
            background: linear-gradient(180deg, #ffffff 0%, #f3f8fc 100%);
            border-radius: 8px;
            padding: 1rem 1.05rem;
            min-height: 18.4rem;
        }
        .qse-primary-insight h2 {
            margin: .1rem 0 .55rem 0;
            font-size: clamp(1.45rem, 2vw, 2.05rem);
            line-height: 1.12;
        }
        .qse-primary-insight p {
            color: #263646;
            margin: 0 0 .8rem 0;
            line-height: 1.42;
        }
        .qse-primary-insight dl {
            display: grid;
            grid-template-columns: 112px 1fr;
            gap: .4rem .65rem;
            margin: .9rem 0 0 0;
        }
        .qse-primary-insight dt {
            color: var(--qse-muted);
            font-weight: 800;
            font-size: .82rem;
        }
        .qse-primary-insight dd {
            margin: 0;
            color: var(--qse-ink);
            font-weight: 700;
        }
        .qse-side-panel {
            border: 1px solid var(--qse-border);
            background: #fff;
            border-radius: 8px;
            padding: .95rem 1rem;
            min-height: 18.4rem;
        }
        .qse-side-panel h3 {
            margin: 0 0 .55rem 0;
            font-size: 1rem;
        }
        .qse-side-panel ul {
            margin: .2rem 0 0 0;
            padding-left: 1.05rem;
            color: #263646;
        }
        .qse-side-panel li {
            margin-bottom: .48rem;
            line-height: 1.32;
        }
        .qse-claim-pill {
            display: inline-block;
            border-radius: 999px;
            padding: .18rem .55rem;
            font-size: .75rem;
            font-weight: 850;
            margin-bottom: .6rem;
            background: #fff7e6;
            color: #7a4a00;
            border: 1px solid #ebd099;
        }
        .qse-card {
            border: 1px solid var(--qse-border);
            background: #fff;
            border-radius: 8px;
            padding: .95rem 1rem;
            min-height: 6.4rem;
        }
        .qse-metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: .75rem;
            align-items: stretch;
            margin: .15rem 0 1rem 0;
        }
        .qse-metric-card {
            border: 1px solid var(--qse-border);
            background: #fff;
            border-radius: 8px;
            padding: .9rem .95rem;
            min-height: 7.1rem;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }
        .qse-metric-card .label {
            color: var(--qse-muted);
            font-size: .74rem;
            font-weight: 800;
            letter-spacing: .04em;
            text-transform: uppercase;
            margin-bottom: .38rem;
            line-height: 1.15;
        }
        .qse-metric-card .value {
            color: var(--qse-ink);
            font-size: clamp(1.1rem, 1.4vw, 1.45rem);
            font-weight: 760;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .qse-metric-card .note {
            color: var(--qse-muted);
            font-size: .84rem;
            line-height: 1.28;
            margin-top: auto;
            padding-top: .55rem;
        }
        .qse-card .label {
            color: var(--qse-muted);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .04em;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }
        .qse-card .value {
            color: var(--qse-ink);
            font-size: 1.55rem;
            font-weight: 760;
            line-height: 1.18;
        }
        .qse-card .note {
            color: var(--qse-muted);
            font-size: .88rem;
            margin-top: .42rem;
        }
        .qse-verdict {
            border: 1px solid #a9cfba;
            border-left: 5px solid var(--qse-green);
            background: #f3faf6;
            border-radius: 8px;
            padding: 1.05rem 1.15rem;
        }
        .qse-warning {
            border-color: #dfc899;
            border-left-color: var(--qse-amber);
            background: #fffaf0;
        }
        .qse-verdict strong {
            display: block;
            color: var(--qse-ink);
            margin-bottom: .32rem;
        }
        .qse-verdict span {
            color: #273849;
        }
        .qse-method {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .7rem;
            margin: .8rem 0 .3rem;
        }
        .qse-method-step {
            border: 1px solid var(--qse-border);
            border-radius: 8px;
            background: #fff;
            padding: .85rem;
            min-height: 7rem;
        }
        .qse-method-step b {
            color: var(--qse-ink);
            display: block;
            margin-bottom: .32rem;
        }
        .qse-method-step span {
            color: var(--qse-muted);
            font-size: .9rem;
        }
        .qse-readiness {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .55rem;
        }
        .qse-rung {
            border: 1px solid var(--qse-border);
            background: #fff;
            border-radius: 8px;
            padding: .75rem;
            min-height: 5.8rem;
        }
        .qse-rung.done {
            background: #f3faf6;
            border-color: #a9cfba;
        }
        .qse-rung.current {
            background: #f1f7fc;
            border-color: #90bfe0;
        }
        .qse-rung b {
            display: block;
            color: var(--qse-ink);
            margin-bottom: .25rem;
        }
        .qse-rung span {
            color: var(--qse-muted);
            font-size: .84rem;
        }
        .qse-explain {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .55rem;
            margin: .65rem 0 1rem;
        }
        .qse-explain div {
            border: 1px solid var(--qse-border);
            border-radius: 8px;
            background: var(--qse-soft);
            padding: .72rem .78rem;
            color: #263646;
            font-size: .9rem;
        }
        .qse-explain b {
            display: block;
            color: var(--qse-ink);
            margin-bottom: .25rem;
        }
        .qse-artifact {
            color: var(--qse-muted);
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            font-size: .84rem;
        }
        .qse-detector-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .75rem;
            margin: .7rem 0 1rem;
        }
        .qse-detector-card {
            border: 1px solid var(--qse-border);
            border-radius: 8px;
            background: #fff;
            padding: .9rem .95rem;
            min-height: 8.4rem;
        }
        .qse-detector-card.good {
            border-top: 4px solid var(--qse-green);
        }
        .qse-detector-card.warn {
            border-top: 4px solid var(--qse-amber);
        }
        .qse-detector-card.bad {
            border-top: 4px solid var(--qse-red);
        }
        .qse-detector-card b {
            color: var(--qse-ink);
            display: block;
            margin-bottom: .32rem;
        }
        .qse-detector-card span {
            color: var(--qse-muted);
            font-size: .9rem;
        }
        .qse-month-card {
            border: 1px solid var(--qse-border);
            border-radius: 8px;
            background: #fff;
            padding: .9rem;
            margin-bottom: .9rem;
        }
        .qse-month-title {
            display: flex;
            justify-content: space-between;
            gap: .75rem;
            align-items: baseline;
            border-bottom: 1px solid var(--qse-border);
            padding-bottom: .55rem;
            margin-bottom: .75rem;
        }
        .qse-month-title b {
            color: var(--qse-ink);
            font-size: 1rem;
        }
        .qse-month-title span {
            color: var(--qse-muted);
            font-size: .84rem;
        }
        .qse-month-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .45rem;
            margin-top: .7rem;
        }
        .qse-month-metrics div {
            background: var(--qse-soft);
            border: 1px solid var(--qse-border);
            border-radius: 6px;
            padding: .45rem .5rem;
        }
        .qse-month-metrics b {
            display: block;
            color: var(--qse-muted);
            font-size: .68rem;
            letter-spacing: .04em;
            text-transform: uppercase;
        }
        .qse-month-metrics span {
            color: var(--qse-ink);
            font-weight: 760;
            font-size: 1rem;
        }
        .qse-final-verdict {
            border: 1px solid #a9cfba;
            border-left: 5px solid var(--qse-green);
            background: #f3faf6;
            border-radius: 8px;
            padding: 1rem 1.1rem;
        }
        .qse-final-verdict h3 {
            margin: 0 0 .55rem 0;
            font-size: 1.05rem;
        }
        .qse-final-verdict dl {
            display: grid;
            grid-template-columns: 210px 1fr;
            gap: .42rem .75rem;
            margin: 0;
        }
        .qse-final-verdict dt {
            color: var(--qse-muted);
            font-weight: 800;
        }
        .qse-final-verdict dd {
            margin: 0;
            color: var(--qse-ink);
        }
        .qse-stale {
            border: 1px solid #dfc899;
            border-left: 5px solid var(--qse-amber);
            background: #fffaf0;
            border-radius: 8px;
            padding: 1rem 1.1rem;
            margin: .25rem 0 1rem;
        }
        .qse-stale b {
            display: block;
            color: var(--qse-ink);
            margin-bottom: .35rem;
        }
        .qse-stale code {
            display: block;
            white-space: pre-wrap;
            background: #fff;
            border: 1px solid #ead7aa;
            border-radius: 6px;
            padding: .55rem .65rem;
            margin-top: .55rem;
            color: #263646;
        }
        .qse-coverage-warning {
            border: 1px solid #dfc899;
            border-left: 5px solid var(--qse-amber);
            background: #fffaf0;
            border-radius: 8px;
            padding: 1rem 1.1rem;
            margin: .25rem 0 1rem;
        }
        .qse-coverage-warning b {
            display: block;
            color: var(--qse-ink);
            margin-bottom: .35rem;
        }
        @media (max-width: 980px) {
            .qse-review-grid, .qse-method, .qse-readiness, .qse-explain, .qse-metric-grid, .qse-detector-grid, .qse-month-metrics {
                grid-template-columns: 1fr;
            }
            .qse-final-verdict dl {
                grid-template-columns: 1fr;
            }
            .qse-primary-insight dl {
                grid-template-columns: 1fr;
            }
        }
        @media (min-width: 981px) and (max-width: 1220px) {
            .qse-metric-grid {
                grid-template-columns: repeat(3, minmax(180px, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def html_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="qse-card">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(cards: list[tuple[str, str, str]]) -> None:
    chunks = ["<div class='qse-metric-grid'>"]
    for label, value, note in cards:
        chunks.append(
            "<div class='qse-metric-card'>"
            f"<div class='label'>{html.escape(label)}</div>"
            f"<div class='value'>{html.escape(value)}</div>"
            f"<div class='note'>{html.escape(note)}</div>"
            "</div>"
        )
    chunks.append("</div>")
    st.markdown("".join(chunks), unsafe_allow_html=True)


def section_heading(eyebrow: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="qse-section-title">
          <div class="eyebrow">{html.escape(eyebrow)}</div>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def detector_story_panel() -> None:
    st.markdown(
        """
        <div class="qse-detector-grid">
          <div class="qse-detector-card good">
            <b>Winner: z-score is usable</b>
            <span>It is simple, stable, and best matched to broad drought-mask agreement on this coarse one-degree grid. Treat it as the current baseline, not a final detector.</span>
          </div>
          <div class="qse-detector-card bad">
            <b>Failure mode: DBSCAN struggles</b>
            <span>DBSCAN expects compact density clusters. USDM labels are broad spatial regions, so it often misses the target geometry or collapses to near-zero F1.</span>
          </div>
          <div class="qse-detector-card warn">
            <b>Watch: isolation forest over-detects</b>
            <span>It can find unusual cells, but on this problem it tends to trade recall for extra false positives. Useful diagnostically, risky as the headline model.</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def verdict(title: str, body: str, warning: bool = False) -> None:
    klass = "qse-verdict qse-warning" if warning else "qse-verdict"
    st.markdown(
        f"""<div class="{klass}"><strong>{title}</strong><span>{body}</span></div>""",
        unsafe_allow_html=True,
    )


def explainer(show: str, good: str, result: str, caution: str) -> None:
    st.markdown(
        f"""
        <div class="qse-explain">
          <div><b>What this shows</b>{show}</div>
          <div><b>Good result</b>{good}</div>
          <div><b>This run</b>{result}</div>
          <div><b>Do not conclude</b>{caution}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_bundle(output_dir: Path) -> dict[str, Any]:
    return {
        "timeline": maybe_csv(output_dir / "timeline_metrics.csv"),
        "month_alignment": maybe_csv(output_dir / "month_alignment.csv"),
        "coverage_summary": maybe_json(output_dir / "coverage_summary.json"),
        "artifact_manifest": maybe_json(output_dir / "artifact_manifest.json"),
        "gldas_metrics": maybe_csv(output_dir / "gldas_hydrology_metrics.csv"),
        "tws_metrics": maybe_csv(output_dir / "tws_comparison_metrics.csv"),
        "basin_metrics": maybe_csv(output_dir / "basin_metrics.csv"),
        "basin_summary_table": maybe_csv(output_dir / "basin_summary.csv"),
        "groundwater_observations": maybe_csv(output_dir / "groundwater_observations.csv"),
        "groundwater_monthly": maybe_csv(output_dir / "groundwater_basin_monthly.csv"),
        "groundwater_metrics": maybe_csv(output_dir / "groundwater_validation_metrics.csv"),
        "groundwater_summary_table": maybe_csv(output_dir / "groundwater_validation_summary.csv"),
        "gldas_summary": maybe_json(output_dir / "gldas_hydrology_summary.json"),
        "tws_summary": maybe_json(output_dir / "tws_comparison_summary.json"),
        "basin_summary": maybe_json(output_dir / "basin_summary.json"),
        "groundwater_summary": maybe_json(output_dir / "groundwater_validation_summary.json") or maybe_json(output_dir / "groundwater_summary.json"),
    }


def resolve_artifact(path_value: Any, output_dir: Path) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, output_dir / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def detection_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    metrics = ["f1", "iou", "false_positive_rate", "false_negative_rate", "rmse", "snr"]
    grouped = (
        df.groupby(["threshold", "sensor_profile", "algorithm"], dropna=False)[metrics]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
    )
    grouped.columns = [
        "_".join(col).rstrip("_") if isinstance(col, tuple) else col for col in grouped.columns
    ]
    grouped["review_score"] = grouped["f1_mean"].fillna(0) + grouped["iou_mean"].fillna(0)
    return grouped.sort_values(["review_score", "f1_mean"], ascending=False)


def best_row(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    scores = df["f1"].fillna(0) + df["iou"].fillna(0)
    return df.loc[scores.idxmax()]


def weakest_row(df: pd.DataFrame) -> pd.Series | None:
    candidates = df[df["algorithm"].eq("z_score")] if "algorithm" in df else df
    if candidates.empty:
        candidates = df
    if candidates.empty:
        return None
    return candidates.loc[candidates["f1"].fillna(0).idxmin()]


def groundwater_ready(groundwater_summary: dict[str, Any]) -> bool:
    return groundwater_summary.get("status") == "ok" and groundwater_summary.get("valid_basin_threshold_rows", 0) > 0


def target_types(gldas_summary: dict[str, Any], tws_summary: dict[str, Any], groundwater_summary: dict[str, Any]) -> str:
    values = ["drought proxy"]
    if tws_summary.get("target_type"):
        values.append("GRACE TWS")
    if gldas_summary.get("status") == "ok":
        values.append("external hydrology")
    if groundwater_summary.get("status") in {"ok", "insufficient_months"}:
        values.append("groundwater wells")
    return " + ".join(values)


def scientific_readiness(gldas_summary: dict[str, Any], groundwater_summary: dict[str, Any]) -> tuple[str, str]:
    if groundwater_ready(groundwater_summary):
        return "Level 5", "Groundwater/storage target present"
    if gldas_summary.get("status") == "ok":
        return "Level 4", "External hydrology target reached"
    return "Level 3", "Real raster plus independent drought proxy"


def basin_callouts(basin_table: pd.DataFrame, groundwater_table: pd.DataFrame) -> tuple[str, str]:
    if not groundwater_table.empty and "status" in groundwater_table and "grace_groundwater_correlation" in groundwater_table:
        ok_rows = groundwater_table[groundwater_table["status"].eq("ok")]
        if not ok_rows.empty:
            best = ok_rows.sort_values("grace_groundwater_correlation", ascending=False, na_position="last").head(1).iloc[0]
            weakest = ok_rows.sort_values("grace_groundwater_correlation", ascending=True, na_position="last").head(1).iloc[0]
            return (
                f"{best.get('basin_name', 'n/a')}: {fmt(best.get('grace_groundwater_correlation'))}",
                f"{weakest.get('basin_name', 'n/a')}: {fmt(weakest.get('grace_groundwater_correlation'))}",
            )
    if not basin_table.empty and "grace_gldas_correlation" in basin_table:
        best = basin_table.sort_values("grace_gldas_correlation", ascending=False, na_position="last").head(1).iloc[0]
        weakest = basin_table.sort_values("grace_gldas_correlation", ascending=True, na_position="last").head(1).iloc[0]
        return (
            f"{best.get('basin_name', 'n/a')}: {fmt(best.get('grace_gldas_correlation'))}",
            f"{weakest.get('basin_name', 'n/a')}: {fmt(weakest.get('grace_gldas_correlation'))}",
        )
    return "n/a", "n/a"


def latest_month(df: pd.DataFrame) -> str | None:
    if df.empty or "month" not in df:
        return None
    months = pd.to_datetime(df["month"].dropna().astype(str), errors="coerce")
    if months.empty or months.isna().all():
        return None
    return months.max().strftime("%Y-%m")


def run_is_stale(df: pd.DataFrame, max_age_years: int = 5) -> bool:
    month = latest_month(df)
    if month is None:
        return False
    latest = pd.to_datetime(month)
    now = pd.Timestamp.now()
    return bool((now - latest).days > max_age_years * 365)


def stale_data_warning(df: pd.DataFrame) -> None:
    month = latest_month(df)
    if not month or not run_is_stale(df):
        return
    st.markdown(
        f"""
        <div class="qse-stale">
          <b>This is an old demonstration run, not a current validation result.</b>
          The newest month in this output is <strong>{html.escape(month)}</strong>. That is useful for proving
          the pipeline wiring, but it is not relevant evidence for present-day drought, groundwater, or hydrology
          conditions. Regenerate the dashboard with recent GRACE-FO and matching USDM/GLDAS data before using it
          for any current scientific story.
          <code>python examples\\grace_tellus\\run_multimonth_usdm.py --mission grace-fo --start 2026-01-01 --months 3 --thresholds 1 2 3 --spatial-folds 4 --output outputs\\gracefo_recent_usdm</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ok_months(frame: pd.DataFrame) -> set[str]:
    if frame.empty or "month" not in frame:
        return set()
    if "status" in frame:
        frame = frame[frame["status"].eq("ok")]
    return set(frame["month"].dropna().astype(str))


def coverage_month_sets(bundle: dict[str, Any]) -> dict[str, set[str]]:
    timeline_months = ok_months(bundle["timeline"])
    return {
        "GRACE": timeline_months,
        "USDM": timeline_months,
        "GLDAS": ok_months(bundle["gldas_metrics"]),
        "TWS": ok_months(bundle["tws_metrics"]),
        "Basin": ok_months(bundle["basin_metrics"]),
        "Groundwater": ok_months(bundle["groundwater_monthly"]),
    }


def coverage_timeline_figure(bundle: dict[str, Any], height: int = 270) -> Any | None:
    if go is None:
        return None
    month_sets = coverage_month_sets(bundle)
    months = sorted(set().union(*month_sets.values())) if month_sets else []
    if not months:
        return None
    targets = list(month_sets.keys())
    z = [[1 if month in month_sets[target] else 0 for month in months] for target in targets]
    text = [
        [f"{target}<br>{month}<br>{'available' if value else 'missing'}" for month, value in zip(months, row)]
        for target, row in zip(targets, z)
    ]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=months,
            y=targets,
            text=text,
            hovertemplate="%{text}<extra></extra>",
            colorscale=[[0, "#f4c95d"], [0.499, "#f4c95d"], [0.5, GREEN], [1, GREEN]],
            showscale=False,
            xgap=2,
            ygap=2,
        )
    )
    fig.update_layout(
        title="Month Coverage By Evidence Target",
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=8, t=42, b=8),
        xaxis_title="Month",
        yaxis_title="",
    )
    fig.update_xaxes(tickangle=0)
    fig.add_annotation(
        text="Green = available, amber = missing",
        xref="paper",
        yref="paper",
        x=1,
        y=1.17,
        showarrow=False,
        xanchor="right",
        font=dict(size=12, color=MUTED),
    )
    return fig


def coverage_label(bundle: dict[str, Any], target: str) -> str:
    month_sets = coverage_month_sets(bundle)
    detection_months = month_sets.get("GRACE", set())
    target_months = month_sets.get(target, set())
    denominator = len(detection_months) or len(target_months)
    return f"{len(target_months)}/{denominator}" if denominator else "n/a"


def coverage_warning(bundle: dict[str, Any]) -> None:
    timeline = bundle["timeline"]
    detection_months = ok_months(timeline)
    gldas_months = ok_months(bundle["gldas_metrics"])
    tws_months = ok_months(bundle["tws_metrics"])
    groundwater_months = ok_months(bundle["groundwater_monthly"])
    if not detection_months:
        return
    missing_gldas = sorted(detection_months - gldas_months)
    missing_tws = sorted(detection_months - tws_months)
    missing_groundwater = sorted(detection_months - groundwater_months)
    groundwater_configured = bundle["groundwater_summary"].get("status") not in {None, "", "not_configured"}
    if not missing_gldas and not missing_tws and (not groundwater_configured or not missing_groundwater):
        return
    gldas_coverage = bundle["gldas_summary"].get("coverage") or f"{len(gldas_months)}/{len(detection_months)}"
    tws_coverage = bundle["tws_summary"].get("coverage") or f"{len(tws_months)}/{len(detection_months)}"
    groundwater_coverage = (
        bundle["coverage_summary"].get("targets", {}).get("groundwater", {}).get("coverage")
        or f"{len(groundwater_months)}/{len(detection_months)}"
    )
    details = []
    if missing_gldas:
        details.append(f"GLDAS missing: {', '.join(missing_gldas)}")
    if missing_tws:
        details.append(f"TWS missing: {', '.join(missing_tws)}")
    if groundwater_configured and missing_groundwater:
        details.append(f"Groundwater missing: {', '.join(missing_groundwater)}")
    st.markdown(
        f"""
        <div class="qse-coverage-warning">
          <b>Target coverage is incomplete for this run.</b>
          Detection months: <strong>{len(detection_months)}</strong>.
          GLDAS coverage: <strong>{html.escape(str(gldas_coverage))}</strong>.
          TWS coverage: <strong>{html.escape(str(tws_coverage))}</strong>.
          Groundwater coverage: <strong>{html.escape(str(groundwater_coverage))}</strong>.
          {'; '.join(html.escape(item) for item in details)}.
          Treat unmatched targets as partial evidence until detector, hydrology, and groundwater months align.
        </div>
        """,
        unsafe_allow_html=True,
    )


def coverage_overview(bundle: dict[str, Any]) -> None:
    alignment = bundle["month_alignment"]
    summary = bundle["coverage_summary"]
    if alignment.empty and not summary:
        return
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Data hierarchy",
        "Month Coverage",
        "Coverage appears before performance metrics so reviewers can see which evidence targets align and which are partial.",
    )
    targets = summary.get("targets", {}) if summary else {}
    cards = []
    for target in ["grace", "usdm", "gldas", "tws", "basin", "groundwater"]:
        info = targets.get(target, {})
        cards.append((labelize(target), str(info.get("coverage", "n/a")), "month alignment"))
    metric_grid(cards)
    explainer(
        "Which target datasets are present for each GRACE/GRACE-FO detector month.",
        "Every validation target covers the same month keys before claims are summarized.",
        "Missing months are shown explicitly and should be treated as partial evidence.",
        "That a mean metric with partial coverage represents the full detector batch.",
    )
    if not alignment.empty:
        st.dataframe(alignment, width="stretch", hide_index=True)


def filter_controls(df: pd.DataFrame) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    if df.empty:
        return controls
    with st.sidebar:
        st.divider()
        st.subheader("Review controls")
        thresholds = sorted(df["threshold"].dropna().unique().tolist())
        sensors = sorted(df["sensor_profile"].dropna().unique().tolist())
        algorithms = sorted(df["algorithm"].dropna().unique().tolist())
        months = sorted(df["month"].dropna().unique().tolist())

        controls["thresholds"] = st.multiselect("USDM threshold", thresholds, default=thresholds)
        controls["sensors"] = st.multiselect("Sensor profile", sensors, default=sensors)
        controls["algorithms"] = st.multiselect("Detector", algorithms, default=algorithms)
        controls["month"] = st.selectbox("Map/outcome month", months, index=0)
        controls["metric"] = st.selectbox("Primary detection metric", ["f1", "iou", "false_positive_rate"], index=0)
    return controls


def apply_filters(df: pd.DataFrame, controls: dict[str, Any]) -> pd.DataFrame:
    if df.empty or not controls:
        return df.copy()
    mask = (
        df["threshold"].isin(controls["thresholds"])
        & df["sensor_profile"].isin(controls["sensors"])
        & df["algorithm"].isin(controls["algorithms"])
    )
    return df.loc[mask].copy()


def title_block() -> None:
    st.markdown(
        """
        <div class="qse-title">
          <div class="qse-kicker">Technical validation dashboard</div>
          <h1>GRACE/GRACE-FO hydrology validation with detector comparison</h1>
          <p>
            This is a GRACE/GRACE-FO hydrology validation workflow with detector comparison, not a proven
            quantum groundwater detector. The dashboard reviews whether water-mass rasters, drought labels,
            GLDAS terrestrial water storage, basin summaries, and groundwater wells produce repeatable evidence that a technical
            reviewer can inspect.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def readiness_ladder(gldas_summary: dict[str, Any], groundwater_summary: dict[str, Any]) -> None:
    reached_gldas = gldas_summary.get("status") == "ok"
    reached_groundwater = groundwater_ready(groundwater_summary)
    steps = [
        ("1. Synthetic", "Metrics and pipeline plumbing.", True, False),
        ("2. Real raster", "GRACE GeoTIFFs with metadata.", True, False),
        ("3. Drought proxy", "Independent USDM masks.", True, not reached_gldas and not reached_groundwater),
        ("4. Hydrology target", "GLDAS/TWS comparison.", reached_gldas, reached_gldas and not reached_groundwater),
        ("5. Groundwater", "Basin wells/storage target.", reached_groundwater, reached_groundwater),
    ]
    chunks = ["<div class='qse-readiness'>"]
    for title, body, done, current in steps:
        klass = "qse-rung"
        if done:
            klass += " done"
        if current:
            klass += " current"
        chunks.append(f"<div class='{klass}'><b>{title}</b><span>{body}</span></div>")
    chunks.append("</div>")
    st.markdown("".join(chunks), unsafe_allow_html=True)


def validation_status(
    bundle: dict[str, Any],
    timeline: pd.DataFrame,
    filtered: pd.DataFrame,
    gldas_summary: dict[str, Any],
    tws_summary: dict[str, Any],
    groundwater_summary: dict[str, Any],
    basin_summary_table: pd.DataFrame,
    groundwater_summary_table: pd.DataFrame,
) -> None:
    level, level_note = scientific_readiness(gldas_summary, groundwater_summary)
    best = best_row(filtered)
    weak = weakest_row(filtered)
    months = timeline["month"].nunique() if not timeline.empty else 0
    best_text = "n/a"
    if best is not None:
        best_text = f"{labelize(best['algorithm'])}, F1 {fmt(best['f1'])}"
    weak_text = "n/a"
    if weak is not None:
        weak_text = f"{weak['month']} D{weak['threshold']}+, F1 {fmt(weak['f1'])}"
    strongest_basin, weakest_basin = basin_callouts(basin_summary_table, groundwater_summary_table)

    section_heading(
        "Golden zone",
        "Validation Status",
        "The top row separates the project’s strongest defensible claim from supporting evidence and claim limits.",
    )
    left, middle, right = st.columns([1.05, 1.45, .9])
    with left:
        st.markdown(
            f"""
            <div class="qse-primary-insight">
              <div class="qse-kicker">Current scientific claim</div>
              <h2>{html.escape(level)}: {html.escape(level_note)}</h2>
              <p>
                This run supports reproducible hydrology workflow validation. It should be reviewed as
                evidence alignment, not as field proof of groundwater discovery or quantum advantage.
              </p>
              <dl>
                <dt>Months</dt><dd>{html.escape(str(months))}</dd>
                <dt>Targets</dt><dd>{html.escape(target_types(gldas_summary, tws_summary, groundwater_summary))}</dd>
                <dt>Best detector</dt><dd>{html.escape(best_text)}</dd>
                <dt>Weak point</dt><dd>{html.escape(weak_text)}</dd>
              </dl>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with middle:
        fig = coverage_timeline_figure(bundle)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            verdict("Coverage unavailable", "No month-level coverage artifacts are available for this output.", warning=True)
    with right:
        st.markdown(
            f"""
            <div class="qse-side-panel">
              <span class="qse-claim-pill">Claim boundary</span>
              <h3>What a reviewer should take away</h3>
              <ul>
                <li><strong>Workflow validation:</strong> yes, when artifacts and tests are present.</li>
                <li><strong>Hydrology comparison:</strong> {html.escape('yes' if gldas_summary.get('status') == 'ok' else 'partial or missing')}.</li>
                <li><strong>Groundwater validation:</strong> {html.escape('begun' if groundwater_ready(groundwater_summary) else 'not yet strong')}.</li>
                <li><strong>Groundwater discovery:</strong> not proven.</li>
                <li><strong>Quantum advantage:</strong> not claimed.</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    metric_grid(
        [
            ("GRACE/USDM", coverage_label(bundle, "GRACE"), "detector months"),
            ("GLDAS", coverage_label(bundle, "GLDAS"), "external hydrology"),
            ("TWS", coverage_label(bundle, "TWS"), "processing-center comparison"),
            ("Groundwater", coverage_label(bundle, "Groundwater"), "well/basin months"),
            ("Strongest basin", strongest_basin, "groundwater first, GLDAS fallback"),
            ("Weakest basin", weakest_basin, "groundwater first, GLDAS fallback"),
        ]
    )
    readiness_ladder(gldas_summary, groundwater_summary)


def evidence_trail() -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Method context",
        "Evidence Trail",
        "A compact workflow from satellite water-mass rasters to proxy masks, detectors, hydrology checks, and groundwater evidence.",
    )
    st.markdown(
        """
        <div class="qse-method">
          <div class="qse-method-step"><b>1. GRACE raster</b><span>Monthly water-mass anomaly grids are cropped to a western U.S. study region.</span></div>
          <div class="qse-method-step"><b>2. Independent mask</b><span>USDM drought classes are rasterized onto the GRACE grid as D1+, D2+, and D3+ proxy labels.</span></div>
          <div class="qse-method-step"><b>3. Detector run</b><span>Classical and quantum-inspired sensor profiles feed z-score, DBSCAN, and isolation forest detectors.</span></div>
          <div class="qse-method-step"><b>4. Hydrology check</b><span>GLDAS, JPL/CSR TWS, and groundwater wells ask whether basin-scale water storage moves consistently.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    explainer(
        "The chain of evidence from raw water-mass rasters to masks, detector outputs, and hydrology agreement.",
        "Each step has explicit artifacts, provenance, and metrics that can be inspected independently.",
        "The workflow is credible as software validation and early hydrology alignment.",
        "That proxy agreement is the same thing as field-validated groundwater detection.",
    )


def selected_month_row(df: pd.DataFrame, controls: dict[str, Any]) -> pd.Series | None:
    if df.empty:
        return None
    month = controls.get("month")
    threshold_values = controls.get("thresholds") or sorted(df["threshold"].unique().tolist())
    threshold = threshold_values[0]
    rows = df[(df["month"].eq(month)) & (df["threshold"].eq(threshold))]
    if rows.empty:
        rows = df[df["month"].eq(month)]
    if rows.empty:
        rows = df
    return rows.iloc[0]


def study_region(output_dir: Path, timeline: pd.DataFrame, controls: dict[str, Any]) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Geospatial context",
        "Study Region",
        "The map shows where the validation happens, which cells are GRACE/GRACE-FO values, and where the independent USDM mask is active.",
    )
    row = selected_month_row(timeline, controls)
    if row is None:
        st.info("No timeline rows are available for the study-region map.")
        return

    grid_path = resolve_artifact(row["grid_path"], output_dir)
    mask_path = resolve_artifact(row["mask_path"], output_dir)
    left, right = st.columns([1.45, .55])
    with left:
        fig = make_region_figure(grid_path, mask_path, str(row["month"]), int(row["threshold"]))
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            fallback = output_dir / "study_region_map.png"
            if fallback.exists():
                st.image(str(fallback), caption="Fallback static study-region artifact", width="stretch")
            else:
                st.warning("No GeoTIFF map or fallback region image is available.")
    with right:
        html_card("Selected month", str(row["month"]), f"USDM D{row['threshold']}+ mask")
        html_card("Grid artifact", grid_path.name, "GRACE raster")
        html_card("Mask artifact", mask_path.name, "USDM proxy label")
    explainer(
        "The geographic crop, GRACE cell footprint, and drought-mask overlay used for validation.",
        "A clear spatial overlap between the raster, mask, and study area, with CRS/resolution preserved.",
        "The map is coordinate-aware when rasterio is installed; otherwise it falls back to the static artifact.",
        "That the mask is direct groundwater truth. It is a spatially aligned drought proxy.",
    )


def make_region_figure(grid_path: Path, mask_path: Path, month: str, threshold: int) -> Any | None:
    if go is None or not grid_path.exists() or not mask_path.exists():
        return None
    grid = read_raster(str(grid_path))
    mask = read_raster(str(mask_path))
    if grid.get("error") or mask.get("error"):
        st.info(grid.get("error") or mask.get("error"))
        return None

    array = np.asarray(grid["array"], dtype=float)
    array = np.where(np.abs(array) > 10000, np.nan, array)
    mask_array = np.where(mask["array"] > 0, 1.0, np.nan)
    finite = array[np.isfinite(array)]
    z_limit = float(np.nanpercentile(np.abs(finite), 98)) if finite.size else 1.0
    if not np.isfinite(z_limit) or z_limit <= 0:
        z_limit = 1.0
    left, bottom, right, top = grid["bounds"]
    x = np.linspace(left, right, array.shape[1])
    y = np.linspace(top, bottom, array.shape[0])

    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            z=array,
            x=x,
            y=y,
            colorscale=WATER_DIVERGING,
            zmin=-z_limit,
            zmax=z_limit,
            zmid=0,
            colorbar=dict(title="GRACE anomaly<br>cm EWT", ticksuffix=" cm"),
            hovertemplate="lon=%{x:.2f}<br>lat=%{y:.2f}<br>GRACE=%{z:.3f} cm<extra></extra>",
            name="GRACE anomaly",
        )
    )
    fig.add_trace(
        go.Heatmap(
            z=mask_array,
            x=x,
            y=y,
            colorscale=[[0, "rgba(201,63,63,0.15)"], [1, "rgba(201,63,63,0.75)"]],
            showscale=False,
            hovertemplate="USDM mask cell<extra></extra>",
            name=f"USDM D{threshold}+ mask",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=12, color=RED, opacity=.75, symbol="square"),
            name=f"USDM D{threshold}+ mask",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=12, color=BLUE, opacity=.85, symbol="square"),
            name="GRACE cm EWT anomaly",
        )
    )
    for xi in x:
        fig.add_shape(type="line", x0=xi, x1=xi, y0=bottom, y1=top, line=dict(color="rgba(20,33,47,.13)", width=1))
    for yi in y:
        fig.add_shape(type="line", x0=left, x1=right, y0=yi, y1=yi, line=dict(color="rgba(20,33,47,.13)", width=1))
    fig.add_shape(
        type="rect",
        x0=left,
        x1=right,
        y0=bottom,
        y1=top,
        line=dict(color=INK, width=1.2),
        fillcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        title=f"{month} GRACE/GRACE-FO Water-Mass Anomaly With USDM D{threshold}+ Overlay",
        template="plotly_white",
        height=520,
        margin=dict(l=10, r=10, t=55, b=10),
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,.85)",
        ),
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.add_annotation(
        text=f"CRS {grid['crs']} | resolution {fmt(grid['resolution'][0])} x {fmt(abs(grid['resolution'][1]))}",
        xref="paper",
        yref="paper",
        x=0,
        y=1.08,
        showarrow=False,
        font=dict(size=12, color=MUTED),
        align="left",
    )
    fig.add_annotation(
        text="Validation crop",
        x=(left + right) / 2,
        y=top - 1,
        showarrow=False,
        font=dict(size=13, color=INK),
        bgcolor="rgba(255,255,255,.72)",
        bordercolor="rgba(20,33,47,.25)",
        borderpad=4,
    )
    fig.add_annotation(
        text="Red cells: independent USDM drought proxy",
        x=left + 1.1,
        y=bottom + 1.1,
        showarrow=False,
        font=dict(size=12, color=RED),
        bgcolor="rgba(255,255,255,.78)",
        bordercolor="rgba(201,63,63,.35)",
        borderpad=4,
        align="left",
    )
    region_labels = [
        ("California", -119.6, 37.2),
        ("Central Valley", -120.5, 36.4),
        ("Great Basin", -116.3, 40.2),
        ("Rockies", -108.2, 43.0),
        ("Pacific coast", -123.9, 43.5),
    ]
    for label, lon, lat in region_labels:
        if left <= lon <= right and bottom <= lat <= top:
            fig.add_annotation(
                text=label,
                x=lon,
                y=lat,
                showarrow=False,
                font=dict(size=11, color="#273849"),
                bgcolor="rgba(255,255,255,.58)",
                borderpad=2,
            )
    return fig


def detection_chart(df: pd.DataFrame, metric: str) -> Any | None:
    if px is None or df.empty:
        return None
    chart_df = df.copy()
    chart_df["Detector"] = chart_df["algorithm"].map(labelize)
    chart_df["Sensor"] = chart_df["sensor_profile"].map(labelize)
    chart_df["USDM"] = "D" + chart_df["threshold"].astype(str) + "+"
    chart_df["Series"] = chart_df["USDM"] + " | " + chart_df["Sensor"] + " | " + chart_df["Detector"]
    y_label = f"{labelize(metric)} (unitless rate)" if metric in {"f1", "iou", "false_positive_rate", "false_negative_rate"} else labelize(metric)
    fig = px.line(
        chart_df,
        x="month",
        y=metric,
        color="Detector",
        line_dash="USDM",
        facet_row="Sensor",
        markers=True,
        color_discrete_map=DETECTOR_COLORS,
        labels={"month": "Month", metric: y_label},
        template="plotly_white",
    )
    fig.update_layout(height=540, margin=dict(l=10, r=10, t=35, b=10), legend_title_text="Detector")
    if metric in {"f1", "iou", "false_positive_rate", "false_negative_rate"}:
        fig.update_yaxes(range=[0, 1])
        reference = 0.5 if metric in {"f1", "iou"} else 0.1
        fig.add_hline(
            y=reference,
            line_dash="dash",
            line_color=AMBER,
            annotation_text="review reference" if metric in {"f1", "iou"} else "FPR caution",
            annotation_position="top left",
        )
    else:
        fig.update_yaxes(rangemode="tozero")
    return fig


def detector_tradeoff_chart(df: pd.DataFrame) -> Any | None:
    if px is None or df.empty:
        return None
    required = {"false_positive_rate", "f1", "iou", "algorithm", "sensor_profile", "threshold", "month"}
    if not required.issubset(df.columns):
        return None
    chart_df = df.copy()
    chart_df["Detector"] = chart_df["algorithm"].map(labelize)
    chart_df["Sensor"] = chart_df["sensor_profile"].map(labelize)
    chart_df["USDM threshold"] = "D" + chart_df["threshold"].astype(str) + "+"
    chart_df["IoU size"] = chart_df["iou"].fillna(0).clip(lower=0) + 0.04
    fig = px.scatter(
        chart_df,
        x="false_positive_rate",
        y="f1",
        color="Detector",
        symbol="Sensor",
        size="IoU size",
        hover_data={
            "month": True,
            "USDM threshold": True,
            "false_positive_rate": ":.3f",
            "f1": ":.3f",
            "iou": ":.3f",
            "IoU size": False,
        },
        facet_col="USDM threshold",
        color_discrete_map=DETECTOR_COLORS,
        template="plotly_white",
        labels={"false_positive_rate": "False positive rate", "f1": "F1 score"},
    )
    fig.add_hline(y=0.5, line_dash="dash", line_color=AMBER, annotation_text="F1 review reference")
    fig.add_vline(x=0.1, line_dash="dash", line_color=AMBER, annotation_text="FPR caution")
    fig.update_xaxes(range=[0, 1])
    fig.update_yaxes(range=[0, 1])
    fig.update_layout(
        title="Detector Tradeoff: F1 Versus False Positives",
        height=420,
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text="Detector",
    )
    return fig


def detection_results(output_dir: Path, filtered: pd.DataFrame, controls: dict[str, Any]) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Detector layer",
        "Detection Results",
        "Detector performance is secondary evidence: useful for comparison, but not the core scientific claim.",
    )
    detector_story_panel()
    metric = controls.get("metric", "f1")
    fig = detection_chart(filtered, metric)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.dataframe(filtered, width="stretch", hide_index=True)
    tradeoff_fig = detector_tradeoff_chart(filtered)
    if tradeoff_fig is not None:
        st.plotly_chart(tradeoff_fig, width="stretch")

    agg = detection_aggregate(filtered)
    best = best_row(filtered)
    weak = weakest_row(filtered)
    cols = st.columns(3)
    with cols[0]:
        value = "n/a" if best is None else f"{labelize(best['algorithm'])}: {fmt(best['f1'])}"
        html_card("Best visible F1", value, "Highest F1+IoU row under current filters")
    with cols[1]:
        value = "n/a" if weak is None else f"{weak['month']}: {fmt(weak['f1'])}"
        html_card("Weakest z-score month", value, "Stress point for repeatability")
    with cols[2]:
        dbscan = filtered[filtered["algorithm"].eq("dbscan")]
        value = fmt(dbscan["f1"].mean()) if not dbscan.empty else "n/a"
        html_card("DBSCAN mean F1", value, "Compact-cluster detector on coarse grids")

    explainer(
        "Held-out mask detection quality across months, sensors, detectors, and drought thresholds.",
        "Stable high F1/IoU and low false-positive rates across thresholds and months.",
        "Z-score is the most usable baseline; DBSCAN often fails on the coarse, broad drought-mask geometry.",
        "That modest mask overlap proves causal groundwater detection or a quantum hardware advantage.",
    )

    st.markdown("**Detector comparison table**")
    if not agg.empty:
        display = agg[
            [
                "threshold",
                "sensor_profile",
                "algorithm",
                "f1_mean",
                "f1_std",
                "iou_mean",
                "false_positive_rate_mean",
                "false_negative_rate_mean",
                "snr_mean",
            ]
        ].rename(
            columns={
                "threshold": "USDM threshold",
                "sensor_profile": "Sensor",
                "algorithm": "Detector",
                "f1_mean": "Mean F1",
                "f1_std": "F1 std",
                "iou_mean": "Mean IoU",
                "false_positive_rate_mean": "Mean FPR",
                "false_negative_rate_mean": "Mean FNR",
                "snr_mean": "Mean SNR",
            }
        )
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "Mean F1": st.column_config.NumberColumn(format="%.3f"),
                "F1 std": st.column_config.NumberColumn(format="%.3f"),
                "Mean IoU": st.column_config.NumberColumn(format="%.3f"),
                "Mean FPR": st.column_config.NumberColumn(format="%.3f"),
                "Mean FNR": st.column_config.NumberColumn(format="%.3f"),
                "Mean SNR": st.column_config.NumberColumn(format="%.3f"),
            },
        )
    month_evidence_cards(output_dir, filtered)
    outcome_artifacts(output_dir, filtered)


def best_month_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for month, month_df in df.groupby("month", sort=True):
        scored = month_df.copy()
        scored["review_score"] = scored["f1"].fillna(0) + scored["iou"].fillna(0)
        rows.append(scored.loc[scored["review_score"].idxmax()])
    return pd.DataFrame(rows)


def month_evidence_cards(output_dir: Path, filtered: pd.DataFrame) -> None:
    st.markdown("**Month-by-month evidence**")
    rows = best_month_rows(filtered)
    if rows.empty:
        st.info("No month-level evidence is available under the current filters.")
        return
    for _, row in rows.iterrows():
        run_dir = resolve_artifact(row["run_dir"], output_dir)
        sensor = str(row["sensor_profile"])
        algorithm = str(row["algorithm"])
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="qse-month-title">
                  <b>{html.escape(str(row['month']))} | USDM D{html.escape(str(row['threshold']))}+ | {html.escape(labelize(algorithm))}</b>
                  <span>{html.escape(labelize(sensor))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            artifacts = [
                ("GRACE anomaly", run_dir / f"{sensor}_measurement.png"),
                ("USDM mask", run_dir / "ground_truth.png"),
                ("Best detector prediction", run_dir / f"{sensor}_{algorithm}_overlay.png"),
            ]
            for col, (caption, path) in zip(cols, artifacts):
                with col:
                    if path.exists():
                        st.image(str(path), caption=caption, width="stretch")
                    else:
                        st.info(f"Missing {caption}: {path.name}")
            st.markdown(
                f"""
                <div class="qse-month-metrics">
                  <div><b>F1</b><span>{fmt(row['f1'])}</span></div>
                  <div><b>IoU</b><span>{fmt(row['iou'])}</span></div>
                  <div><b>FPR</b><span>{fmt(row['false_positive_rate'])}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def outcome_artifacts(output_dir: Path, filtered: pd.DataFrame) -> None:
    best = best_row(filtered)
    if best is None:
        return
    run_dir = resolve_artifact(best["run_dir"], output_dir)
    sensor = str(best["sensor_profile"])
    algorithm = str(best["algorithm"])
    candidates = [
        ("Validation mask", run_dir / "ground_truth.png"),
        ("Sensor measurement", run_dir / f"{sensor}_measurement.png"),
        ("Prediction overlay", run_dir / f"{sensor}_{algorithm}_overlay.png"),
    ]
    with st.expander("Best-row artifact thumbnails", expanded=False):
        cols = st.columns(3)
        for col, (label, path) in zip(cols, candidates):
            with col:
                if path.exists():
                    st.image(str(path), caption=label, width="stretch")
                else:
                    st.info(f"Missing {label}: {path.name}")


def hydrology_chart(metrics: pd.DataFrame, title: str, target_label: str, mode: str) -> Any | None:
    if px is None or metrics.empty:
        return None
    if mode == "error":
        keep = [col for col in ["rmse_cm", "bias_cm"] if col in metrics.columns]
        y_label = "Error / bias (cm EWT)"
        colors = [AMBER, RED]
    else:
        keep = [col for col in ["correlation", "anomaly_sign_agreement", "trend_agreement"] if col in metrics.columns]
        y_label = "Agreement metric (unitless)"
        colors = [BLUE, GREEN, AMBER]
    if not keep:
        return None
    long_df = metrics.melt(id_vars=["month"], value_vars=keep, var_name="metric", value_name="value")
    long_df["metric"] = long_df["metric"].map(labelize)
    fig = px.line(
        long_df,
        x="month",
        y="value",
        color="metric",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=colors,
        labels={"month": "Month", "value": y_label, "metric": target_label},
    )
    fig.update_layout(title=title, height=410, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    if mode == "error":
        fig.add_hline(y=0, line_dash="dash", line_color=MUTED, annotation_text="zero bias", annotation_position="bottom right")
    else:
        fig.update_yaxes(range=[-1, 1])
        fig.add_hline(y=0, line_dash="dash", line_color=MUTED, annotation_text="no relationship", annotation_position="bottom right")
    return fig


def geometry_rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        return coordinates[:1]
    if geometry_type == "MultiPolygon":
        rings: list[list[list[float]]] = []
        for polygon in coordinates:
            if polygon:
                rings.append(polygon[0])
        return rings
    return []


def basin_map_figure(summary: dict[str, Any], summary_table: pd.DataFrame | None = None, color_metric: str | None = None) -> Any | None:
    if go is None:
        return None
    fixture = summary.get("basin_fixture")
    if not fixture:
        return None
    path = Path(fixture)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return None
    payload = read_json(str(path))
    fig = go.Figure()
    metric_by_basin: dict[str, pd.Series] = {}
    vmin = float("nan")
    vmax = float("nan")
    if summary_table is not None and not summary_table.empty and color_metric in summary_table.columns:
        metric_rows = summary_table.drop_duplicates("basin_id").copy()
        metric_by_basin = {str(row["basin_id"]): row for _, row in metric_rows.iterrows()}
        numeric_values = pd.to_numeric(metric_rows[color_metric], errors="coerce").dropna()
        if not numeric_values.empty:
            vmin = float(numeric_values.min())
            vmax = float(numeric_values.max())
            if color_metric and "correlation" in color_metric:
                vmin = min(vmin, -1.0)
                vmax = max(vmax, 1.0)
    all_x: list[float] = []
    all_y: list[float] = []
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {})
        rings = geometry_rings(feature.get("geometry", {}))
        if not rings:
            continue
        name = props.get("name", f"Basin {index + 1}")
        basin_id = str(props.get("basin_id", ""))
        metric_row = metric_by_basin.get(basin_id)
        metric_value = metric_row.get(color_metric) if metric_row is not None and color_metric else None
        fill = value_color(metric_value, vmin, vmax) if color_metric else rgba(BLUE, 0.22)
        hover_lines = [
            f"<b>{html.escape(str(name))}</b>",
            f"Basin ID: {html.escape(basin_id)}",
            f"Target: {html.escape(str(props.get('target_relevance', 'basin_observation')))}",
        ]
        if color_metric and metric_row is not None:
            hover_lines.extend(
                [
                    f"{html.escape(labelize(color_metric))}: {fmt(metric_value)}",
                    f"Valid months: {html.escape(str(metric_row.get('valid_months', metric_row.get('months', 'n/a'))))}",
                    f"Sites: {html.escape(str(metric_row.get('site_count', 'n/a')))}",
                    f"Observations: {html.escape(str(metric_row.get('observation_count', 'n/a')))}",
                ]
            )
        for ring_index, ring in enumerate(rings):
            xs = [point[0] for point in ring]
            ys = [point[1] for point in ring]
            all_x.extend(xs)
            all_y.extend(ys)
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    fill="toself",
                    name=name if ring_index == 0 else f"{name} part {ring_index + 1}",
                    line=dict(color=INK, width=0.8),
                    fillcolor=fill,
                    opacity=0.9,
                    hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
                    showlegend=False,
                )
            )
    if color_metric and not pd.isna(vmin) and not pd.isna(vmax):
        fig.add_trace(
            go.Scatter(
                x=[all_x[0] if all_x else 0],
                y=[all_y[0] if all_y else 0],
                mode="markers",
                marker=dict(
                    color=[vmin],
                    cmin=vmin,
                    cmax=vmax,
                    colorscale=SCIENCE_COLORSCALE,
                    showscale=True,
                    colorbar=dict(title=labelize(color_metric), len=0.72),
                    opacity=0,
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.update_layout(
        title="Central Valley Basin Map Colored By Review Metric" if color_metric else "Named Basin Boundaries",
        template="plotly_white",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        annotations=[
            dict(
                text="Hover a basin for source, metric, observation, and site-count context.",
                xref="paper",
                yref="paper",
                x=0,
                y=1.08,
                showarrow=False,
                xanchor="left",
                font=dict(size=12, color=MUTED),
            )
        ],
    )
    if all_x and all_y:
        pad_x = max((max(all_x) - min(all_x)) * 0.08, 0.5)
        pad_y = max((max(all_y) - min(all_y)) * 0.08, 0.5)
        fig.update_xaxes(range=[min(all_x) - pad_x, max(all_x) + pad_x])
        fig.update_yaxes(range=[min(all_y) - pad_y, max(all_y) + pad_y], scaleanchor="x", scaleratio=1)
    return fig


def basin_time_series(metrics: pd.DataFrame) -> Any | None:
    if px is None or metrics.empty:
        return None
    long_df = metrics.melt(
        id_vars=["month", "basin_name"],
        value_vars=["grace_mean_cm", "gldas_mean_cm", "usdm_drought_coverage_pct"],
        var_name="metric",
        value_name="value",
    )
    long_df["metric"] = long_df["metric"].map(
        {
            "grace_mean_cm": "GRACE mean cm",
            "gldas_mean_cm": "GLDAS mean cm",
            "usdm_drought_coverage_pct": "USDM drought coverage %",
        }
    )
    fig = px.line(
        long_df,
        x="month",
        y="value",
        color="basin_name",
        facet_row="metric",
        markers=True,
        template="plotly_white",
        labels={"month": "Month", "value": "Value (cm EWT or % coverage)", "basin_name": "Basin"},
    )
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=25, b=10), legend_title_text="")
    fig.update_yaxes(matches=None)
    return fig


def basin_validation(output_dir: Path, bundle: dict[str, Any]) -> None:
    metrics = bundle["basin_metrics"]
    summary_table = bundle["basin_summary_table"]
    summary = bundle["basin_summary"]
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Basin scale",
        "Basin Validation",
        "Basin aggregation is the more defensible scale for coarse GRACE/GRACE-FO water-mass signals.",
    )
    if metrics.empty or summary_table.empty:
        st.info("No basin metrics found yet. Rerun the multimonth workflow to generate basin_metrics.csv and basin_summary.csv.")
        return
    thresholds = sorted(metrics["threshold"].dropna().unique().tolist()) if "threshold" in metrics else [1]
    threshold = st.selectbox("Basin drought threshold", thresholds, index=0, format_func=lambda value: f"D{int(value)}+")
    metrics = metrics[metrics["threshold"].eq(threshold)].copy()
    summary_table = summary_table[summary_table["threshold"].eq(threshold)].copy() if "threshold" in summary_table else summary_table
    metric_options = [
        column
        for column in [
            "grace_gldas_correlation",
            "grace_gldas_lag1_correlation",
            "grace_gldas_trend_agreement",
            "grace_usdm_correlation",
            "mean_usdm_drought_coverage_pct",
        ]
        if column in summary_table.columns
    ]
    color_metric = (
        st.selectbox("Basin map color", metric_options, index=0, format_func=labelize)
        if metric_options
        else None
    )

    best = summary_table.sort_values("grace_gldas_correlation", ascending=False, na_position="last").head(1)
    weakest = summary_table.sort_values("grace_gldas_correlation", ascending=True, na_position="last").head(1)
    metric_grid(
        [
            ("Basins", str(summary.get("basins", summary_table["basin_id"].nunique())), "Named basin fixtures"),
            ("Months", str(summary.get("months", metrics["month"].nunique())), "Basin/month rows"),
            ("Best basin corr.", fmt(best["grace_gldas_correlation"].iloc[0]) if not best.empty else "n/a", best["basin_name"].iloc[0] if not best.empty else ""),
            ("Weakest basin corr.", fmt(weakest["grace_gldas_correlation"].iloc[0]) if not weakest.empty else "n/a", weakest["basin_name"].iloc[0] if not weakest.empty else ""),
            ("USDM threshold", f"D{int(threshold)}+", "Basin drought coverage"),
        ]
    )
    verdict(
        "Why this matters",
        "The dashboard now aggregates GRACE, GLDAS, and USDM by named basin fixtures. These are still approximate boundaries, but basin-scale metrics are a more honest validation unit than a single western-U.S. rectangle.",
    )
    if summary.get("limitations"):
        verdict("Boundary quality warning", str(summary["limitations"]), warning=True)

    left, right = st.columns([.9, 1.1])
    with left:
        fig = basin_map_figure(summary, summary_table, color_metric)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    with right:
        fig = basin_time_series(metrics)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")

    explainer(
        "Basin-level GRACE mean anomaly, GLDAS mean anomaly, and USDM drought coverage over time.",
        "A credible basin signal should show stable GRACE/GLDAS correlation and interpretable drought coverage changes.",
        "This converts the project from a rectangular regional proxy into named-basin hydrology validation.",
        "That approximate fixture basins are authoritative groundwater boundaries. They are a workflow bridge.",
    )
    st.markdown("**Basin comparison table**")
    st.dataframe(
        summary_table,
        width="stretch",
        hide_index=True,
        column_config={
            "grace_gldas_correlation": st.column_config.NumberColumn(format="%.3f"),
            "grace_gldas_lag1_correlation": st.column_config.NumberColumn(format="%.3f"),
            "grace_gldas_trend_agreement": st.column_config.NumberColumn(format="%.3f"),
            "grace_usdm_correlation": st.column_config.NumberColumn(format="%.3f"),
            "mean_usdm_drought_coverage_pct": st.column_config.NumberColumn(format="%.1f"),
        },
    )


def groundwater_time_series(metrics: pd.DataFrame, monthly: pd.DataFrame, basin_id: str, threshold: int | None) -> Any | None:
    if px is None or monthly.empty:
        return None
    basin_monthly = monthly[monthly["basin_id"].astype(str).eq(str(basin_id))].copy()
    if basin_monthly.empty:
        return None
    columns = ["groundwater_monthly_mean", "groundwater_level_anomaly"]
    long_df = basin_monthly.melt(id_vars=["month"], value_vars=columns, var_name="metric", value_name="value")
    long_df["metric"] = long_df["metric"].map(
        {
            "groundwater_monthly_mean": "Groundwater raw monthly mean",
            "groundwater_level_anomaly": "Groundwater anomaly",
        }
    )
    fig = px.line(
        long_df,
        x="month",
        y="value",
        color="metric",
        facet_row="metric",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=[GREEN, BLUE],
        labels={"month": "Month", "value": "Groundwater value / anomaly", "metric": ""},
    )
    fig.update_layout(
        title=f"Groundwater observation track for basin {basin_id}" + (f" | D{threshold}+" if threshold else ""),
        height=470,
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="",
    )
    fig.update_yaxes(matches=None)
    return fig


def groundwater_scatter_chart(
    basin_metrics: pd.DataFrame,
    monthly: pd.DataFrame,
    basin_id: str,
    threshold: int | None,
) -> Any | None:
    if px is None or go is None or basin_metrics.empty or monthly.empty:
        return None
    basin_monthly = monthly[monthly["basin_id"].astype(str).eq(str(basin_id))].copy()
    basin_signal = basin_metrics[basin_metrics["basin_id"].astype(str).eq(str(basin_id))].copy()
    if threshold is not None and "threshold" in basin_signal.columns:
        basin_signal = basin_signal[basin_signal["threshold"].eq(threshold)]
    if basin_monthly.empty or basin_signal.empty:
        return None
    joined = pd.merge(
        basin_signal,
        basin_monthly[["basin_id", "month", "groundwater_level_anomaly", "observation_count", "site_count"]],
        on=["basin_id", "month"],
        how="inner",
    )
    joined = joined.dropna(subset=["grace_mean_cm", "groundwater_level_anomaly"])
    if joined.empty:
        return None
    fig = px.scatter(
        joined,
        x="grace_mean_cm",
        y="groundwater_level_anomaly",
        size="observation_count",
        color="month",
        hover_data={
            "month": True,
            "gldas_mean_cm": ":.3f" if "gldas_mean_cm" in joined.columns else False,
            "usdm_drought_coverage_pct": ":.1f" if "usdm_drought_coverage_pct" in joined.columns else False,
            "observation_count": True,
            "site_count": True,
        },
        template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={
            "grace_mean_cm": "GRACE basin mean anomaly (cm EWT)",
            "groundwater_level_anomaly": "Groundwater level anomaly (feet)",
        },
    )
    if len(joined) >= 2 and joined["grace_mean_cm"].nunique() > 1:
        coeff = np.polyfit(joined["grace_mean_cm"], joined["groundwater_level_anomaly"], 1)
        xs = np.linspace(float(joined["grace_mean_cm"].min()), float(joined["grace_mean_cm"].max()), 80)
        ys = coeff[0] * xs + coeff[1]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=INK, width=2, dash="dash"),
                name="linear fit",
                hovertemplate="Linear fit<extra></extra>",
            )
        )
    fig.update_layout(
        title="GRACE Basin Signal Versus Groundwater Anomaly",
        height=430,
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Month",
    )
    fig.add_annotation(
        text="Bubble size = DWR observation count. This is relationship evidence, not discovery proof.",
        xref="paper",
        yref="paper",
        x=0,
        y=1.08,
        showarrow=False,
        xanchor="left",
        font=dict(size=12, color=MUTED),
    )
    return fig


def groundwater_lag_chart(summary_table: pd.DataFrame) -> Any | None:
    if px is None or summary_table.empty:
        return None
    keep = [
        "grace_groundwater_correlation",
        "grace_groundwater_lag1_correlation",
        "grace_groundwater_lag2_correlation",
        "grace_groundwater_trend_agreement",
        "grace_groundwater_sign_agreement",
    ]
    keep = [column for column in keep if column in summary_table.columns]
    if not keep:
        return None
    chart_df = summary_table.copy()
    chart_df["basin_label"] = chart_df["basin_name"].astype(str) + " D" + chart_df["threshold"].astype(str) + "+"
    long_df = chart_df.melt(id_vars=["basin_label"], value_vars=keep, var_name="metric", value_name="value")
    long_df["metric"] = long_df["metric"].map(labelize)
    fig = px.bar(
        long_df,
        x="basin_label",
        y="value",
        color="metric",
        barmode="group",
        template="plotly_white",
        color_discrete_sequence=[BLUE, GREEN, AMBER, RED, "#6b5fb5"],
        labels={"basin_label": "Basin / threshold", "value": "Metric", "metric": ""},
    )
    fig.update_layout(height=470, margin=dict(l=10, r=10, t=25, b=100), legend_title_text="")
    fig.update_xaxes(tickangle=35)
    return fig


def groundwater_validation(output_dir: Path, bundle: dict[str, Any]) -> None:
    summary = bundle["groundwater_summary"]
    observations = bundle["groundwater_observations"]
    monthly = bundle["groundwater_monthly"]
    metrics = bundle["groundwater_metrics"]
    summary_table = bundle["groundwater_summary_table"]
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Primary release target",
        "Groundwater Validation",
        "This section appears only when DWR/USGS well observations have been normalized and joined to basins.",
    )
    if not summary or summary.get("status") == "not_configured":
        st.info("No groundwater observation track is configured for this run. Add DWR Periodic Groundwater Level Measurements or USGS groundwater observations to begin basin-scale groundwater validation.")
        return

    status = str(summary.get("status", "unknown"))
    metric_grid(
        [
            ("Groundwater status", labelize(status), "DWR/USGS well target"),
            ("Observation rows", str(summary.get("observation_rows", len(observations))), "well measurements"),
            ("Basin-month rows", str(summary.get("basin_month_rows", len(monthly))), "aggregated observations"),
            ("Valid basin rows", str(summary.get("valid_basin_threshold_rows", 0)), ">= 3 valid months"),
            ("Insufficient rows", str(summary.get("insufficient_basin_threshold_rows", 0)), "not summarized as strong evidence"),
        ]
    )
    if status == "ok":
        verdict(
            "Groundwater validation has begun",
            "The dashboard found basin/month groundwater observations and computed GRACE-groundwater metrics. This advances the project beyond drought proxies, but it is still validation evidence rather than discovery proof.",
        )
    else:
        verdict(
            "Groundwater coverage warning",
            "Groundwater observations are present, but at least one basin/threshold has fewer than three valid months. Those rows are marked insufficient_months and should not be used as strong evidence.",
            warning=True,
        )
    verdict(
        "Claim boundary",
        "Groundwater discovery is not proven, and quantum advantage is not claimed. This section tests whether basin-scale GRACE/GRACE-FO anomalies move with well observations over time.",
        warning=True,
    )

    if not summary_table.empty:
        display_table = summary_table.copy()
        strongest = display_table[display_table["status"].eq("ok")].sort_values("grace_groundwater_correlation", ascending=False, na_position="last").head(1)
        weakest = display_table[display_table["status"].eq("ok")].sort_values("grace_groundwater_correlation", ascending=True, na_position="last").head(1)
        cols = st.columns(2)
        with cols[0]:
            html_card(
                "Strongest basin",
                strongest["basin_name"].iloc[0] if not strongest.empty else "n/a",
                f"corr {fmt(strongest['grace_groundwater_correlation'].iloc[0])}" if not strongest.empty else "Need >= 3 months",
            )
        with cols[1]:
            html_card(
                "Weakest basin",
                weakest["basin_name"].iloc[0] if not weakest.empty else "n/a",
                f"corr {fmt(weakest['grace_groundwater_correlation'].iloc[0])}" if not weakest.empty else "Need >= 3 months",
            )

    if not monthly.empty:
        basin_options = sorted(monthly["basin_id"].dropna().astype(str).unique().tolist())
        selected_basin = st.selectbox("Groundwater basin", basin_options, index=0)
        threshold = None
        if not metrics.empty and "threshold" in metrics:
            threshold_options = sorted(metrics["threshold"].dropna().unique().tolist())
            threshold = st.selectbox("Groundwater comparison threshold", threshold_options, index=0, format_func=lambda value: f"D{int(value)}+")
        fig = groundwater_time_series(metrics, monthly, selected_basin, int(threshold) if threshold is not None else None)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        scatter_fig = groundwater_scatter_chart(
            bundle["basin_metrics"],
            monthly,
            selected_basin,
            int(threshold) if threshold is not None else None,
        )
        if scatter_fig is not None:
            st.plotly_chart(scatter_fig, width="stretch")

    fig = groundwater_lag_chart(summary_table)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")

    explainer(
        "Basin-level well observations aggregated to monthly groundwater anomalies and compared with GRACE basin means.",
        "At least three valid months per basin plus stable correlation, trend agreement, and sign agreement.",
        "Rows with too few months are labeled insufficient_months so they cannot silently inflate the claim.",
        "That well agreement establishes site-level discovery or quantum sensor superiority.",
    )
    with st.expander("Groundwater tables", expanded=False):
        st.markdown("**Groundwater validation summary**")
        st.dataframe(summary_table, width="stretch", hide_index=True)
        st.markdown("**Groundwater monthly basin observations**")
        st.dataframe(monthly, width="stretch", hide_index=True)
        st.markdown("**Groundwater observation rows**")
        st.dataframe(observations, width="stretch", hide_index=True)


def hydrology_targets(
    output_dir: Path,
    gldas_metrics: pd.DataFrame,
    tws_metrics: pd.DataFrame,
    gldas_summary: dict[str, Any],
    tws_summary: dict[str, Any],
) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "External target",
        "Hydrology Target",
        "GLDAS/TWS metrics test water-storage agreement with units and error separated from unitless correlations.",
    )
    metric_grid(
        [
            ("GLDAS corr.", fmt(gldas_summary.get("mean_correlation")), "External TWS target"),
            ("GLDAS RMSE", fmt(gldas_summary.get("mean_rmse_cm"), suffix=" cm"), "Mean monthly error"),
            ("GLDAS bias", fmt(gldas_summary.get("mean_bias_cm"), suffix=" cm"), "GRACE minus GLDAS"),
            ("Sign agree", fmt(gldas_summary.get("mean_anomaly_sign_agreement")), "Cell anomaly direction"),
            ("CSR/JPL corr.", fmt(tws_summary.get("mean_correlation")), "Processing-center agreement"),
        ]
    )

    left, right = st.columns(2)
    with left:
        fig = hydrology_chart(gldas_metrics, "GRACE vs GLDAS Agreement", "GLDAS", "agreement")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    with right:
        fig = hydrology_chart(tws_metrics, "CSR vs JPL TWS Agreement", "TWS", "agreement")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        fig = hydrology_chart(gldas_metrics, "GRACE vs GLDAS Error", "GLDAS", "error")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    with right:
        fig = hydrology_chart(tws_metrics, "CSR vs JPL TWS Error", "TWS", "error")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")

    explainer(
        "Basin-scale agreement metrics for water-storage-like targets, separate from drought-mask detection.",
        "High correlation, low RMSE/bias, and consistent anomaly direction across months.",
        "The TWS processing-center comparison is strong; GLDAS shows moderate alignment but nontrivial bias/error.",
        "That GLDAS agreement validates groundwater detection. It validates a closer hydrology target than USDM.",
    )

    with st.expander("Hydrology metric tables", expanded=False):
        st.markdown("**GLDAS**")
        st.dataframe(gldas_metrics, width="stretch", hide_index=True)
        st.markdown("**TWS**")
        st.dataframe(tws_metrics, width="stretch", hide_index=True)

    fallback_paths = [output_dir / "gldas_hydrology_comparison.png", output_dir / "tws_comparison.png"]
    with st.expander("Static hydrology artifacts", expanded=False):
        cols = st.columns(2)
        for col, path in zip(cols, fallback_paths):
            with col:
                if path.exists():
                    st.image(str(path), caption=path.name, width="stretch")


def limits_and_next_step(output_dir: Path, bundle: dict[str, Any]) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    section_heading(
        "Reviewer verdict",
        "Limits and Next Step",
        "The dashboard ends by drawing the scientific claim boundary and naming the dataset needed next.",
    )
    st.markdown(
        """
        <div class="qse-final-verdict">
          <h3>Reviewer Verdict</h3>
          <dl>
            <dt>Workflow validation ready?</dt><dd><strong>Yes.</strong> The run is reproducible, artifact-backed, and compares real GRACE-derived rasters with independent drought and hydrology targets.</dd>
            <dt>Groundwater claims ready?</dt><dd><strong>No.</strong> Groundwater validation may be present, but discovery claims require stronger basin/well coverage, interpretation, and sensitivity analysis.</dd>
            <dt>Next required dataset</dt><dd>Longer Central Valley basin well coverage, basin storage observations, or another independent groundwater record aligned over 6-12+ months.</dd>
          </dl>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        verdict(
            "Scientific caveat",
            "The dashboard supports software validation, hydrology comparison, and the beginning of basin-scale groundwater validation when wells are present. It should not be presented as a proven detector for groundwater discovery.",
            warning=True,
        )
    with right:
        verdict(
            "Recommended next experiment",
            "Run the Central Valley workflow over 6-12 recent GRACE-FO months with DWR B118 basins and DWR periodic groundwater wells, then inspect which basins have enough independent observations.",
        )

    paths = [
        output_dir / "timeline_metrics.csv",
        output_dir / "gldas_hydrology_metrics.csv",
        output_dir / "gldas_hydrology_summary.json",
        output_dir / "tws_comparison_metrics.csv",
        output_dir / "tws_comparison_summary.json",
        output_dir / "coverage_summary.json",
        output_dir / "month_alignment.csv",
        output_dir / "groundwater_summary.json",
        output_dir / "groundwater_validation_summary.json",
        output_dir / "groundwater_validation_metrics.csv",
        output_dir / "artifact_manifest.json",
        output_dir / "timeline_report.html",
    ]
    with st.expander("Artifacts and provenance", expanded=False):
        for path in paths:
            status = "present" if path.exists() else "missing"
            st.markdown(f"- **{status}**: <span class='qse-artifact'>{path.resolve()}</span>", unsafe_allow_html=True)
        st.markdown("**GLDAS summary**")
        st.json(bundle["gldas_summary"] or {"status": "missing"})
        st.markdown("**TWS summary**")
        st.json(bundle["tws_summary"] or {"status": "missing"})
        st.markdown("**Groundwater summary**")
        st.json(bundle["groundwater_summary"] or {"status": "missing"})


def main() -> None:
    inject_css()
    args = parse_args()

    with st.sidebar:
        st.title("Review Panel")
        output_text = st.text_input("Output directory", value=args.output)
        output_dir = Path(output_text)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        st.caption("Launch: `python -m streamlit run src/dashboard/app.py -- --output outputs/grace_multimonth_usdm`")

    bundle = load_bundle(output_dir)
    timeline = bundle["timeline"]
    controls = filter_controls(timeline)
    filtered = apply_filters(timeline, controls)

    title_block()
    if timeline.empty:
        st.error(f"No timeline_metrics.csv found in {output_dir}. Generate a multimonth run first.")
        return

    stale_data_warning(timeline)
    coverage_warning(bundle)
    validation_status(
        bundle,
        timeline,
        filtered,
        bundle["gldas_summary"],
        bundle["tws_summary"],
        bundle["groundwater_summary"],
        bundle["basin_summary_table"],
        bundle["groundwater_summary_table"],
    )
    coverage_overview(bundle)
    evidence_trail()
    study_region(output_dir, timeline, controls)
    basin_validation(output_dir, bundle)
    groundwater_validation(output_dir, bundle)
    hydrology_targets(
        output_dir,
        bundle["gldas_metrics"],
        bundle["tws_metrics"],
        bundle["gldas_summary"],
        bundle["tws_summary"],
    )
    detection_results(output_dir, filtered, controls)
    limits_and_next_step(output_dir, bundle)


if __name__ == "__main__":
    main()
