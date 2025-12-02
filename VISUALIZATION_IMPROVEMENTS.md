# Visualization Improvements for Multi-Scale Benchmarks

## Problem

The dashboard displayed benchmark results with vastly different scales on the same charts, making them unreadable:

- coremark: ~500,000
- coremark_pro: ~44,000  
- passmark: ~370,000
- streams: ~130,000
- auto_hpl: ~1,700
- uperf: ~10
- phoronix: ~10,000,000

When plotted together, smaller-scale benchmarks (like uperf with values around 10) become invisible, while larger-scale benchmarks (like phoronix with values in the millions) dominate the visualization.

## Solutions Implemented

### 1. Faceted Charts (Primary Solution)

**Box Plots and Time Series**: When multiple benchmark types are present, the visualizations now use Plotly's faceting feature to create separate subplots with **independent y-axes** for each benchmark type.

- Each benchmark gets its own subplot
- Y-axis scales independently based on that benchmark's data range
- All benchmarks are now clearly visible and comparable within their own scale

**Usage**:
```python
fig = create_box_plot(df, x_col='test_name', y_col='primary_metric_value', use_facets=True)
fig = create_time_series_chart(df, x_col='timestamp', y_col='primary_metric_value', color_col='test_name', use_facets=True)
```

### 2. Normalized Heatmaps

**Heatmaps**: When multiple benchmark types are present, heatmaps now normalize values within each benchmark type, showing performance as a percentage of the mean for that benchmark.

- Values are normalized to percentage of mean (100 = average performance)
- Higher percentages (e.g., 110%) indicate better than average
- Lower percentages (e.g., 90%) indicate worse than average
- Makes cross-benchmark comparisons meaningful

**Usage**:
```python
fig = create_heatmap(df, row_dim='os_version', col_dim='instance_type', value_col='primary_metric_value', normalize_by_test=True)
```

### 3. New "By Benchmark" Tab

Added a dedicated tab that shows separate, focused charts for each benchmark type:

- Individual box plots for each benchmark by OS version
- Individual box plots for each benchmark by instance type
- Each chart uses its own optimal scale
- Ideal for detailed analysis of specific benchmarks

## Dashboard Changes

### Updated Tabs

1. **Overview**: Uses faceted charts when multiple benchmark types are present
2. **By Benchmark** (NEW): Shows separate charts for each benchmark type
3. **Comparisons**: Unchanged (already handles comparisons properly)
4. **Time Series**: Uses faceted charts when multiple benchmark types are present
5. **Heatmap**: Uses normalized values when multiple benchmark types are present
6. **Detailed Table**: Unchanged

### Automatic Behavior

The dashboard automatically detects when multiple benchmark types with different scales are present and applies the appropriate visualization strategy:

- If only one benchmark type is selected via filters → standard single-scale charts
- If multiple benchmark types are present → faceted/normalized charts

## Technical Details

### Modified Functions

**visualizations.py**:
- `create_box_plot()`: Added `use_facets` parameter
- `create_time_series_chart()`: Added `use_facets` parameter  
- `create_heatmap()`: Added `normalize_by_test` parameter
- `create_separate_test_charts()`: New function to generate individual charts per benchmark

**app.py**:
- Updated all tab rendering to detect multiple test types
- Applied appropriate visualization strategies based on data
- Added new "By Benchmark" tab

## Benefits

1. **Readability**: All benchmarks are now clearly visible regardless of scale
2. **Flexibility**: Users can choose between combined views (Overview) or separate views (By Benchmark)
3. **Automatic**: No manual configuration needed - dashboard adapts to the data
4. **Backward Compatible**: Still works perfectly with single benchmark type selections

## Usage Tips

- Use **Overview** tab for a quick glance at all benchmarks together
- Use **By Benchmark** tab for detailed analysis of individual benchmarks
- Use **filters** to focus on specific benchmark types if you want standard single-scale charts
- Heatmap percentages make it easy to spot performance outliers across different benchmarks

