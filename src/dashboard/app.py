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
    return read_csv(str(path)) if path.exists() else pd.DataFrame()


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
            border-bottom: 1px solid var(--qse-border);
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
            border-top: 1px solid var(--qse-border);
            padding-top: 1.25rem;
            margin-top: 1.55rem;
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
            grid-template-columns: repeat(5, minmax(150px, 1fr));
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
            .qse-method, .qse-readiness, .qse-explain, .qse-metric-grid, .qse-detector-grid, .qse-month-metrics {
                grid-template-columns: 1fr;
            }
            .qse-final-verdict dl {
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
        "gldas_metrics": maybe_csv(output_dir / "gldas_hydrology_metrics.csv"),
        "tws_metrics": maybe_csv(output_dir / "tws_comparison_metrics.csv"),
        "basin_metrics": maybe_csv(output_dir / "basin_metrics.csv"),
        "basin_summary_table": maybe_csv(output_dir / "basin_summary.csv"),
        "gldas_summary": maybe_json(output_dir / "gldas_hydrology_summary.json"),
        "tws_summary": maybe_json(output_dir / "tws_comparison_summary.json"),
        "basin_summary": maybe_json(output_dir / "basin_summary.json"),
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


def target_types(gldas_summary: dict[str, Any], tws_summary: dict[str, Any]) -> str:
    values = ["drought proxy"]
    if tws_summary.get("target_type"):
        values.append("GRACE TWS")
    if gldas_summary.get("status") == "ok":
        values.append("external hydrology")
    return " + ".join(values)


def scientific_readiness(gldas_summary: dict[str, Any]) -> tuple[str, str]:
    if gldas_summary.get("status") == "ok":
        return "Level 4", "External hydrology target reached"
    return "Level 3", "Real raster plus independent drought proxy"


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


def coverage_warning(bundle: dict[str, Any]) -> None:
    timeline = bundle["timeline"]
    detection_months = ok_months(timeline)
    gldas_months = ok_months(bundle["gldas_metrics"])
    tws_months = ok_months(bundle["tws_metrics"])
    if not detection_months:
        return
    missing_gldas = sorted(detection_months - gldas_months)
    missing_tws = sorted(detection_months - tws_months)
    if not missing_gldas and not missing_tws:
        return
    gldas_coverage = bundle["gldas_summary"].get("coverage") or f"{len(gldas_months)}/{len(detection_months)}"
    tws_coverage = bundle["tws_summary"].get("coverage") or f"{len(tws_months)}/{len(detection_months)}"
    details = []
    if missing_gldas:
        details.append(f"GLDAS missing: {', '.join(missing_gldas)}")
    if missing_tws:
        details.append(f"TWS missing: {', '.join(missing_tws)}")
    st.markdown(
        f"""
        <div class="qse-coverage-warning">
          <b>Hydrology coverage is incomplete for this run.</b>
          Detection months: <strong>{len(detection_months)}</strong>.
          GLDAS coverage: <strong>{html.escape(str(gldas_coverage))}</strong>.
          TWS coverage: <strong>{html.escape(str(tws_coverage))}</strong>.
          {'; '.join(html.escape(item) for item in details)}.
          Treat hydrology metrics as partial evidence until all detector months have matching hydrology targets.
        </div>
        """,
        unsafe_allow_html=True,
    )


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
          <h1>Can gravity-derived water-mass signals align with independent drought and hydrology targets?</h1>
          <p>
            This dashboard reviews a GRACE-FO hydrology validation run against named western basins,
            USDM drought masks, GLDAS terrestrial water storage, and GRACE processing-center agreement.
            Quantum-inspired sensor simulation is kept as one comparison layer, while the main scientific
            question is whether basin-scale water-mass signals are credible and repeatable.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def readiness_ladder(gldas_summary: dict[str, Any]) -> None:
    reached_gldas = gldas_summary.get("status") == "ok"
    steps = [
        ("1. Synthetic", "Metrics and pipeline plumbing.", True, False),
        ("2. Real raster", "GRACE GeoTIFFs with metadata.", True, False),
        ("3. Drought proxy", "Independent USDM masks.", True, not reached_gldas),
        ("4. Hydrology target", "GLDAS/TWS comparison.", reached_gldas, reached_gldas),
        ("5. Groundwater", "Needs wells or basin studies.", False, False),
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
    timeline: pd.DataFrame,
    filtered: pd.DataFrame,
    gldas_summary: dict[str, Any],
    tws_summary: dict[str, Any],
) -> None:
    level, level_note = scientific_readiness(gldas_summary)
    best = best_row(filtered)
    weak = weakest_row(filtered)
    months = timeline["month"].nunique() if not timeline.empty else 0
    best_text = "n/a"
    if best is not None:
        best_text = f"{labelize(best['algorithm'])}, F1 {fmt(best['f1'])}"
    weak_text = "n/a"
    if weak is not None:
        weak_text = f"{weak['month']} D{weak['threshold']}+, F1 {fmt(weak['f1'])}"

    metric_grid(
        [
            ("Validation status", level, level_note),
            ("Months tested", str(months), "GRACE/USDM monthly folds"),
            ("Targets", target_types(gldas_summary, tws_summary), "Mask and hydrology evidence"),
            ("Strongest result", best_text, "Best visible detector row"),
            ("Weakest point", weak_text, "Low-performing z-score month"),
        ]
    )

    left, right = st.columns([1.25, 1])
    with left:
        verdict(
            "Current conclusion",
            "The project now demonstrates a reproducible validation workflow on real GRACE-derived rasters with independent drought labels and an external hydrology target. The detector agreement is modest, but the data pipeline is inspectable and repeatable.",
        )
    with right:
        verdict(
            "Boundary of the claim",
            "This does not prove groundwater discovery or quantum sensor superiority. USDM is a drought proxy, GLDAS is model-assimilated hydrology, and the next credible target is basin or groundwater observations.",
            warning=True,
        )
    readiness_ladder(gldas_summary)


def evidence_trail() -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    st.subheader("Evidence Trail")
    st.markdown(
        """
        <div class="qse-method">
          <div class="qse-method-step"><b>1. GRACE raster</b><span>Monthly water-mass anomaly grids are cropped to a western U.S. study region.</span></div>
          <div class="qse-method-step"><b>2. Independent mask</b><span>USDM drought classes are rasterized onto the GRACE grid as D1+, D2+, and D3+ proxy labels.</span></div>
          <div class="qse-method-step"><b>3. Detector run</b><span>Classical and quantum-inspired sensor profiles feed z-score, DBSCAN, and isolation forest detectors.</span></div>
          <div class="qse-method-step"><b>4. Hydrology check</b><span>GLDAS and JPL/CSR TWS comparisons ask whether basin-scale water storage moves consistently.</span></div>
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
    st.subheader("Study Region")
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

    array = grid["array"]
    mask_array = np.where(mask["array"] > 0, 1.0, np.nan)
    left, bottom, right, top = grid["bounds"]
    x = np.linspace(left, right, array.shape[1])
    y = np.linspace(top, bottom, array.shape[0])

    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            z=array,
            x=x,
            y=y,
            colorscale="RdBu",
            zmid=0,
            colorbar=dict(title="cm EWT"),
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
    fig.update_layout(
        title=f"{month} Western U.S. GRACE Crop With USDM D{threshold}+ Mask",
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
        text="Western U.S. validation crop",
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
    return fig


def detection_chart(df: pd.DataFrame, metric: str) -> Any | None:
    if px is None or df.empty:
        return None
    chart_df = df.copy()
    chart_df["Detector"] = chart_df["algorithm"].map(labelize)
    chart_df["Sensor"] = chart_df["sensor_profile"].map(labelize)
    chart_df["USDM"] = "D" + chart_df["threshold"].astype(str) + "+"
    chart_df["Series"] = chart_df["USDM"] + " | " + chart_df["Sensor"] + " | " + chart_df["Detector"]
    colors = {
        "Z Score": BLUE,
        "Dbscan": AMBER,
        "Isolation Forest": GREEN,
    }
    fig = px.line(
        chart_df,
        x="month",
        y=metric,
        color="Detector",
        line_dash="USDM",
        facet_row="Sensor",
        markers=True,
        color_discrete_map=colors,
        labels={"month": "Month", metric: labelize(metric)},
        template="plotly_white",
    )
    fig.update_layout(height=540, margin=dict(l=10, r=10, t=35, b=10), legend_title_text="Detector")
    fig.update_yaxes(rangemode="tozero")
    return fig


def detection_results(output_dir: Path, filtered: pd.DataFrame, controls: dict[str, Any]) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    st.subheader("Detection Results")
    detector_story_panel()
    metric = controls.get("metric", "f1")
    fig = detection_chart(filtered, metric)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.dataframe(filtered, width="stretch", hide_index=True)

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


def hydrology_chart(metrics: pd.DataFrame, title: str, target_label: str) -> Any | None:
    if px is None or metrics.empty:
        return None
    keep = [col for col in ["correlation", "anomaly_sign_agreement", "rmse_cm", "bias_cm"] if col in metrics.columns]
    long_df = metrics.melt(id_vars=["month"], value_vars=keep, var_name="metric", value_name="value")
    long_df["metric"] = long_df["metric"].map(labelize)
    fig = px.line(
        long_df,
        x="month",
        y="value",
        color="metric",
        markers=True,
        template="plotly_white",
        color_discrete_sequence=[BLUE, GREEN, AMBER, RED],
        labels={"month": "Month", "value": "Metric value", "metric": target_label},
    )
    fig.update_layout(title=title, height=410, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="")
    return fig


def basin_map_figure(summary: dict[str, Any]) -> Any | None:
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
    colors = [BLUE, GREEN, AMBER, RED, "#6b5fb5"]
    for index, feature in enumerate(payload.get("features", [])):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        if not coords:
            continue
        ring = coords[0]
        xs = [point[0] for point in ring]
        ys = [point[1] for point in ring]
        name = props.get("name", f"Basin {index + 1}")
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                fill="toself",
                name=name,
                line=dict(color=colors[index % len(colors)], width=2),
                fillcolor=colors[index % len(colors)].replace("#", "rgba(") if False else None,
                opacity=.42,
                hovertemplate=f"{name}<br>{props.get('target_relevance', 'basin_observation')}<extra></extra>",
            )
        )
    fig.update_layout(
        title="Named Basin Fixtures Over Western U.S. Crop",
        template="plotly_white",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        legend_title_text="Basin",
    )
    fig.update_xaxes(range=[-125, -102])
    fig.update_yaxes(range=[31, 49], scaleanchor="x", scaleratio=1)
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
        line_dash="metric",
        markers=True,
        template="plotly_white",
        labels={"month": "Month", "value": "Value", "basin_name": "Basin"},
    )
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=25, b=10), legend_title_text="")
    return fig


def basin_validation(output_dir: Path, bundle: dict[str, Any]) -> None:
    metrics = bundle["basin_metrics"]
    summary_table = bundle["basin_summary_table"]
    summary = bundle["basin_summary"]
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    st.subheader("Basin Validation")
    if metrics.empty or summary_table.empty:
        st.info("No basin metrics found yet. Rerun the multimonth workflow to generate basin_metrics.csv and basin_summary.csv.")
        return
    thresholds = sorted(metrics["threshold"].dropna().unique().tolist()) if "threshold" in metrics else [1]
    threshold = st.selectbox("Basin drought threshold", thresholds, index=0, format_func=lambda value: f"D{int(value)}+")
    metrics = metrics[metrics["threshold"].eq(threshold)].copy()
    summary_table = summary_table[summary_table["threshold"].eq(threshold)].copy() if "threshold" in summary_table else summary_table

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
        fig = basin_map_figure(summary)
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


def hydrology_targets(
    output_dir: Path,
    gldas_metrics: pd.DataFrame,
    tws_metrics: pd.DataFrame,
    gldas_summary: dict[str, Any],
    tws_summary: dict[str, Any],
) -> None:
    st.markdown("<div class='qse-section'></div>", unsafe_allow_html=True)
    st.subheader("Hydrology Target")
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
        fig = hydrology_chart(gldas_metrics, "GRACE vs GLDAS Hydrology Agreement", "GLDAS")
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    with right:
        fig = hydrology_chart(tws_metrics, "CSR vs JPL GRACE TWS Agreement", "TWS")
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
    st.subheader("Limits and Next Step")
    st.markdown(
        """
        <div class="qse-final-verdict">
          <h3>Reviewer Verdict</h3>
          <dl>
            <dt>Workflow validation ready?</dt><dd><strong>Yes.</strong> The run is reproducible, artifact-backed, and compares real GRACE-derived rasters with independent drought and hydrology targets.</dd>
            <dt>Groundwater claims ready?</dt><dd><strong>No.</strong> USDM and GLDAS are useful validation targets, but they are not direct groundwater truth.</dd>
            <dt>Next required dataset</dt><dd>Basin storage observations, groundwater wells, or another independent groundwater/hydrology record aligned over multiple months.</dd>
          </dl>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        verdict(
            "Scientific caveat",
            "The dashboard supports software validation and early hydrology comparison. It should not be presented as a proven detector for groundwater discovery until basin observations or groundwater wells are evaluated.",
            warning=True,
        )
    with right:
        verdict(
            "Recommended next experiment",
            "Move from drought proxies to basin-scale groundwater or storage observations over more months. Keep the same artifact contract so the dashboard can compare USDM, GLDAS, TWS, and basin observations side by side.",
        )

    paths = [
        output_dir / "timeline_metrics.csv",
        output_dir / "gldas_hydrology_metrics.csv",
        output_dir / "gldas_hydrology_summary.json",
        output_dir / "tws_comparison_metrics.csv",
        output_dir / "tws_comparison_summary.json",
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
    validation_status(timeline, filtered, bundle["gldas_summary"], bundle["tws_summary"])
    evidence_trail()
    study_region(output_dir, timeline, controls)
    basin_validation(output_dir, bundle)
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
