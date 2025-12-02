# Bug Fix: RHEL Version Regression Analysis Showing "No data available"

## Issue Summary

All sections of the RHEL Version Regression Analysis were showing "No data available" messages despite having synthetic data with RHEL versions.

## Root Causes

**This was a CODE ISSUE with TWO separate problems**, not a synthetic data issue:

### Problem 1: Instance Type Filter (Initial Issue)

The problem was in `/home/gdumas/src/zaxby/src/components/filters.py` where the instance type filter was initialized with only the first 5 instance types:

```python
value=instance_types[:5] if len(instance_types) > 5 else instance_types
```

### Impact of the Bug

When the dashboard loaded with default filters:
- **Total data**: Reduced from 2500 records to only 470 records
- **RHEL data**: Reduced from 835 records to only 145 records
- **Result**: Insufficient overlapping hardware configurations for meaningful comparisons

The RHEL regression analysis requires tests to run on **identical hardware configurations** (same cloud provider + instance type) to make valid comparisons. With only 5 out of 32 instance types selected, there wasn't enough data overlap between RHEL versions.

### Analysis Results Before Fix

```
After initial filtering: 470 records
RHEL records after filter: 145
Analysis summary: No significant regressions detected

major_release_comparison: 1 comparisons, 0 regressions
rhel9_sequential: 0 comparisons, 0 regressions
rhel10_sequential: 0 comparisons, 0 regressions
```

## The Fix

Changed the instance type filter default in `src/components/filters.py` (line 56) to include ALL instance types:

```python
# Before:
value=instance_types[:5] if len(instance_types) > 5 else instance_types

# After:
value=instance_types
```

### Analysis Results After Fix

```
After filtering with ALL instance types: 2500 records
RHEL records after filter: 835
Analysis summary:
Total: 3 regression(s) detected
RHEL 9.5 vs 9.6: 1 regression(s)
RHEL 10.0 vs 10.1: 2 regression(s)

major_release_comparison:
  Versions: 9.6 vs 10.1
  Comparisons: 2
  Regressions: 0

rhel9_sequential:
  Versions: 9.5 vs 9.6
  Comparisons: 1
  Regressions: 1

rhel10_sequential:
  Versions: 10.0 vs 10.1
  Comparisons: 4
  Regressions: 2
```

## Verification

The synthetic data was **NOT** the issue. The data includes:
- 835 RHEL records across versions: 9.2, 9.3, 9.4, 9.5, 9.6, 10.0, 10.1
- 32 different instance types across AWS, Azure, and GCP
- 12 different benchmark tests
- Proper OS distribution and version fields

### Problem 2: JSON Serialization Type Conversion (Critical Bug)

After fixing Problem 1, a second issue was discovered: **Type conversion during JSON serialization**.

The Dash callback chain works as follows:
1. `update_filtered_data()` filters the DataFrame and serializes it to JSON
2. `analyze_filtered_data()` deserializes the JSON back to a DataFrame
3. `analyze_rhel_simplified_regressions()` processes the data

**The Bug:** When `df.to_json()` serializes the DataFrame, version strings like `'9.5'`, `'10.1'` get converted to float64 numbers like `9.5`, `10.1`. When `pd.read_json()` deserializes them, they remain as `numpy.float64` objects.

**The Error:** In `analyze_rhel_simplified_regressions()`, the code tried to call `.startswith('9.')` on these float64 objects, causing:
```
AttributeError: 'numpy.float64' object has no attribute 'startswith'
```

#### Fix for Problem 2

Updated `src/data_processing.py` in two places:

**1. In `analyze_rhel_simplified_regressions()` (line ~491):**
```python
# Ensure os_version is string type (may be float after JSON deserialization)
df_rhel['os_version'] = df_rhel['os_version'].astype(str)
```

**2. In `_sort_versions()` method (line ~447):**
```python
def version_key(version):
    """Convert version string to tuple for natural sorting."""
    try:
        # Convert to string first (in case it's a number)
        version_str = str(version)
        # Split on '.' and convert each part to int
        parts = version_str.split('.')
        return tuple(int(part) for part in parts)
    except (ValueError, AttributeError):
        # If conversion fails, return a tuple that sorts last
        return (999, 999, str(version))

# Convert all versions to strings for consistent output
return sorted([str(v) for v in versions], key=version_key)
```

This ensures the code handles both string and numeric version values robustly.

## Files Changed

- `/home/gdumas/src/zaxby/src/components/filters.py` - Line 56 (Problem 1)
- `/home/gdumas/src/zaxby/src/data_processing.py` - Lines ~491 and ~447-457 (Problem 2)

## Testing

Verified that:
1. ✅ App starts successfully and loads 2500 records
2. ✅ RHEL regression analysis detects 3 regressions
3. ✅ All three comparison sections show data:
   - Major Release Comparison (9.6 vs 10.1)
   - RHEL 9.X Sequential (9.5 vs 9.6)
   - RHEL 10.X Sequential (10.0 vs 10.1)
4. ✅ No linter errors

## Testing - Final Results

After applying both fixes:

```
=== Testing JSON Round-Trip Fix ===

After JSON deserialization:
os_version dtype: float64
Sample os_version values: [24.04, 24.04, 24.04]
Type of first value: <class 'numpy.float64'>

=== Running RHEL Regression Analysis ===

✓ Analysis succeeded!

Summary:
Total: 3 regression(s) detected
RHEL 9.5 vs 9.6: 1 regression(s)
RHEL 10.0 vs 10.1: 2 regression(s)

Total regressions: 3

major_release_comparison:
  Versions: 9.6 vs 10.1
  Comparisons: 2
  Regressions: 0

rhel9_sequential:
  Versions: 9.5 vs 9.6
  Comparisons: 1
  Regressions: 1

rhel10_sequential:
  Versions: 10.0 vs 10.1
  Comparisons: 4
  Regressions: 2
```

## Recommendation

The dashboard should now display RHEL regression analysis data correctly. Both the data filtering issue and the type conversion issue have been resolved. Users will see comparison charts and regression summaries for all three analysis sections.

## Key Takeaway

This bug demonstrates the importance of testing with the full Dash callback chain, as JSON serialization/deserialization can introduce subtle type conversion issues that don't appear when testing functions in isolation.

