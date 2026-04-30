"""
Pulse v1 executive KPI panel — charts and layout for the recommended core metrics.

Metrics: total runs, reporting window, activity trend, category mix, plus scope footnote.
See docs/guides/IMPLEMENTATION_PLAN.md Phase 2 (Pulse). Aggregations are descriptive
only (no cross-cohort performance comparisons).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import plotly.graph_objects as go
from dash import dcc, html

from src.query_service import (
    ActivityTimelineSnapshot,
    CategoryKpiSnapshot,
    PulseScopeFootnote,
    ResultsOverviewSnapshot,
    format_pulse_scope_footnote,
)


def _empty_figure(title: str, message: str, *, height: int = 220) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color="#64748b"),
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        template="plotly_white",
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def figure_pulse_activity_timeline(
    timeline: ActivityTimelineSnapshot,
    *,
    title: str = "Activity trend (runs per month)",
    height: int = 240,
) -> go.Figure:
    """Line chart of monthly run counts; suitable as a compact Pulse sparkline-style view."""
    if timeline.error:
        return _empty_figure(title, timeline.error, height=height)
    if not timeline.by_month:
        return _empty_figure(title, "No monthly activity data", height=height)

    labels = [p[0] for p in timeline.by_month]
    counts = [p[1] for p in timeline.by_month]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=counts,
            mode="lines+markers",
            line=dict(color="#1d4ed8", width=2),
            marker=dict(size=6, color="#1d4ed8"),
            hovertemplate="%{x}<br>Runs: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        template="plotly_white",
        height=height,
        margin=dict(l=50, r=20, t=50, b=80),
        xaxis=dict(title="Month", tickangle=-45),
        yaxis=dict(title="Runs"),
        showlegend=False,
    )
    return fig


def figure_pulse_category_mix(
    cat: CategoryKpiSnapshot,
    *,
    title: str = "Mix by benchmark category",
    max_categories: int = 12,
    height: int = 280,
) -> go.Figure:
    """Horizontal bar chart of document counts rolled up to dashboard categories."""
    if cat.error:
        return _empty_figure(title, cat.error, height=height)
    if not cat.by_category:
        return _empty_figure(title, "No category breakdown", height=height)

    pairs: List[Tuple[str, int]] = list(cat.by_category[: max(1, int(max_categories))])
    pairs.sort(key=lambda x: (-x[1], x[0]))
    labels = [p[0] for p in pairs]
    counts = [p[1] for p in pairs]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker=dict(color="#0e7490"),
            hovertemplate="%{y}<br>Documents: %{x:,}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        template="plotly_white",
        height=height,
        margin=dict(l=140, r=20, t=50, b=40),
        xaxis=dict(title="Documents"),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    return fig


def _pulse_disclaimer() -> html.P:
    return html.P(
        [
            "Counts are run-level documents in the results index. ",
            "They describe coverage and collection activity, not performance rankings or regressions. ",
            "Use Detailed analyses below for comparisons.",
        ],
        className="text-muted small mb-0",
    )


def render_pulse_v1_panel(
    *,
    snap: ResultsOverviewSnapshot,
    scope_snap: PulseScopeFootnote,
    cat_snap: CategoryKpiSnapshot,
    timeline_snap: ActivityTimelineSnapshot,
    data_mode: str,
    results_index_label: str,
    kpi_definition_version: Optional[str] = None,
    policy_template_id: Optional[str] = None,
) -> html.Div:
    """
    Build the Pulse v1 panel: KPI cards, two charts, footnote and disclaimer.

    Args:
        results_index_label: Human-readable index name for the footnote (may be empty).
        kpi_definition_version: When set with ``policy_template_id``, appends the PULSE_KPIS.md catalog line.
        policy_template_id: Comparison-policy anchor used for the KPI bundle (e.g. TPL_CATEGORY_ROLLUP).
    """
    def _warn(msg: str, err: str) -> html.Div:
        return html.Div(
            [msg, html.Code(err)],
            className="alert alert-warning mb-2 py-2",
            role="alert",
        )

    alerts: List = []
    if snap.error:
        alerts.append(_warn("Results overview failed: ", snap.error))
    if scope_snap.error:
        alerts.append(_warn("Reporting window metadata failed: ", scope_snap.error))
    if cat_snap.error:
        alerts.append(_warn("Category mix failed: ", cat_snap.error))
    if timeline_snap.error:
        alerts.append(_warn("Activity timeline failed: ", timeline_snap.error))

    total_display = "—"
    if not snap.error and snap.total is not None:
        total_display = f"{snap.total:,}"

    dmin = scope_snap.run_date_min_utc
    dmax = scope_snap.run_date_max_utc
    if scope_snap.error:
        window_primary = "Unavailable"
        window_sub = ""
    elif dmin and dmax:
        window_primary = f"{dmin} to {dmax} (UTC)" if dmin != dmax else f"{dmin} (UTC)"
        window_sub = (
            f"{scope_snap.document_count:,} runs with timestamps"
            if scope_snap.document_count is not None
            else ""
        )
    elif dmin:
        window_primary = f"From {dmin} (UTC)"
        window_sub = ""
    else:
        window_primary = "No run timestamps in scope"
        window_sub = ""

    fig_timeline = figure_pulse_activity_timeline(timeline_snap)
    fig_category = figure_pulse_category_mix(cat_snap)

    mode_label = (data_mode or "").strip().lower() or "unknown"
    idx_part = results_index_label.strip() if results_index_label.strip() else "(index not set)"
    source_line = html.P(
        [
            html.Strong("Data: "),
            f"mode={mode_label}",
            " · ",
            f"results index: {idx_part}",
        ],
        className="small text-muted mb-1",
    )

    scope_line = format_pulse_scope_footnote(scope_snap, data_mode=data_mode)
    scope_el = (
        html.P(scope_line, className="small text-muted mb-2")
        if scope_line
        else html.Div()
    )

    badge_cls = "bg-info" if mode_label == "opensearch" else "bg-secondary"
    children: List = [
        *alerts,
        html.Div(
            [
                html.Div(
                    html.Div(
                        html.Div(
                            [
                                html.P("Total benchmark runs", className="text-muted small mb-1"),
                                html.H3(total_display, className="mb-0 text-primary"),
                                html.P(
                                    html.Span(
                                        f"Source: {snap.source}",
                                        className=f"badge {badge_cls} mt-2",
                                    ),
                                    className="mb-0",
                                ),
                            ],
                            className="card-body",
                        ),
                        className="card h-100 border-primary",
                    ),
                    className="col-md-6",
                ),
                html.Div(
                    html.Div(
                        html.Div(
                            [
                                html.P("Reporting window", className="text-muted small mb-1"),
                                html.H5(window_primary, className="mb-1"),
                                *(
                                    [html.P(window_sub, className="small text-muted mb-0")]
                                    if window_sub
                                    else []
                                ),
                            ],
                            className="card-body",
                        ),
                        className="card h-100",
                    ),
                    className="col-md-6",
                ),
            ],
            className="row g-3 mb-3",
        ),
        html.Div(
            [
                html.Div(
                    dcc.Graph(figure=fig_timeline, config={"displayModeBar": False}),
                    className="col-md-6",
                ),
                html.Div(
                    dcc.Graph(figure=fig_category, config={"displayModeBar": False}),
                    className="col-md-6",
                ),
            ],
            className="row g-3 mb-2",
        ),
        html.Hr(className="my-2"),
        source_line,
        scope_el,
        _pulse_disclaimer(),
    ]
    if kpi_definition_version is not None and policy_template_id is not None:
        children.append(
            html.P(
                html.Small(
                    f"Pulse KPI bundle v{kpi_definition_version} · policy anchor {policy_template_id}. "
                    "Definitions: docs/guides/PULSE_KPIS.md (metric semantics and exec-facing copy are subject to review).",
                    className="text-muted",
                ),
                className="mb-0 mt-3 pt-2 border-top small",
            )
        )
    return html.Div(children)
