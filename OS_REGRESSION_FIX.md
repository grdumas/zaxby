# OS Version Regression Analysis Fix

## Problem

The OS Version Regression Analysis was making nonsensical comparisons between different operating systems. The heatmap showed version transitions like:
- RHEL 9.6 → SLES 15.4
- SLES 15.6 → Ubuntu 20.04  
- Ubuntu 24.04 → Amazon Linux 2023.0

This occurred because the analysis was sorting all OS versions alphabetically across all distributions, resulting in cross-OS comparisons that don't make sense.

## Root Cause

In `src/data_processing.py`, the `analyze_os_version_regressions()` method was auto-detecting OS versions using:

```python
os_versions = sorted(df_with_cats['os_version'].dropna().unique())
```

This would sort ALL versions from ALL distributions alphabetically, creating a sequence like:
`["15.4", "15.5", "15.6", "2", "2023", "20.04", "22.04", "24.04", "9.2", "9.3", "9.4", "9.5", "9.6"]`

Then consecutive versions were compared regardless of which OS distribution they belonged to.

## Solution

### 1. Updated `analyze_os_version_regressions()` Method

**File:** `src/data_processing.py`

Added an `os_distribution` parameter to filter data to a single OS distribution before analyzing version regressions:

```python
def analyze_os_version_regressions(
    self,
    df: pd.DataFrame,
    os_distribution: str = 'rhel',  # NEW parameter
    os_versions: Optional[List[str]] = None,
    regression_threshold: float = -5.0
) -> Dict[str, Any]:
```

The method now:
1. Filters the dataframe to only include records from the specified OS distribution
2. Auto-detects versions ONLY within that distribution
3. Creates comparisons between consecutive versions of the SAME OS

### 2. Updated Dashboard Analysis Call

**File:** `app.py`

Updated the Q1 analysis callback to explicitly specify RHEL as the target distribution:

```python
# Question 1: OS Version Regressions (RHEL only)
try:
    results['q1'] = processor.analyze_os_version_regressions(
        filtered_df, 
        os_distribution='rhel'  # NEW parameter
    )
```

### 3. Enhanced Investigation Drill-Down

**File:** `app.py`

Updated the investigation view to:
- Track which OS distribution is being investigated
- Filter investigation data to only that distribution
- Display the OS distribution in the investigation header

Changes include:
- Added `os_distribution` to navigation state parameters
- Updated `create_investigation_layout()` to display OS distribution
- Updated `update_investigation_view()` to filter by OS distribution

## Verification

Created and ran `test_os_regression_fix.py` which confirmed:

### RHEL Analysis
- ✓ Versions: 9.2, 9.3, 9.4, 9.5, 9.6
- ✓ Transitions: 9.2→9.3, 9.3→9.4, 9.4→9.5, 9.5→9.6
- ✓ All comparisons within RHEL only

### Ubuntu Analysis
- ✓ Versions: 20.04, 22.04, 24.04
- ✓ Transitions: 20.04→22.04, 22.04→24.04
- ✓ All comparisons within Ubuntu only

### SLES Analysis
- ✓ Versions: 15.4, 15.5, 15.6
- ✓ Transitions: 15.4→15.5, 15.5→15.6
- ✓ All comparisons within SLES only

## Impact

### Fixed
- ❌ **Before:** Cross-OS comparisons (e.g., RHEL 9.6 vs SLES 15.4)
- ✅ **After:** Within-OS comparisons (e.g., RHEL 9.5 vs RHEL 9.6)

### Dashboard Behavior
- The "RHEL Version Regression Analysis" section now shows ONLY RHEL version comparisons
- The heatmap displays version transitions within RHEL only (e.g., 9.2→9.3, 9.3→9.4, etc.)
- Investigation drill-downs are properly filtered to the specified OS distribution
- The investigation view now displays which OS distribution is being analyzed

### Future Enhancement Opportunities

The fix makes the analysis more flexible for future use:

1. **Multi-OS Dashboard:** The method can now be called with different `os_distribution` values to create separate regression analyses for Ubuntu, SLES, Amazon Linux, etc.

2. **Configurable OS Selection:** The dashboard could be enhanced to let users select which OS distribution to analyze via a dropdown, rather than hardcoding RHEL.

3. **Comparative Regression View:** Could show regression analyses side-by-side for multiple OS distributions.

Example usage for other distributions:
```python
# Analyze Ubuntu regressions
ubuntu_results = processor.analyze_os_version_regressions(df, os_distribution='ubuntu')

# Analyze SLES regressions  
sles_results = processor.analyze_os_version_regressions(df, os_distribution='sles')

# Analyze Amazon Linux regressions
amazon_results = processor.analyze_os_version_regressions(df, os_distribution='amazon')
```

## Files Modified

1. `src/data_processing.py`
   - Updated `analyze_os_version_regressions()` signature and implementation
   - Added OS distribution filtering logic
   - Updated all dataframe references to use filtered data

2. `app.py`
   - Updated Q1 analysis call to specify `os_distribution='rhel'`
   - Added OS distribution to investigation navigation parameters
   - Updated investigation layout to display OS distribution
   - Updated investigation view to filter by OS distribution

## Testing

Run the dashboard and verify:
1. Navigate to http://127.0.0.1:8050
2. Check "RHEL Version Regression Analysis" section
3. Verify heatmap shows only RHEL-to-RHEL version transitions
4. Click on a heatmap cell to drill down
5. Verify investigation view shows OS distribution and filters correctly

Expected heatmap columns: `9.2→9.3`, `9.3→9.4`, `9.4→9.5`, `9.5→9.6` (RHEL versions only)

