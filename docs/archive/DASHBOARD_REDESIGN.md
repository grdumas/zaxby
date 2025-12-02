# Dashboard Redesign Documentation

## Overview

The Performance Engineering Dashboard has been redesigned to provide a cleaner, more intuitive interface that directly answers three critical questions for Red Hat's Performance Engineering Department.

## Design Philosophy: "Answer First, Details on Demand"

Instead of presenting users with cluttered visualizations and ambiguous insights, the new dashboard prioritizes clarity by:

1. **Answering three key questions upfront** on the landing page
2. **Providing executive-friendly summaries** with visual indicators
3. **Enabling drill-down investigations** when issues are detected
4. **Organizing benchmarks by category** to solve scale mismatch issues

## The Three Key Questions

### Question 1: Did RHEL regress between OS versions?

**Visualization**: Heatmap showing percentage changes between OS version transitions

- **Green cells**: Performance improvements or stable performance
- **Red cells**: Performance regressions (>5% drop)
- **Gray cells**: Minimal change (±5%)
- **Clickable**: Click any cell to drill into detailed investigation

**Summary Text**: Shows number of regressions detected and highlights the top 3 most significant ones.

### Question 2: Is RHEL performing competitively with peer OSes?

**Visualization**: Grouped bar chart comparing RHEL against Ubuntu, SLES, and other peer operating systems

- Benchmarks are grouped by category (Networking, Storage/IO, HPC/Compute, System)
- Bars show relative performance (RHEL = 100% baseline)
- Green zone (90-110%) indicates competitive range
- Color coding shows performance status

**Summary Text**: Reports how many benchmarks RHEL is competitive in, and flags areas where peers significantly outperform.

### Question 3: How does RHEL scale across cloud instance classes?

**Visualization**: Line chart showing performance scaling across instance sizes

- User selects cloud provider (AWS, Azure, GCP) and OS version
- Shows performance vs. CPU cores or instance type
- Includes ideal linear scaling reference line
- Multiple lines for different benchmark categories

**Summary Text**: Indicates how many benchmarks show good linear scaling, and flags workloads with diminishing returns.

## New Features

### 1. Benchmark Categorization

Benchmarks are now grouped into logical categories:

- **Networking**: uperf
- **Storage/IO**: fio (Flexible I/O Tester)
- **HPC/Compute**: streams, specjbb, auto_hpl
- **System**: sysbench, coremark_pro, pig, coremark, phoronix, passmark

This solves the scale mismatch problem where different benchmarks have vastly different metric ranges (e.g., uperf at 140k vs. pig at 120).

### 2. Investigation Drill-Down

When a regression is detected:

1. Click on the red cell in the Question 1 heatmap
2. Navigate to a detailed investigation view showing:
   - Side-by-side box plot comparison
   - Time series trend showing when regression occurred
   - Detailed table of test runs with metadata
   - Summary statistics and percentage changes

3. Use the "Back to Overview" button to return to the main dashboard

### 3. Simplified Filtering

**Default View**: Minimal controls - just a date range picker

**Advanced Filters**: Collapse panel with full multi-axis filtering:
- OS versions (multi-select)
- Instance types (multi-select)
- Benchmark types (multi-select)
- Cloud providers (multi-select)
- Test status (PASS/FAIL/UNKNOWN)

This keeps the interface clean for managers while providing power users access to detailed controls.

### 4. Status Icons and Color Coding

- ✅ **Green/Success**: No issues detected, performance is stable or improved
- ⚠️ **Yellow/Warning**: Minor issues detected (1-2 regressions)
- 🔴 **Red/Danger**: Significant issues detected (3+ regressions)

## File Changes

### New Files

1. **`src/components/summaries.py`**: Text summary generation functions
2. **`app_old_backup.py`**: Backup of the previous dashboard version
3. **`DASHBOARD_REDESIGN.md`**: This documentation

### Modified Files

1. **`app.py`**: Complete restructure with three-question layout
   - New overview layout with three question cards
   - Investigation drill-down view
   - Navigation state management
   - Analysis callbacks for all three questions

2. **`src/data_processing.py`**: Added analysis functions
   - `BENCHMARK_GROUPS`: Category definitions
   - `get_benchmark_category()`: Categorize benchmarks
   - `add_benchmark_categories()`: Add category column to DataFrame
   - `analyze_os_version_regressions()`: Detect regressions between OS versions
   - `analyze_peer_os_comparison()`: Compare RHEL vs peer OSes
   - `analyze_cloud_scaling()`: Analyze scaling across instance sizes

3. **`src/components/visualizations.py`**: New visualization functions
   - `create_regression_heatmap()`: Heatmap with color-coded percentage changes
   - `create_peer_os_comparison_chart()`: Grouped bar chart for OS comparison
   - `create_cloud_scaling_chart()`: Line chart with linear scaling reference
   - `create_investigation_detail_chart()`: Detailed comparison for drill-down

4. **`assets/style.css`**: Enhanced styling
   - Card hover effects
   - Alert/summary styling with left border
   - Animation for filter collapse
   - Improved responsive design
   - Investigation view styles

## Usage Guide

### For Managers/Executives

1. **Open the dashboard** - The landing page immediately shows three question cards
2. **Read the summaries** - Each card has a text summary with status icons
3. **Scan the visualizations** - Green = good, Red = issues
4. **Export/share** - Take screenshots of any cards for reports

### For Engineers

1. **Use advanced filters** - Click "Advanced Filters" to narrow down data
2. **Investigate regressions** - Click on red heatmap cells to drill into details
3. **Compare configurations** - Use Question 3 dropdowns to analyze different setups
4. **Access raw data** - Investigation view shows detailed test run tables
5. **Track trends** - Time series charts show performance over time

### For Partners

Same as managers - the default view is designed for non-technical stakeholders who need high-level insights.

## Technical Architecture

### Data Flow

```
Raw Data (OpenSearch/Synthetic)
    ↓
BenchmarkDataProcessor.documents_to_dataframe()
    ↓
Filter Panel → update_filtered_data() → filtered-data-store
    ↓
analyze_filtered_data() → analysis-results-store
    ↓
    ├─→ update_question1() → Q1 Heatmap + Summary
    ├─→ update_question2() → Q2 Comparison + Summary
    └─→ update_question3() → Q3 Scaling + Summary

Navigation:
    Heatmap Click → navigation-state → update_investigation_view()
```

### State Management

The dashboard uses three Dash `dcc.Store` components:

1. **`filtered-data-store`**: Holds the filtered DataFrame as JSON
2. **`analysis-results-store`**: Holds pre-computed analysis results for all three questions
3. **`navigation-state`**: Tracks current view (overview vs investigation) and parameters

This approach minimizes server round-trips and improves performance.

## Performance Optimizations

1. **Pre-computed analyses**: All three questions are analyzed once when filters change
2. **Client-side caching**: Filtered data stored in browser memory
3. **Lazy loading**: Investigation view only loads when accessed
4. **Efficient pivots**: Heatmap uses pandas pivot_table for speed
5. **Data serialization**: DataFrames converted to JSON for transfer

## Testing

To verify the redesign:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the dashboard
python app.py

# Visit http://127.0.0.1:8050 in your browser
```

### Test Scenarios

1. **Default view**: Should show three question cards with heatmap, bar chart, and line chart
2. **Filter by OS version**: Select specific RHEL versions, summaries should update
3. **Click heatmap cell**: Should navigate to investigation view
4. **Back button**: Should return to overview
5. **Question 3 dropdowns**: Change cloud provider and OS version, chart should update
6. **Advanced filters**: Toggle should show/hide filter panel

## Comparison: Old vs New

### Old Dashboard Problems

❌ Cluttered with 3+ charts on Overview tab
❌ Scale mismatches (uperf 140k vs pig 120 on same chart)
❌ Unclear purpose - what am I looking at?
❌ Heavy filter sidebar always visible
❌ No clear path to investigate issues
❌ Mixed benchmark types with no grouping

### New Dashboard Solutions

✅ Three focused question cards
✅ Benchmarks grouped by category (solves scale issues)
✅ Clear purpose - answers three specific questions
✅ Minimal controls by default, advanced filters hidden
✅ Click-to-investigate drill-down
✅ Logical benchmark categorization

## Future Enhancements

Potential additions for future iterations:

1. **Export functionality**: Download reports as PDF
2. **Email alerts**: Notify when regressions detected
3. **Historical comparisons**: Compare current results to N days ago
4. **Benchmark search**: Quick search/filter for specific tests
5. **Custom question templates**: Allow users to save their own queries
6. **Annotations**: Add notes to specific data points
7. **Multi-compare**: Compare 3+ OS versions side-by-side

## Rollback Instructions

If you need to revert to the old dashboard:

```bash
# Restore old version
mv app.py app_redesigned.py
mv app_old_backup.py app.py

# Restart the server
python app.py
```

The old dashboard code is preserved in `app_old_backup.py`.

## Support and Feedback

For questions or issues with the redesign:

1. Check this documentation first
2. Review the inline code comments in `app.py`
3. Test with synthetic data (default mode) before OpenSearch
4. Check browser console for any JavaScript errors

## Summary

The redesigned dashboard transforms a cluttered, confusing interface into a clean, purpose-driven tool that:

- **Answers three key questions** that matter to Performance Engineering
- **Serves both managers and engineers** with appropriate detail levels
- **Solves technical issues** like benchmark scale mismatches
- **Enables investigation** when problems are detected
- **Maintains flexibility** through advanced filtering

The result is a professional, intuitive dashboard that earns user trust and provides actionable insights.

