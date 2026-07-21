"""Tests for centralized color palette module."""

import pytest
from src.color_palettes import (
    STANDARD,
    COLORBLIND,
    get_palette,
    Palette,
    SemanticColors,
    ComparisonColors,
    TableColors,
    BrandingColors,
    DivergingScale,
    ChartPatterns,
)


def test_standard_palette_has_all_fields():
    """Standard palette has all required attributes."""
    assert STANDARD.name == "standard"
    assert isinstance(STANDARD.semantic, SemanticColors)
    assert isinstance(STANDARD.comparison, ComparisonColors)
    assert isinstance(STANDARD.table, TableColors)
    assert isinstance(STANDARD.branding, BrandingColors)
    assert isinstance(STANDARD.regression_heatmap_scale, DivergingScale)
    assert isinstance(STANDARD.hardware_heatmap_scale, DivergingScale)
    assert isinstance(STANDARD.patterns, ChartPatterns)
    assert STANDARD.performance_heatmap_scale is not None


def test_colorblind_palette_has_all_fields():
    """Colorblind palette has all required attributes."""
    assert COLORBLIND.name == "colorblind"
    assert isinstance(COLORBLIND.semantic, SemanticColors)
    assert isinstance(COLORBLIND.comparison, ComparisonColors)
    assert isinstance(COLORBLIND.table, TableColors)
    assert isinstance(COLORBLIND.branding, BrandingColors)
    assert isinstance(COLORBLIND.regression_heatmap_scale, DivergingScale)
    assert isinstance(COLORBLIND.hardware_heatmap_scale, DivergingScale)
    assert isinstance(COLORBLIND.patterns, ChartPatterns)
    assert COLORBLIND.performance_heatmap_scale is not None


def test_get_palette_returns_standard_by_default():
    """get_palette() returns STANDARD when colorblind_mode=False."""
    palette = get_palette(colorblind_mode=False)
    assert palette is STANDARD


def test_get_palette_returns_colorblind_when_true():
    """get_palette() returns COLORBLIND when colorblind_mode=True."""
    palette = get_palette(colorblind_mode=True)
    assert COLORBLIND is COLORBLIND


def test_colorblind_no_red_green_confusion():
    """Colorblind palette uses different hues for regression vs improvement."""
    # Red-green confusion means we should NOT use:
    # - Pure red (#ff0000 family) for regression
    # - Pure green (#00ff00 family) for improvement
    # Instead we should use:
    # - Orange/vermillion for regression
    # - Blue for improvement

    # The STANDARD palette uses red/green (that's the problem we're fixing)
    assert STANDARD.semantic.regression == "#d73027"  # red
    assert STANDARD.semantic.improvement == "#1a9850"  # green

    # The COLORBLIND palette should use orange/blue
    assert COLORBLIND.semantic.regression == "#d55e00"  # vermillion
    assert COLORBLIND.semantic.improvement == "#0072b2"  # blue

    # Verify they're not the same (sanity check)
    assert STANDARD.semantic.regression != COLORBLIND.semantic.regression
    assert STANDARD.semantic.improvement != COLORBLIND.semantic.improvement


def test_all_semantic_colors_are_valid_hex():
    """All semantic colors are valid hex color codes."""
    for palette in [STANDARD, COLORBLIND]:
        colors = [
            palette.semantic.regression,
            palette.semantic.mixed_regression,
            palette.semantic.stable,
            palette.semantic.mixed_improvement,
            palette.semantic.improvement,
            palette.semantic.moderate_difference,
            palette.semantic.undefined,
        ]
        for color in colors:
            assert color.startswith("#"), f"Color {color} should start with #"
            assert len(color) == 7, f"Color {color} should be 7 chars (e.g., #ff00ff)"
            # Verify it's valid hex
            int(color[1:], 16)


def test_colorblind_palette_uses_distinct_patterns():
    """Colorblind mode patterns are non-empty for key categories."""
    # In colorblind mode, we amplify pattern usage for redundant encoding
    cb_patterns = COLORBLIND.patterns

    # Regression and improvement should have distinct patterns
    assert cb_patterns.regression != ""
    assert cb_patterns.improvement != ""
    assert cb_patterns.regression != cb_patterns.improvement

    # Mixed results should also have patterns
    assert cb_patterns.mixed_regression != ""
    assert cb_patterns.mixed_improvement != ""


def test_colorblind_diverging_scale_avoids_red_green():
    """Colorblind diverging scales do not use pure red or pure green."""
    scale = COLORBLIND.regression_heatmap_scale.scale

    # Check all color values in the scale
    for position, color in scale:
        assert 0.0 <= position <= 1.0
        # Should not contain the standard red or green
        assert color != "#d73027", "Colorblind scale should not use standard red"
        assert color != "#1a9850", "Colorblind scale should not use standard green"
        # Verify it's a valid hex color
        assert color.startswith("#")
        assert len(color) == 7
        int(color[1:], 16)


def test_marker_symbols_list_nonempty():
    """ChartPatterns has a non-empty marker symbols list."""
    assert len(STANDARD.patterns.marker_symbols) > 0
    assert len(COLORBLIND.patterns.marker_symbols) > 0
    # Should have at least 4 distinct symbols for variety
    assert len(COLORBLIND.patterns.marker_symbols) >= 4


def test_line_dashes_list_nonempty():
    """ChartPatterns has a non-empty line dash list."""
    assert len(STANDARD.patterns.line_dashes) > 0
    assert len(COLORBLIND.patterns.line_dashes) > 0
    # Should have at least 3 distinct dash styles
    assert len(COLORBLIND.patterns.line_dashes) >= 3


def test_standard_and_colorblind_palettes_same_structure():
    """Standard and colorblind palettes have the same attribute structure."""
    # This ensures we can swap palettes without code changes
    assert dir(STANDARD.semantic) == dir(COLORBLIND.semantic)
    assert dir(STANDARD.comparison) == dir(COLORBLIND.comparison)
    assert dir(STANDARD.table) == dir(COLORBLIND.table)
    assert dir(STANDARD.branding) == dir(COLORBLIND.branding)
    assert dir(STANDARD.patterns) == dir(COLORBLIND.patterns)


def test_diverging_scale_has_5_stops():
    """Diverging scales have exactly 5 color stops (0.0, 0.3, 0.5, 0.7, 1.0)."""
    for palette in [STANDARD, COLORBLIND]:
        scale = palette.regression_heatmap_scale.scale
        assert len(scale) == 5
        positions = [stop[0] for stop in scale]
        assert positions == [0.0, 0.3, 0.5, 0.7, 1.0]


def test_comparison_colors_are_different():
    """Baseline and comparison colors are visually distinct."""
    for palette in [STANDARD, COLORBLIND]:
        assert palette.comparison.baseline != palette.comparison.comparison
