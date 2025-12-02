# Synthetic Data Hardware Consistency Fix

## Issue Summary

**Problem:** The "Compare Latest Major Releases" section in the RHEL Version Regression Analysis was only showing the `pig` benchmark when comparing RHEL 9.6 vs 10.1, even though 12 different benchmarks existed in the dataset for both versions.

**User Question:** "Where are the other benchmarks? Is this a synthetic data or a code issue?"

**Answer:** This was a **synthetic data generation issue**, not a code bug.

## Root Cause

The regression analysis code correctly requires that version comparisons only be made on **identical hardware configurations** (same `cloud_provider` + `instance_type` combination). This is essential for valid apples-to-apples performance comparisons.

However, the synthetic data generator was **randomly assigning** hardware configurations to each test/OS version combination without ensuring overlap between versions. This resulted in:

### Before the Fix:
- **RHEL 9.6** and **10.1** both contained all 12 benchmarks
- But only **2 tests** had any common hardware configurations:
  - `pig`: 1 common config (`azure/Standard_D64s_v3`)
  - `pyperf`: 1 common config (`gcp/n2-standard-64`)
- The other **10 tests** had zero common hardware configs between the two versions
- Only `pig` showed up in the UI because it was the only test with a detectable regression on matching hardware

### Data Analysis Results (Before Fix):

```
Tests that appear in both RHEL 9.6 and 10.1:
  auto_hpl: 0 common HW configs
  coremark: 0 common HW configs
  coremark_pro: 0 common HW configs
  fio: 0 common HW configs
  passmark: 0 common HW configs
  phoronix: 0 common HW configs
  pig: 1 common HW config     ← Only this showed up
    -> azure/Standard_D64s_v3
  pyperf: 1 common HW config
    -> gcp/n2-standard-64
  specjbb: 0 common HW configs
  streams: 0 common HW configs
  sysbench: 0 common HW configs
  uperf: 0 common HW configs
```

## The Fix

Modified `src/synthetic_data.py` in the `_generate_scenarios()` method to:

1. **Pre-assign consistent hardware configurations per test type**
   - Each test gets 2-3 hardware configurations assigned once
   - These same configurations are used across ALL OS versions

2. **Generate scenarios with hardware consistency**
   - When generating scenarios for RHEL 9.6, a test runs on its assigned hardware
   - When generating scenarios for RHEL 10.1, the SAME test runs on the SAME hardware
   - This ensures valid version-to-version comparisons

### Code Changes:

**Before:**
```python
for rhel_version in rhel_versions:
    for test_type in self.test_types:
        # Randomly select hardware (no consistency!)
        cloud_provider = random.choice(self.cloud_providers)
        instance_type = random.choice(self.instance_types[cloud_provider])
        
        scenarios.append({...})
```

**After:**
```python
# Pre-assign hardware configs per test type
test_hardware_configs = {}
for test_type in self.test_types:
    num_configs = random.randint(2, 3)
    test_configs = []
    for _ in range(num_configs):
        cloud_provider = random.choice(self.cloud_providers)
        instance_type = random.choice(self.instance_types[cloud_provider])
        test_configs.append((cloud_provider, instance_type))
    test_hardware_configs[test_type] = test_configs

# Use consistent hardware across all versions
for rhel_version in rhel_versions:
    for test_type in self.test_types:
        # Use pre-assigned hardware for this test
        for cloud_provider, instance_type in test_hardware_configs[test_type]:
            scenarios.append({...})
```

## Results After Fix

### New Data Distribution:

```
Total test×hardware comparisons: 29 (was 2)

Tests included in comparison:
  • pig                 : 4 hardware config(s)  ← Now 4 instead of 1
  • streams             : 3 hardware config(s)  ← Now included!
  • phoronix            : 3 hardware config(s)  ← Now included!
  • pyperf              : 3 hardware config(s)  ← Now 3 instead of 1
  • fio                 : 2 hardware config(s)  ← Now included!
  • coremark_pro        : 2 hardware config(s)  ← Now included!
  • coremark            : 2 hardware config(s)  ← Now included!
  • auto_hpl            : 2 hardware config(s)  ← Now included!
  • passmark            : 2 hardware config(s)  ← Now included!
  • specjbb             : 2 hardware config(s)  ← Now included!
  • sysbench            : 2 hardware config(s)  ← Now included!
  • uperf               : 2 hardware config(s)  ← Now included!
```

### Regressions Detected:

```
8 regressions detected across 7 different benchmarks:
  • streams              on aws/c6i.24xlarge              :  -41.39%
  • pyperf               on aws/r5.24xlarge               :  -40.55%
  • sysbench             on azure/Standard_D64s_v3        :  -34.68%
  • specjbb              on gcp/c2-standard-48            :  -28.82%
  • phoronix             on azure/Standard_F96s_v2        :  -23.43%
  • phoronix             on aws/m5.4xlarge                :  -14.86%
  • sysbench             on aws/r5.12xlarge               :   -9.72%
  • passmark             on gcp/c2-standard-30            :   -8.37%
```

## Summary

- **The regression analysis code was working correctly** - it properly enforces hardware-aware comparisons
- **The synthetic data generator had a flaw** - it wasn't creating data that could be meaningfully compared
- **The fix ensures every test runs on the same hardware across all OS versions**, enabling comprehensive regression analysis
- **Impact:** The dashboard now shows **all 12 benchmarks** instead of just 1, with **29 test×hardware comparisons** instead of 2

## Files Modified

1. `src/synthetic_data.py`:
   - Modified `_generate_scenarios()` method to pre-assign and reuse hardware configs per test
   - Updated comments and print statements to reflect the change
   - Adjusted `main()` to generate 3000 documents (was 2500)

2. `data/synthetic/benchmark_results.json`:
   - Regenerated with the fix applied
   - Now contains 3000 records with hardware consistency

## Verification

To verify the fix worked:

```bash
cd /home/gdumas/src/zaxby
source venv/bin/activate
python3 -c "
from src.data_processing import BenchmarkDataProcessor, load_synthetic_data
processor = BenchmarkDataProcessor()
raw_docs = load_synthetic_data()
df = processor.documents_to_dataframe(raw_docs)
results = processor.analyze_rhel_simplified_regressions(df)
major_comp = results['major_release_comparison']
print(f'Tests included: {len(major_comp[\"comparison_data\"][\"test_name\"].unique())}')
print(f'Total comparisons: {major_comp[\"num_comparisons\"]}')
"
```

Expected output:
- Tests included: 12 (all benchmarks)
- Total comparisons: 29 (multiple hardware configs per test)

## Lessons Learned

When generating synthetic data for regression analysis, it's critical that:

1. **The same tests run on the same hardware across different versions** being compared
2. **Hardware diversity is maintained** (multiple configs per test) but **consistently applied**
3. **Data generation should match the analysis requirements** - if the analysis needs hardware consistency, the generator must provide it

This fix makes the synthetic data much more realistic and useful for testing the regression analysis features of the dashboard.

