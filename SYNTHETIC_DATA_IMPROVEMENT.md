# Synthetic Data Generator Improvement

## Problem
The RHEL regression analysis heatmap was showing only one visible result (passmark) because the synthetic data had very sparse test coverage across RHEL versions. Tests were randomly assigned to OS versions with no guarantee of overlap, resulting in:
- Only 1-2 tests appearing in both versions of consecutive RHEL version pairs
- Most heatmap cells being empty (NaN)
- Poor regression analysis due to insufficient comparison data

## Solution

### 1. Enhanced Scenario Generation (`src/synthetic_data.py`)

Completely rewrote the `_generate_scenarios()` method to use a **phase-based approach**:

#### Phase 1: Complete RHEL Coverage
- **Ensures ALL test types run on ALL RHEL versions**
- For each RHEL version (9.2, 9.3, 9.4, 9.5, 9.6, 10.0, 10.1):
  - Run all 12 test types
  - Vary cloud providers and instance types for diversity
- Result: 7 versions × 12 tests = 84 guaranteed RHEL scenarios

#### Phase 2: Other OS Coverage
- Apply the same comprehensive coverage to other OS distributions
- Ubuntu, SLES, Amazon Linux all get full test coverage across their versions

#### Phase 3: Additional Diversity
- Add random scenarios to reach the requested scenario count
- Provides additional data points and variability

### 2. Added RHEL 10.0 and 10.1 Versions

Updated the OS configuration to include future RHEL versions:
```python
self.os_configs = {
    "rhel": ["9.2", "9.3", "9.4", "9.5", "9.6", "10.0", "10.1"],
    # ... other OS configs
}
```

Updated kernel version generator to support RHEL 10.x:
- RHEL 9.x: Uses 5.14.0 kernel series
- RHEL 10.x: Uses 6.8.0 kernel series (newer)

### 3. Fixed Version Sorting (`src/data_processing.py`)

Added `_sort_versions()` method to sort versions in natural order:
- Before: Alphabetical sorting put "10.0" before "9.2"
- After: Natural sorting: 9.2 → 9.3 → 9.4 → 9.5 → 9.6 → 10.0 → 10.1

Implementation uses tuple comparison after splitting version strings:
```python
def _sort_versions(self, versions: List[str]) -> List[str]:
    def version_key(version_str):
        parts = version_str.split('.')
        return tuple(int(part) for part in parts)
    return sorted(versions, key=version_key)
```

## Results

### Before
- **RHEL records**: 176 (from 800 total)
- **Test overlap**: 1-2 tests per version transition
- **Heatmap completeness**: ~10-20% (mostly NaN cells)
- **Visible results**: Only 1 test (passmark) prominently visible

### After
- **Total records**: 2,500 (3.1× increase)
- **RHEL records**: 835 (4.7× increase)
- **RHEL versions**: 7 (added 10.0, 10.1)
- **Test overlap**: 12/12 tests (100%) on all version transitions
- **Heatmap completeness**: 72/72 cells filled (100%)
- **Version transitions**: 6 transitions analyzed
- **Regressions detected**: 27 (vs 3 before)

### Test Coverage by RHEL Version
Every RHEL version now has complete test coverage:
```
RHEL 9.2:  12/12 tests (100%)
RHEL 9.3:  12/12 tests (100%)
RHEL 9.4:  12/12 tests (100%)
RHEL 9.5:  12/12 tests (100%)
RHEL 9.6:  12/12 tests (100%)
RHEL 10.0: 12/12 tests (100%)
RHEL 10.1: 12/12 tests (100%)
```

### Heatmap Data
```
Version Transitions: 9.2→9.3, 9.3→9.4, 9.4→9.5, 9.5→9.6, 9.6→10.0, 10.0→10.1
Tests per transition: 12/12 (100% coverage)
```

## Files Modified

1. **`src/synthetic_data.py`**
   - Updated `os_configs` to include RHEL 10.0 and 10.1
   - Completely rewrote `_generate_scenarios()` with phase-based generation
   - Updated `_get_kernel_version()` to support RHEL 10.x
   - Updated `main()` to increase scenario count and add progress output

2. **`src/data_processing.py`**
   - Added `_sort_versions()` method for natural version sorting
   - Updated `analyze_os_version_regressions()` to use version sorting

3. **`data/synthetic/benchmark_results.json`**
   - Regenerated with 2,500 documents (was 800)
   - File size: 9.10 MB (was ~3 MB)

## Usage

To regenerate the synthetic data:
```bash
cd /home/gdumas/src/zaxby
source venv/bin/activate
python3 src/synthetic_data.py
```

The dashboard will automatically load the new data on next restart:
```bash
python3 app.py
```

## Visual Improvement

The RHEL Version Regression Analysis heatmap now displays:
- **12 test rows** (all visible with data)
- **6 version transition columns** (including 10.0 and 10.1)
- **72 filled cells** with percentage changes
- **Color-coded** performance changes (green = improvement, red = regression)

Users can now:
- See performance trends for ALL tests across ALL RHEL versions
- Click any cell to drill down into detailed investigation
- Compare performance across major version transitions (9.x → 10.x)
- Identify which tests regress or improve with each version

## Impact

✅ **Solved the original problem**: The heatmap now shows all 12 tests, not just one

✅ **Better regression analysis**: 100% data coverage enables meaningful insights

✅ **Future-proofing**: Added RHEL 10.0 and 10.1 for forward-looking analysis

✅ **Improved data quality**: Consistent test coverage across all OS versions

✅ **Scalable approach**: Phase-based generation can easily accommodate new tests or OS versions

