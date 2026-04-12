# Competitive Performance Category Drill-Down Guide

## Overview

The Competitive Performance section now supports interactive drill-down functionality, allowing users to explore individual benchmarks within each category. This feature provides two levels of detail:

1. **Inline Detail Panel** - Quick summary and benchmark chart (click a category bar)
2. **Full Modal Analysis** - Deep-dive with hardware matrix and raw data (click "Full Details")

## User Guide

### Accessing Category Details

1. Navigate to the **Competitive Performance** section on the dashboard
2. Click on any category bar in the chart (e.g., "Networking", "Storage/IO", "HPC/Compute", "System")
3. An inline detail panel will expand below the chart

### Inline Detail Panel

The inline panel shows:

- **Summary Statistics**:
  - Number of benchmarks in the category
  - Number of hardware configurations tested
  - Average relative performance
  - Competitive rate (percentage of tests where RHEL is competitive)

- **Benchmark Detail Chart**: Horizontal bar chart showing each benchmark's performance relative to RHEL baseline (100%)

### Full Modal Analysis

Click the **"Full Details"** button to open a comprehensive modal with three tabs:

1. **Benchmark Breakdown**: Same horizontal bar chart as inline panel, but larger
2. **Hardware Matrix**: Heatmap showing benchmark × hardware performance matrix
3. **Raw Data**: Sortable table with all comparison data points

## Technical Implementation

Category names and benchmark tokens are defined in **`data/benchmark_categories.json`** and loaded via **`src/benchmark_categories.py`** (Phase 1, P1-C). Edit the JSON to add benchmarks or adjust groupings; restart the app to pick up changes.

### New Components Added

#### Layout (`app.py`)

```python
# Inline detail panel (hidden by default)
html.Div(
    id='q2-category-detail-container',
    children=[...],
    style={"display": "none"}
)

# Modal for deep-dive analysis
dbc.Modal([...], id="q2-category-modal", size="xl")

# Store for selected category data
dcc.Store(id='q2-selected-category-store')
```

#### Callbacks (`app.py`)

| Callback | Purpose |
|----------|---------|
| `handle_category_click` | Handles bar click, shows inline panel |
| `toggle_category_modal` | Opens/closes the modal dialog |
| `update_modal_tab_content` | Populates modal tabs based on selection |

#### Visualizations (`src/components/visualizations.py`)

| Function | Purpose |
|----------|---------|
| `create_category_benchmark_detail_chart()` | Horizontal bar chart for individual benchmarks |
| `create_category_hardware_heatmap()` | Benchmark × hardware performance matrix |

### Data Flow

```
User clicks category bar
        ↓
handle_category_click callback
        ↓
Filters comparison_data to selected category
        ↓
Stores category data in q2-selected-category-store
        ↓
Renders inline panel with summary + chart
        ↓
(Optional) User clicks "Full Details"
        ↓
toggle_category_modal opens modal
        ↓
update_modal_tab_content populates tabs
```

## Color Coding

Performance colors are consistent across all views:

| Color | Relative Performance | Meaning |
|-------|---------------------|---------|
| 🟢 Green (#1a9850) | 90-110% | Competitive |
| 🟡 Amber (#d97706) | 80-120% | Moderate difference |
| 🔴 Red (#d73027) | <80% or >120% | Significant difference |

## Keyboard Navigation

- **Escape**: Closes the modal
- **Tab**: Navigate between modal elements

## Accessibility

- All interactive elements have proper ARIA labels
- Color coding is supplemented with text indicators (✅, ⚠️, ❌)
- Modal is scrollable for long content

## Troubleshooting

### Panel doesn't appear after clicking

1. Ensure the Competitive Performance section has data
2. Check browser console for JavaScript errors
3. Verify filters haven't excluded all comparison data

### Modal shows "No data available"

1. The category may have been filtered out between click and modal open
2. Try clicking the category bar again to refresh the data

## Future Enhancements

Potential improvements for future iterations:

- [ ] Add export functionality for category data
- [ ] Include trend analysis over time
- [ ] Add comparison between multiple peer OSes
- [ ] Integrate with JIRA for automatic ticket creation on regressions

