# Hardware-Aware Comparisons - Quick Reference

## Why It Matters

**❌ INVALID:** Comparing RHEL 9.5 on AWS c5.2xlarge vs RHEL 9.6 on Azure Standard_D4
- Hardware differences dominate the results
- Leads to false conclusions about OS performance

**✅ VALID:** Comparing RHEL 9.5 on AWS c5.2xlarge vs RHEL 9.6 on AWS c5.2xlarge
- Same hardware, only OS version differs
- Isolates OS performance impact

## How It Works

### Automatic Hardware Matching
```
For each benchmark test:
1. Find all hardware configs in baseline version (9.5)
2. Find all hardware configs in comparison version (9.6)
3. Only compare on hardware that exists in BOTH versions
4. Create separate comparison for each matching config
```

### Example Scenario

**Available Data:**
```
benchmark_cpu, RHEL 9.5, aws/c5.2xlarge    → 100 ops/sec
benchmark_cpu, RHEL 9.6, aws/c5.2xlarge    → 95 ops/sec  ✓ Match!
benchmark_cpu, RHEL 9.5, azure/Standard_D4 → 110 ops/sec
benchmark_cpu, RHEL 9.6, azure/Standard_D4 → 100 ops/sec ✓ Match!
benchmark_cpu, RHEL 9.5, gcp/n2-standard-4 → 120 ops/sec
benchmark_cpu, RHEL 9.6, aws/c5.4xlarge    → 180 ops/sec ✗ No match
```

**Results:**
```
✓ 2 comparisons created:
  • benchmark_cpu on aws/c5.2xlarge: -5.0% regression
  • benchmark_cpu on azure/Standard_D4: -9.1% regression
  • Average shown in chart: -7.05%

✗ GCP n2-standard-4 excluded (no 9.6 data on this hardware)
✗ AWS c5.4xlarge excluded (no 9.5 data on this hardware)
```

## What You'll See

### In Summary Cards
```
⚠ 2 regressions detected
45 test×hardware comparison(s) | Compared on 3 hardware
configuration(s): aws/c5.2xlarge, azure/Standard_D4, gcp/n2-standard-4
─────────────────────────────────────────────────────────────────────
• benchmark_cpu on aws/c5.2xlarge: -8.2%
• benchmark_io on azure/Standard_D4: -6.1%
```

### In Bar Charts

**Y-axis Labels:**
- Single config: `benchmark_cpu (aws/c5.2xlarge)`
- Multiple configs: `benchmark_cpu (avg across 3 configs)`

**Hover Tooltips:**
```
benchmark_cpu
Average change: -7.1%

By Hardware:
  aws/c5.2xlarge: -5.0% (100.00 → 95.00)
  azure/Standard_D4: -9.1% (110.00 → 100.00)
```

## Key Terms

**Hardware Configuration** = Cloud Provider + Instance Type
- Example: `aws/c5.2xlarge`
- Example: `azure/Standard_D4`
- Example: `gcp/n2-standard-4`

**Test×Hardware Comparison** = One benchmark test on one hardware config
- Example: 45 test×hardware comparisons = maybe 15 tests × 3 hardware configs

**Matching Hardware** = Same hardware config exists in both OS versions
- Only these are included in comparisons

## Common Questions

### Q: Why do I see fewer comparisons than expected?
**A:** Only tests that ran on matching hardware in both versions are compared. If a test only ran on hardware config A in version 9.5 and only on hardware config B in version 9.6, no comparison is made.

### Q: Can I see which hardware was excluded?
**A:** The hardware summary shows which configs were used. Any hardware not listed wasn't available in both versions for that test.

### Q: What if a test shows different trends on different hardware?
**A:** The bar chart shows the average, but hover over the bar to see per-hardware breakdown. This can reveal hardware-specific issues.

### Q: How does this affect regression detection?
**A:** More accurate! A test is marked as regressed if it regressed on ANY hardware config where it was compared, not just on average.

## Visual Guide

```
┌─────────────────────────────────────────────────────────────┐
│ Compare Latest Major Releases (9.X vs 10.X)                 │
├─────────────────────────────────────────────────────────────┤
│ ⚠ 3 regressions detected                                    │
│ 18 test×hardware comparison(s) | Compared on 2 hardware     │
│ configuration(s): aws/c5.2xlarge, azure/Standard_D4         │
│ ───────────────────────────────────────────────────────────│
│ • benchmark_cpu on aws/c5.2xlarge: -8.2%                   │
│ • benchmark_io on azure/Standard_D4: -6.1%                 │
│ • benchmark_mem on aws/c5.2xlarge: -5.5%                   │
│                                                             │
│ [Bar Chart]                                                 │
│                                                             │
│ benchmark_cpu (avg across 2 configs)  ████▒▒ -7.1%         │
│ benchmark_io (azure/Standard_D4)      ████▒▒ -6.1%         │
│ benchmark_mem (aws/c5.2xlarge)        █████▒ -5.5%         │
│ benchmark_net (avg across 2 configs)  ██████ +2.3%         │
│                                                             │
│ Hover over any bar to see per-hardware breakdown!          │
└─────────────────────────────────────────────────────────────┘
```

## Behind the Scenes

### Data Structure Per Comparison
```python
{
    'test_name': 'benchmark_cpu',
    'cloud_provider': 'aws',
    'instance_type': 'c5.2xlarge',
    'hardware_config': 'aws/c5.2xlarge',
    'baseline_version': '9.5',
    'comparison_version': '9.6',
    'baseline_mean': 100.0,
    'baseline_count': 5,      # 5 test runs
    'comparison_mean': 95.0,
    'comparison_count': 5,    # 5 test runs
    'percent_change': -5.0,
    'is_regression': False
}
```

### When Tests Have Multiple Hardware Configs
The visualization:
1. Groups by test_name
2. Averages percent_change across hardware configs
3. Shows individual configs in hover tooltip
4. Marks as regression if ANY config regressed

## Best Practices

1. **Trust the Data**: If a comparison isn't shown, there's a good reason (no matching hardware)

2. **Check the Hover**: Always hover to see per-hardware details, especially for tests with multiple configs

3. **Compare Hardware Configs**: If you see different results on different hardware, that's valuable info!

4. **Use the Hardware Summary**: Tells you exactly which hardware was used in analysis

5. **Investigate Discrepancies**: If one hardware shows regression but another doesn't, drill down to investigate

## Summary

✅ **Automatic** - No configuration needed
✅ **Accurate** - Only valid comparisons included
✅ **Transparent** - Hardware always visible
✅ **Detailed** - Per-hardware breakdown available
✅ **Trustworthy** - Scientifically sound methodology

Your performance comparisons are now **valid and meaningful**!

