"""
Tests for visualization constants and conventions.
"""

import pytest
from src.components.visualizations import (
    LEGEND_RIGHT_MARGIN,
    LEGEND_BOTTOM_MARGIN,
    HEATMAP_HELP_MARGIN,
    LEGEND_HORIZONTAL_BOTTOM,
    LEGEND_VERTICAL_TOPRIGHT
)


def test_right_margin_constant_exists():
    """Test that right margin constant is defined."""
    assert isinstance(LEGEND_RIGHT_MARGIN, (int, float))
    assert LEGEND_RIGHT_MARGIN >= 180


def test_bottom_margin_constant_exists():
    """Test that bottom margin constant is defined."""
    assert isinstance(LEGEND_BOTTOM_MARGIN, (int, float))
    assert LEGEND_BOTTOM_MARGIN >= 80


def test_heatmap_help_margin_constant_exists():
    """Test that heatmap help annotation margin is defined."""
    assert isinstance(HEATMAP_HELP_MARGIN, (int, float))
    assert HEATMAP_HELP_MARGIN >= 180


def test_horizontal_bottom_legend_config():
    """Test that horizontal bottom legend config is defined."""
    assert isinstance(LEGEND_HORIZONTAL_BOTTOM, dict)
    assert LEGEND_HORIZONTAL_BOTTOM['orientation'] == 'h'
    assert LEGEND_HORIZONTAL_BOTTOM['yanchor'] == 'top'
    assert LEGEND_HORIZONTAL_BOTTOM['y'] < 0


def test_vertical_topright_legend_config():
    """Test that vertical top-right legend config is defined."""
    assert isinstance(LEGEND_VERTICAL_TOPRIGHT, dict)
    assert LEGEND_VERTICAL_TOPRIGHT['orientation'] == 'v'
    assert LEGEND_VERTICAL_TOPRIGHT['xanchor'] == 'right'
    assert LEGEND_VERTICAL_TOPRIGHT['x'] == 0.99
    assert LEGEND_VERTICAL_TOPRIGHT['yanchor'] == 'top'
    assert LEGEND_VERTICAL_TOPRIGHT['y'] == 0.99
