"""
Investigation drill-down navigation helpers (Phase 1, P1-C).

Category → leaf trail for views opened from RHEL Regression charts.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc


def investigation_drill_breadcrumb(benchmark_category: str, test_name: str) -> dbc.Breadcrumb:
    """Breadcrumb: RHEL Regression Analysis → category → benchmark (active)."""
    return dbc.Breadcrumb(
        items=[
            {"label": "RHEL Regression Analysis"},
            {"label": benchmark_category},
            {"label": test_name, "active": True},
        ],
        className="mb-2 bg-transparent py-0",
    )
