# Category Navigation Guide

## Overview

The dashboard provides hierarchical category navigation across multiple sections, enabling users to drill down from high-level benchmark categories to individual test results. This feature includes breadcrumb navigation for easy traversal and context awareness.

### Navigation Levels

1. **Category Level** - Browse benchmarks by category (Networking, Storage/IO, HPC/Compute, System, Other)
2. **Benchmark Level** - View individual benchmark results within a category
3. **Detail Views** - Inline panels and modals with comprehensive analysis

### Supported Sections

- **Competitive Performance**: Category-based comparison with peer operating systems
- **RHEL Regression Analysis**: Category → benchmark investigation drill-down with breadcrumb trail

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

## Category Structure

### Category Mapping

Benchmarks are organized into the following categories:

| Category | Benchmarks |
|----------|-----------|
| **Networking** | uperf |
| **Storage/IO** | fio |
| **HPC/Compute** | streams, specjbb, auto_hpl |
| **System** | sysbench, coremark_pro, pig, coremark, phoronix, passmark |
| **Other** | Any unmapped benchmarks |

Category mappings are defined in **`data/benchmark_categories.json`** and loaded via **`src/benchmark_categories.py`**. To add new benchmarks or adjust groupings:

1. Edit `data/benchmark_categories.json`
2. Add benchmark name tokens to the appropriate category
3. Restart the app to pick up changes

Matching is case-insensitive and uses substring matching (e.g., "CoreMark-Pro" matches "coremark_pro").

### Unmapped Benchmarks

Benchmarks not listed in the category mapping automatically resolve to the **"Other"** category. This is intentional behavior for new or experimental benchmarks that haven't been categorized yet.

## Breadcrumb Navigation

### Competitive Performance Breadcrumbs

Format: **Competitive Performance** → **[Category]**

Example:
```
Competitive Performance → Networking
```

### RHEL Regression Analysis Breadcrumbs

Format: **RHEL Regression Analysis** → **[Category]** → **[Benchmark]**

Example:
```
RHEL Regression Analysis → Storage/IO → fio
```

The breadcrumb trail provides:
- Visual hierarchy of current location
- Context for the data being viewed
- Clear navigation path for users
- Active state indicator on current level

## Technical Implementation

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

## Testing

The category navigation feature has comprehensive test coverage (≥85%):

### Test Suites

1. **`tests/test_benchmark_categories.py`** - Core category mapping and lookup
   - Category resolution (known, unmapped, edge cases)
   - Hierarchy validation
   - Error handling (missing files, invalid JSON, malformed data)
   - Cache behavior
   - Empty and single-benchmark categories

2. **`tests/test_category_navigation.py`** - UI navigation components
   - Breadcrumb structure and styling
   - Active state indicators
   - All category paths
   - Special characters and edge cases

3. **`tests/test_category_navigation_integration.py`** - End-to-end workflows
   - Category browse → leaf view workflow
   - Data filtering by category
   - Category detail panel data flow
   - Cross-category isolation
   - Hierarchy consistency

4. **`tests/test_investigation_nav.py`** - Investigation breadcrumb tests

### Running Tests

```bash
# Run all category navigation tests
pytest tests/test_benchmark_categories.py tests/test_category_navigation.py tests/test_category_navigation_integration.py -v

# Run with coverage
pytest tests/test_benchmark_categories.py --cov=src.benchmark_categories --cov-report=term-missing
```

## Future Enhancements

Potential improvements for future iterations:

- [ ] Add export functionality for category data
- [ ] Include trend analysis over time
- [ ] Add comparison between multiple peer OSes
- [ ] Integrate with JIRA for automatic ticket creation on regressions
- [ ] Dynamic category creation based on test.name patterns
- [ ] Category-level performance trends

