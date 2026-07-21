"""
Centralized color palettes for dashboard visualizations.

Provides STANDARD and COLORBLIND palette sets. All chart functions
should reference these palettes rather than hardcoding hex values.

The COLORBLIND palette follows Wong (2011) and IBM Design colorblind-safe
guidelines to ensure accessibility for users with deuteranopia and protanopia
(red-green color vision deficiency affecting ~8% of males).
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Union


@dataclass(frozen=True)
class SemanticColors:
    """Colors for regression/improvement semantic encoding."""

    regression: str  # All configs regressed
    mixed_regression: str  # Mixed results, net regression
    stable: str  # Within threshold
    mixed_improvement: str  # Mixed results, net improvement
    improvement: str  # All configs improved
    moderate_difference: str  # Moderate (80-120% range)
    undefined: str  # Missing/NaN data


@dataclass(frozen=True)
class ComparisonColors:
    """Colors for baseline vs comparison pair."""

    baseline: str
    comparison: str


@dataclass(frozen=True)
class TableColors:
    """Colors for table header and cells."""

    header: str
    cells: str


@dataclass(frozen=True)
class BrandingColors:
    """Single-series branding colors."""

    pulse_line: str  # pulse activity timeline
    pulse_bar: str  # pulse category mix
    nightly: str  # nightly run charts


@dataclass(frozen=True)
class DivergingScale:
    """Plotly-format diverging colorscale."""

    scale: List[Tuple[float, str]]


@dataclass(frozen=True)
class ChartPatterns:
    """Pattern shapes for redundant encoding beyond color."""

    regression: str  # e.g., 'x'
    mixed_regression: str  # e.g., '/'
    stable: str  # e.g., ''
    mixed_improvement: str  # e.g., '/'
    improvement: str  # e.g., ''
    # Marker symbols for scatter/line charts
    marker_symbols: List[str] = field(
        default_factory=lambda: [
            "circle",
            "square",
            "diamond",
            "triangle-up",
            "star",
            "hexagon",
        ]
    )
    # Line dash styles for time series
    line_dashes: List[str] = field(
        default_factory=lambda: ["solid", "dash", "dot", "dashdot", "longdash"]
    )


@dataclass(frozen=True)
class Palette:
    """Complete color palette for the dashboard."""

    name: str
    semantic: SemanticColors
    comparison: ComparisonColors
    table: TableColors
    branding: BrandingColors
    regression_heatmap_scale: DivergingScale
    performance_heatmap_scale: Union[str, DivergingScale]  # Named Plotly scale or DivergingScale
    hardware_heatmap_scale: DivergingScale
    patterns: ChartPatterns


# ============================================================================
# STANDARD PALETTE (current colors - uses red-green for regression/improvement)
# ============================================================================

STANDARD = Palette(
    name="standard",
    semantic=SemanticColors(
        regression="#d73027",  # Red (problematic for colorblind)
        mixed_regression="#f46d43",  # Orange
        stable="#9ca3af",  # Medium gray
        mixed_improvement="#fdae61",  # Amber
        improvement="#1a9850",  # Green (problematic for colorblind)
        moderate_difference="#d97706",  # Amber
        undefined="#bdbdbd",  # Gray
    ),
    comparison=ComparisonColors(
        baseline="lightblue",  # CSS named color
        comparison="lightcoral",  # CSS named color
    ),
    table=TableColors(
        header="paleturquoise",  # CSS named color
        cells="lavender",  # CSS named color
    ),
    branding=BrandingColors(
        pulse_line="#1d4ed8",  # Blue (already safe)
        pulse_bar="#0e7490",  # Teal (already safe)
        nightly="#7c3aed",  # Purple (already safe)
    ),
    regression_heatmap_scale=DivergingScale(
        scale=[
            (0.0, "#d73027"),  # Strong regression (red)
            (0.3, "#fc8d59"),  # Moderate regression (orange)
            (0.5, "#ffffbf"),  # Neutral (light yellow)
            (0.7, "#91cf60"),  # Moderate improvement (light green)
            (1.0, "#1a9850"),  # Strong improvement (green)
        ]
    ),
    performance_heatmap_scale="RdYlGn",  # Plotly built-in (red-yellow-green)
    hardware_heatmap_scale=DivergingScale(
        scale=[
            (0.0, "#d73027"),  # Red
            (0.3, "#fc8d59"),  # Orange
            (0.5, "#ffffbf"),  # Light yellow (baseline)
            (0.7, "#91cf60"),  # Green
            (1.0, "#1a9850"),  # Dark green
        ]
    ),
    patterns=ChartPatterns(
        regression="",  # No pattern in standard mode
        mixed_regression="/",  # Striped (existing pattern)
        stable="",  # No pattern
        mixed_improvement="/",  # Striped (existing pattern)
        improvement="",  # No pattern in standard mode
    ),
)


# ============================================================================
# COLORBLIND PALETTE (Wong/IBM colorblind-safe - uses blue-orange divergence)
# ============================================================================

COLORBLIND = Palette(
    name="colorblind",
    semantic=SemanticColors(
        regression="#d55e00",  # Vermillion (safe)
        mixed_regression="#e69f00",  # Amber/gold (safe)
        stable="#9ca3af",  # Medium gray (achromatic, always safe)
        mixed_improvement="#56b4e9",  # Sky blue (safe)
        improvement="#0072b2",  # Strong blue (safe, replaces green)
        moderate_difference="#e69f00",  # Amber (safe)
        undefined="#bdbdbd",  # Gray (achromatic, always safe)
    ),
    comparison=ComparisonColors(
        baseline="#56b4e9",  # Sky blue (safe)
        comparison="#e69f00",  # Amber (safe)
    ),
    table=TableColors(
        header="#c7e3f0",  # Steel blue (safe)
        cells="#f0e6d3",  # Warm cream (safe)
    ),
    branding=BrandingColors(
        pulse_line="#1d4ed8",  # Blue (already safe, no change needed)
        pulse_bar="#0e7490",  # Teal (already safe, no change needed)
        nightly="#7c3aed",  # Purple (already safe, no change needed)
    ),
    regression_heatmap_scale=DivergingScale(
        scale=[
            (0.0, "#d55e00"),  # Strong regression (vermillion)
            (0.3, "#f0ad4e"),  # Moderate regression (amber)
            (0.5, "#f0f0f0"),  # Neutral (light gray)
            (0.7, "#56b4e9"),  # Moderate improvement (sky blue)
            (1.0, "#0072b2"),  # Strong improvement (blue)
        ]
    ),
    performance_heatmap_scale=DivergingScale(
        scale=[
            (0.0, "#0072b2"),  # Blue (improvement)
            (0.3, "#56b4e9"),  # Light blue
            (0.5, "#f0f0f0"),  # Neutral gray
            (0.7, "#e69f00"),  # Amber
            (1.0, "#d55e00"),  # Vermillion (regression)
        ]
    ),
    hardware_heatmap_scale=DivergingScale(
        scale=[
            (0.0, "#d55e00"),  # Vermillion (regression)
            (0.3, "#f0ad4e"),  # Amber
            (0.5, "#f0f0f0"),  # Light gray (baseline)
            (0.7, "#56b4e9"),  # Sky blue
            (1.0, "#0072b2"),  # Strong blue (improvement)
        ]
    ),
    patterns=ChartPatterns(
        regression="x",  # X pattern for redundancy
        mixed_regression="/",  # Striped
        stable="",  # No pattern (stable is neutral)
        mixed_improvement="/",  # Striped
        improvement="+",  # Plus pattern for redundancy
    ),
)


def get_palette(colorblind_mode: bool = False) -> Palette:
    """
    Return the active palette based on mode.

    Args:
        colorblind_mode: If True, return colorblind-safe palette

    Returns:
        COLORBLIND palette if colorblind_mode=True, otherwise STANDARD
    """
    return COLORBLIND if colorblind_mode else STANDARD
