# Quick Start: Simplified RHEL Regression Analysis

## What Changed?

The RHEL regression analysis now shows **three focused comparisons** instead of a complex heatmap:

### 1. Major Release Comparison (9.X vs 10.X)
Compares the latest RHEL 9.X version with the latest RHEL 10.X version.

**Answers:** "Did we regress moving from RHEL 9 to RHEL 10?"

### 2. RHEL 9.X Sequential
Compares the two most recent RHEL 9.X versions (e.g., 9.5 → 9.6).

**Answers:** "Did the latest RHEL 9 minor release introduce regressions?"

### 3. RHEL 10.X Sequential  
Compares the two most recent RHEL 10.X versions (e.g., 10.0 → 10.1).

**Answers:** "Did the latest RHEL 10 minor release introduce regressions?"

## How to Use

1. **Open the Dashboard**
   ```bash
   cd /home/gdumas/src/zaxby
   source venv/bin/activate
   python app.py
   ```
   Navigate to http://127.0.0.1:8050

2. **View the RHEL Version Regression Analysis Section**
   - Located at the top of the dashboard
   - Shows an overall summary with total regressions across all three comparisons

3. **Explore Each Comparison**
   - Each comparison is in a collapsible card
   - Click the section header to expand/collapse
   - Each section shows:
     - **Summary**: Number of regressions and top issues
     - **Bar Chart**: All benchmarks with color-coded performance changes
       - 🔴 Red = Regression (>5% slower)
       - 🟢 Green = Improvement (>5% faster)
       - ⚪ Gray = Stable (within 5%)

4. **Drill Down into Details**
   - Click any bar in the chart to see detailed investigation
   - Shows comparison charts, timelines, and test run details

## Example Output

```
┌─────────────────────────────────────────────────────────┐
│ RHEL Version Regression Analysis                        │
├─────────────────────────────────────────────────────────┤
│ ✓ Overall Summary                                       │
│   Total: 3 regression(s) detected                       │
│   - RHEL 9.6 vs 10.1: 2 regression(s)                   │
│   - RHEL 9.5 vs 9.6: 1 regression(s)                    │
├─────────────────────────────────────────────────────────┤
│ ▼ Compare Latest Major Releases (9.X vs 10.X)          │
│   ⚠ 2 regressions detected                              │
│   • benchmark_cpu_intensive: -8.2%                      │
│   • benchmark_io_throughput: -6.1%                      │
│   [Bar Chart: 15 benchmarks]                            │
├─────────────────────────────────────────────────────────┤
│ ▼ Compare RHEL 9.X Versions (Sequential)               │
│   ⚠ 1 regression detected                               │
│   • benchmark_memory_latency: -5.5%                     │
│   [Bar Chart: 15 benchmarks]                            │
├─────────────────────────────────────────────────────────┤
│ ▼ Compare RHEL 10.X Versions (Sequential)              │
│   ✓ No significant regressions detected                │
│   [Bar Chart: 15 benchmarks]                            │
└─────────────────────────────────────────────────────────┘
```

## Key Features

- **Automatic Version Detection**: Automatically finds the latest versions in your data
- **Focused Comparisons**: Shows only the most relevant version transitions
- **Collapsible Sections**: Hide sections you're not interested in
- **Interactive Charts**: Click to drill down into any benchmark
- **Color-Coded Results**: Easy visual identification of issues
- **Works with Filters**: All advanced filters still apply

## Tips

1. **Use Date Filters**: Narrow down to recent data for faster analysis
2. **Collapse Sections**: If you only care about major releases, collapse the sequential comparisons
3. **Click for Details**: Every bar in the charts is clickable for detailed investigation
4. **Check Overall Summary**: See total impact at a glance

## Technical Notes

- Regression threshold: -5% (configurable in code)
- Requires at least 2 versions in each major release for sequential comparisons
- Gracefully handles missing data (sections won't appear if insufficient versions)
- All DataFrames are properly serialized for storage and callbacks

