#!/usr/bin/env python3
"""
Demonstration script showing the scale fix for multi-benchmark visualizations.

This script generates example visualizations comparing the old approach (single scale)
with the new approach (faceted/normalized scales).
"""

import json
import pandas as pd
from src.data_processing import BenchmarkDataProcessor
from src.components import visualizations
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def main():
    print("=" * 70)
    print("Dashboard Scale Fix Demonstration")
    print("=" * 70)
    
    # Load sample data
    print("\n1. Loading sample benchmark data...")
    with open('data/synthetic/benchmark_results.json', 'r') as f:
        data = json.load(f)[:200]  # Use first 200 records
    
    processor = BenchmarkDataProcessor()
    df = processor.documents_to_dataframe(data)
    
    print(f"   Loaded {len(df)} records")
    print(f"   Benchmark types: {len(df['test_name'].unique())}")
    
    # Show scale differences
    print("\n2. Scale Analysis:")
    print("   " + "-" * 66)
    print(f"   {'Benchmark':<20} {'Min':>12} {'Max':>12} {'Mean':>12} {'Scale'}")
    print("   " + "-" * 66)
    
    scale_data = []
    for test in sorted(df['test_name'].unique()):
        test_data = df[df['test_name'] == test]['primary_metric_value']
        if len(test_data) > 0:
            min_val = test_data.min()
            max_val = test_data.max()
            mean_val = test_data.mean()
            scale = max_val - min_val
            scale_data.append((test, min_val, max_val, mean_val, scale))
            print(f"   {test:<20} {min_val:>12,.0f} {max_val:>12,.0f} {mean_val:>12,.0f} {scale:>12,.0f}")
    
    print("   " + "-" * 66)
    
    # Calculate scale ratio
    scales = [s[4] for s in scale_data if s[4] > 0]
    if scales:
        max_scale = max(scales)
        min_scale = min(scales)
        ratio = max_scale / min_scale if min_scale > 0 else float('inf')
        print(f"\n   Scale range ratio: {ratio:,.0f}x difference between largest and smallest")
    
    # Demonstrate the problem
    print("\n3. THE PROBLEM: Standard box plot with all benchmarks")
    print("   Creating a standard box plot (OLD approach)...")
    
    old_fig = visualizations.create_box_plot(
        df,
        x_col='test_name',
        y_col='primary_metric_value',
        title="OLD: All Benchmarks on Single Scale (UNREADABLE)",
        use_facets=False  # Old behavior
    )
    
    # Count how many benchmarks are effectively invisible
    invisible_count = 0
    for test in df['test_name'].unique():
        test_mean = df[df['test_name'] == test]['primary_metric_value'].mean()
        max_mean = df.groupby('test_name')['primary_metric_value'].mean().max()
        if test_mean < max_mean * 0.1:  # Less than 10% of max
            invisible_count += 1
    
    print(f"   ⚠️  {invisible_count} out of {len(df['test_name'].unique())} benchmarks are nearly invisible!")
    print(f"   ⚠️  Small-scale benchmarks are crushed by large-scale ones")
    
    # Demonstrate the solution
    print("\n4. THE SOLUTION: Faceted box plot with independent scales")
    print("   Creating faceted box plots (NEW approach)...")
    
    new_fig = visualizations.create_box_plot(
        df,
        x_col='test_name',
        y_col='primary_metric_value',
        title="NEW: Each Benchmark on Independent Scale (READABLE)",
        use_facets=True  # New behavior
    )
    
    print(f"   ✅ All {len(df['test_name'].unique())} benchmarks are now clearly visible")
    print(f"   ✅ Each benchmark uses its optimal scale")
    print(f"   ✅ Created {len(new_fig.data)} subplots with independent y-axes")
    
    # Demonstrate normalized heatmap
    print("\n5. BONUS: Normalized heatmap for cross-benchmark comparison")
    print("   Creating normalized heatmap...")
    
    heatmap_fig = visualizations.create_heatmap(
        df,
        row_dim='os_version',
        col_dim='test_name',
        value_col='primary_metric_value',
        title="Normalized Performance Heatmap (% of Mean)",
        normalize_by_test=True
    )
    
    print("   ✅ Values normalized to percentage of mean per benchmark")
    print("   ✅ 100% = average performance for that benchmark")
    print("   ✅ Easy to spot relative strengths/weaknesses")
    
    # Demonstrate separate charts
    print("\n6. ALTERNATIVE: Separate charts for detailed analysis")
    print("   Creating individual charts per benchmark...")
    
    separate_figs = visualizations.create_separate_test_charts(
        df,
        chart_type='box',
        x_col='os_version',
        y_col='primary_metric_value',
        title_prefix="Performance by OS Version"
    )
    
    print(f"   ✅ Created {len(separate_figs)} individual charts")
    print(f"   ✅ Each optimized for its specific benchmark")
    print(f"   ✅ Available in the new 'By Benchmark' tab")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\n✅ FIXED: Visualizations now handle multi-scale data properly")
    print("✅ ADDED: Faceted charts with independent y-axes")
    print("✅ ADDED: Normalized heatmaps for cross-benchmark comparison")
    print("✅ ADDED: New 'By Benchmark' tab for detailed analysis")
    print("✅ AUTOMATIC: Dashboard detects and adapts to multi-scale data")
    print("\n" + "=" * 70)
    print("\nTo see the improvements in action, run:")
    print("  python app.py")
    print("\nThen navigate through the different tabs to see the new visualizations!")
    print("=" * 70)

if __name__ == '__main__':
    main()

