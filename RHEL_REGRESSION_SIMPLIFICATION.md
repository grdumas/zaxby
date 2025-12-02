# RHEL Regression Analysis Simplification

## Summary
Simplified the RHEL version regression analysis from a complex heatmap showing all version-to-version comparisons to three focused, collapsible comparisons that answer specific questions.

## Changes Made

### 1. New Analysis Method (`src/data_processing.py`)

Added `analyze_rhel_simplified_regressions()` method that provides three specific comparisons:

1. **Major Release Comparison**: Latest 9.X vs Latest 10.X
   - Compares the most recent RHEL 9.X version with the most recent RHEL 10.X version
   - Helps answer: "Did we regress moving from RHEL 9 to RHEL 10?"

2. **RHEL 9.X Sequential**: Latest 9.X vs Previous 9.X
   - Compares the two most recent RHEL 9.X versions (e.g., 9.5 vs 9.6)
   - Helps answer: "Did the latest RHEL 9 update introduce regressions?"

3. **RHEL 10.X Sequential**: Latest 10.X vs Previous 10.X
   - Compares the two most recent RHEL 10.X versions (e.g., 10.0 vs 10.1)
   - Helps answer: "Did the latest RHEL 10 update introduce regressions?"

Added helper method `_compare_two_versions()` that performs the detailed comparison between any two OS versions.

**IMPORTANT: Hardware-Aware Comparisons**
- Comparisons only include tests that ran on **identical hardware** (same cloud_provider + instance_type)
- This ensures valid apples-to-apples comparisons
- Hardware configuration details are tracked and displayed in summaries and visualizations
- See `HARDWARE_FILTERING_UPDATE.md` for complete details

### 2. New Visualization (`src/components/visualizations.py`)

Added `create_version_comparison_bar_chart()` function:
- Creates horizontal bar charts showing percent change for each benchmark
- Color-coded bars:
  - **Red**: Regressions (> 5% performance decrease)
  - **Green**: Improvements (> 5% performance increase)
  - **Gray**: Stable (within 5%)
- Displays actual values and percent change in hover tooltips
- Sorted by percent change (regressions appear first)

### 3. Updated Dashboard UI (`app.py`)

**New Layout Components:**
- `create_comparison_collapse()`: Reusable function to create collapsible comparison sections
- Each comparison has its own:
  - Collapsible card with toggle button
  - Summary section showing number of regressions and top issues
  - Bar chart visualization
  - All sections start expanded but can be collapsed individually

**New Callbacks:**
- `toggle_major_release()`: Toggle major release comparison section
- `toggle_rhel9_seq()`: Toggle RHEL 9 sequential comparison section
- `toggle_rhel10_seq()`: Toggle RHEL 10 sequential comparison section
- `update_q1_overall_summary()`: Shows overall summary across all three comparisons
- `update_major_release_comparison()`: Renders major release comparison
- `update_rhel9_sequential()`: Renders RHEL 9 sequential comparison
- `update_rhel10_sequential()`: Renders RHEL 10 sequential comparison

**Updated Navigation:**
- Modified `handle_navigation()` to handle clicks on all three bar charts
- Clicking any bar drills into investigation view for that specific benchmark

### 4. Data Serialization Updates

Updated `analyze_filtered_data()` callback to properly serialize the new comparison structure:
- Serializes comparison_data DataFrame for each of the three comparisons
- Maintains proper JSON structure for storage

## Benefits

1. **Clearer Focus**: Instead of showing all possible version transitions, focuses on the most relevant comparisons
2. **Better Organization**: Three collapsible sections make it easy to find specific information
3. **Improved Readability**: Bar charts are more intuitive than heatmaps for this type of comparison
4. **Preserved Functionality**: Clicking on any benchmark still drills into detailed investigation view
5. **Flexible Display**: Users can collapse sections they're not interested in

## Usage

When you open the dashboard:
1. The overall summary shows total regressions across all three comparisons
2. Each section is initially expanded showing:
   - Number of regressions detected
   - Top regression details
   - Bar chart with all benchmarks
3. Click the section headers to collapse/expand individual comparisons
4. Click any bar to drill into detailed investigation for that benchmark

## Example Output

```
Overall Summary: Total: 3 regression(s) detected
- RHEL 9.6 vs 10.1: 2 regression(s)
- RHEL 9.5 vs 9.6: 1 regression(s)

[Compare Latest Major Releases (9.X vs 10.X)] ▼
  Summary: 2 regressions detected
  • benchmark_cpu_intensive: -8.2%
  • benchmark_io_throughput: -6.1%
  [Bar Chart showing all benchmarks]

[Compare RHEL 9.X Versions (Sequential)] ▼
  Summary: 1 regression detected
  • benchmark_memory_latency: -5.5%
  [Bar Chart showing all benchmarks]

[Compare RHEL 10.X Versions (Sequential)] ▼
  Summary: No significant regressions detected
  [Bar Chart showing all benchmarks]
```

## Technical Notes

- The method automatically detects available versions and picks the latest ones
- Returns None for comparisons where insufficient versions exist
- Gracefully handles missing data
- Maintains backward compatibility with investigation drill-down views
- All three comparisons use the same regression threshold (default: -5%)

## Files Modified

1. `src/data_processing.py` - Added new analysis methods
2. `src/components/visualizations.py` - Added bar chart visualization
3. `app.py` - Updated layout and callbacks for new comparison structure

