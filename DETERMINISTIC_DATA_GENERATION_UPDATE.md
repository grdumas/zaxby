# Deterministic Data Generation Update

## Issue

After the initial hardware consistency fix, the regression comparison was still not showing all 12 benchmarks. It was showing only 6 benchmarks (pig, pyperf, fio, auto_hpl, passmark, specjbb) instead of all 12.

**Root Cause:** The hardware assignment was still partially random:
- Using `random.randint(2, 3)` for the number of configs per test
- Random selection of cloud providers and instance types
- Random sampling when scenario count exceeded the target

This randomness meant some tests might get 2 configs while others got 3, and the specific hardware assigned varied, leading to incomplete coverage.

## Solution: Fully Deterministic Generation

Made the synthetic data generation **completely deterministic** to guarantee 100% coverage:

### 1. Fixed Hardware Configuration Pool

Defined a stable set of 3 hardware configs per cloud provider:

```python
stable_configs = {
    "aws": ["c6i.24xlarge", "m5.4xlarge", "r5.24xlarge"],
    "azure": ["Standard_D64s_v3", "Standard_F48s_v2", "Standard_E64s_v5"],
    "gcp": ["n2-standard-64", "c2-standard-60", "n2-highmem-96"]
}
```

### 2. Deterministic Test-to-Hardware Assignment

Each test gets **exactly 3 hardware configs** (one from each cloud provider) assigned using a deterministic pattern:

```python
for idx, test_type in enumerate(self.test_types):
    test_configs = []
    for cloud_provider in ["aws", "azure", "gcp"]:
        instance_idx = idx % len(stable_configs[cloud_provider])
        instance_type = stable_configs[cloud_provider][instance_idx]
        test_configs.append((cloud_provider, instance_type))
    test_hardware_configs[test_type] = test_configs
```

This ensures:
- Every test runs on exactly 3 hardware configurations
- Same configs are used across all OS versions
- Assignment is repeatable (same seed = same data)

### 3. No Random Sampling

Removed the random sampling logic that could drop scenarios. Now **all generated scenarios are used** to guarantee complete coverage.

## Results

### Perfect Distribution

```
📊 Test Type Distribution: All 12 tests have exactly 90 records (8.3% each)
📦 OS Version Distribution: All 15 versions have exactly 72 records (6.7% each)  
☁️  Cloud Provider Distribution: Perfectly balanced at 33.3% each
💻 Instance Type Variety: Only 9 unique configurations (deterministic)
```

### Complete RHEL 9.6 vs 10.1 Coverage

```
Total test×hardware comparisons: 36 (12 tests × 3 hardware configs)
Unique tests: 12 (ALL benchmarks)
Unique hardware configs: 9

Tests included:
  • auto_hpl      : 3 configs [aws/m5.4xlarge, azure/Standard_F48s_v2, gcp/c2-standard-60]
  • coremark      : 3 configs [gcp/n2-standard-64, azure/Standard_D64s_v3, aws/c6i.24xlarge]
  • coremark_pro  : 3 configs [aws/m5.4xlarge, azure/Standard_F48s_v2, gcp/c2-standard-60]
  • fio           : 3 configs [aws/m5.4xlarge, azure/Standard_F48s_v2, gcp/c2-standard-60]
  • passmark      : 3 configs [azure/Standard_E64s_v5, aws/r5.24xlarge, gcp/n2-highmem-96]
  • phoronix      : 3 configs [azure/Standard_D64s_v3, gcp/n2-standard-64, aws/c6i.24xlarge]
  • pig           : 3 configs [azure/Standard_E64s_v5, aws/r5.24xlarge, gcp/n2-highmem-96]
  • pyperf        : 3 configs [azure/Standard_E64s_v5, aws/r5.24xlarge, gcp/n2-highmem-96]
  • specjbb       : 3 configs [azure/Standard_D64s_v3, gcp/n2-standard-64, aws/c6i.24xlarge]
  • streams       : 3 configs [azure/Standard_D64s_v3, gcp/n2-standard-64, aws/c6i.24xlarge]
  • sysbench      : 3 configs [azure/Standard_E64s_v5, aws/r5.24xlarge, gcp/n2-highmem-96]
  • uperf         : 3 configs [aws/m5.4xlarge, azure/Standard_F48s_v2, gcp/c2-standard-60]
```

## Benefits

1. **Guaranteed Coverage:** Every test appears in every version comparison with the same hardware
2. **Reproducibility:** Same random seed produces identical data every time
3. **Efficiency:** Smaller file size (3.93 MB vs 10.91 MB) with better coverage
4. **Predictability:** No surprises - you know exactly what data will be generated
5. **Debugging:** Much easier to reason about and debug issues

## Files Modified

- `src/synthetic_data.py`:
  - Replaced random hardware selection with deterministic assignment
  - Removed random sampling that could drop scenarios
  - Updated documentation and print statements

## Dataset Statistics

- **Total documents:** 1,080 (down from 3,000, but with better coverage)
- **Scenarios:** 540 (all used)
- **Iterations per scenario:** 2
- **File size:** 3.93 MB
- **Test distribution:** Perfectly uniform (90 records per test)
- **OS version distribution:** Perfectly uniform (72 records per version)
- **Hardware distribution:** Perfectly uniform (120 records per config)

## Verification

```bash
cd /home/gdumas/src/zaxby
source venv/bin/activate
python3 -c "
from src.data_processing import BenchmarkDataProcessor, load_synthetic_data
processor = BenchmarkDataProcessor()
raw_docs = load_synthetic_data()
df = processor.documents_to_dataframe(raw_docs)
results = processor.analyze_rhel_simplified_regressions(df)
major = results['major_release_comparison']
print(f'Tests: {major[\"comparison_data\"][\"test_name\"].nunique()} (expect 12)')
print(f'Comparisons: {major[\"num_comparisons\"]} (expect 36)')
"
```

Output should show:
- Tests: 12 (all benchmarks)
- Comparisons: 36 (complete coverage)

## Dashboard

View the complete results at: **http://127.0.0.1:8050**

The "Compare Latest Major Releases (9.X vs 10.X)" section now shows all 12 benchmarks with comprehensive hardware coverage.

