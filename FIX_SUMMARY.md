# Fix Summary: Missing Benchmarks in RHEL Regression Comparison

## Quick Answer

**This was a synthetic data generation issue, not a code bug.**

The regression analysis only showed `pig` because the synthetic data generator was randomly assigning hardware configurations, resulting in only 2 out of 12 benchmarks having matching hardware between RHEL 9.6 and 10.1. The code correctly requires matching hardware for valid comparisons.

## Before Fix
- Only **2 of 12 tests** had any hardware overlap between RHEL 9.6 and 10.1
- Only `pig` showed a regression on matching hardware
- **29 test×hardware comparisons should have been possible but only 2 were**

## After Fix  
- **All 12 tests** now have 2-3 matching hardware configurations
- **29 test×hardware comparisons** are now possible
- **8 regressions detected** across 7 different benchmarks

## What Changed

Modified `src/synthetic_data.py` to pre-assign consistent hardware configurations per test type, ensuring each test runs on the same hardware across all OS versions.

## Results

The dashboard now shows comprehensive regression data:

```
Tests included in RHEL 9.6 vs 10.1 comparison:
  • pig          : 4 hardware configs
  • streams      : 3 hardware configs  
  • phoronix     : 3 hardware configs
  • pyperf       : 3 hardware configs
  • fio          : 2 hardware configs
  • coremark_pro : 2 hardware configs
  • coremark     : 2 hardware configs
  • auto_hpl     : 2 hardware configs
  • passmark     : 2 hardware configs
  • specjbb      : 2 hardware configs
  • sysbench     : 2 hardware configs
  • uperf        : 2 hardware configs

Regressions detected: 8 across 7 benchmarks
```

## View the Fix

1. **Dashboard**: http://127.0.0.1:8050 (now running with fixed data)
2. **Detailed explanation**: See `SYNTHETIC_DATA_HARDWARE_CONSISTENCY_FIX.md`
3. **Code changes**: See `src/synthetic_data.py` (lines 253-302)

## Verification

The fix has been applied and verified:
- ✅ Synthetic data regenerated with hardware consistency
- ✅ All 12 benchmarks now have matching hardware configs
- ✅ Dashboard now shows comprehensive regression analysis
- ✅ No linter errors

Refresh your browser at http://127.0.0.1:8050 to see all benchmarks in the "Compare Latest Major Releases" section!

