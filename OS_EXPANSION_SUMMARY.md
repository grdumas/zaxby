# Operating System Expansion Summary

## Overview

The synthetic data generator has been expanded to include multiple Linux distributions beyond RHEL, providing a more comprehensive dataset for testing OS performance comparisons.

## Changes Made

### 1. Synthetic Data Generator (`src/synthetic_data.py`)

**Added OS Distribution Support:**
- Changed from single OS version list to multi-distribution configuration
- Now supports 4 major Linux distributions with 13 total versions

**New Data Structure:**
```python
self.os_configs = {
    "rhel": ["9.2", "9.3", "9.4", "9.5", "9.6"],
    "ubuntu": ["20.04", "22.04", "24.04"],
    "amazon": ["2", "2023"],
    "sles": ["15.4", "15.5", "15.6"]
}
```

**Key Method Updates:**
- `_generate_scenarios()`: Now selects OS distribution and version independently
- `_generate_document()`: Updated to pass OS distribution as separate parameter
- `_generate_system_info()`: Updated to handle distribution-specific kernel versions
- `_generate_test_config()`: Updated to use OS distribution in configuration
- Added `_get_kernel_version()`: Generates realistic kernel versions per distribution

**Kernel Version Mapping:**
- **RHEL**: `5.14.0-503.11.1.el9_X.x86_64` (where X = minor version)
- **Ubuntu 20.04**: `5.15.0-91-generic`
- **Ubuntu 22.04**: `6.5.0-35-generic`
- **Ubuntu 24.04**: `6.8.0-31-generic`
- **Amazon Linux 2**: `5.10.220-173.862.amzn2.x86_64`
- **Amazon Linux 2023**: `6.1.82-99.168.amzn2023.x86_64`
- **SLES 15.x**: `5.14.21-150500.55.52-default`

### 2. Updated Statistics Output

The generator now tracks and reports:
- OS distribution counts (4 distributions)
- OS version details (13 versions)
- Distribution in summary output

### 3. Documentation Updates

**Updated Files:**
- `data/synthetic/README.md`: Added comprehensive OS distribution section
- `data/synthetic/USAGE_GUIDE.md`: Updated examples to show multi-distribution queries
- Both files now document all 4 distributions and 13 versions

## Current Dataset Distribution

After regeneration with the expanded OS support:

### By Distribution (800 total documents)
- **Ubuntu**: 224 tests (28.0%)
- **Amazon Linux**: 224 tests (28.0%)
- **RHEL**: 176 tests (22.0%)
- **SLES**: 176 tests (22.0%)

### By Version (13 unique versions)
- Amazon Linux 2: 128 tests (16.0%)
- Amazon Linux 2023: 96 tests (12.0%)
- Ubuntu 24.04: 104 tests (13.0%)
- Ubuntu 20.04: 72 tests (9.0%)
- Ubuntu 22.04: 48 tests (6.0%)
- SLES 15.4: 80 tests (10.0%)
- SLES 15.6: 64 tests (8.0%)
- SLES 15.5: 32 tests (4.0%)
- RHEL 9.3: 48 tests (6.0%)
- RHEL 9.2: 40 tests (5.0%)
- RHEL 9.6: 40 tests (5.0%)
- RHEL 9.4: 24 tests (3.0%)
- RHEL 9.5: 24 tests (3.0%)

## Data Structure Changes

### Metadata Field
```json
{
  "metadata": {
    "os_vendor": "ubuntu",  // Now can be: rhel, ubuntu, amazon, or sles
    "scenario_name": "ubuntu_2004"  // Format: {distribution}_{version_no_dots}
  }
}
```

### System Under Test Field
```json
{
  "system_under_test": {
    "operating_system": {
      "distribution": "ubuntu",  // Now can be: rhel, ubuntu, amazon, or sles
      "version": "20.04",
      "kernel_version": "5.15.0-91-generic",  // Distribution-specific
      "hostname": "test-aws-323.internal"
    }
  }
}
```

### Test Configuration Field
```json
{
  "test_configuration": {
    "parameters": {
      "os_vendor": "ubuntu"  // Now can be: rhel, ubuntu, amazon, or sles
    }
  }
}
```

## Benefits

1. **More Realistic Testing**: Dataset now covers major enterprise Linux distributions
2. **Better OS Comparison**: Can compare performance across different OS families
3. **Broader Coverage**: Represents diverse real-world deployment scenarios
4. **LTS Version Support**: Includes current LTS versions of Ubuntu and RHEL
5. **Cloud-Native OS**: Amazon Linux 2 and 2023 represent AWS-optimized distributions
6. **Enterprise SLES**: SUSE Linux Enterprise Server for enterprise scenarios

## Usage Examples

### Filter by Distribution
```python
# Get all Ubuntu tests
ubuntu_tests = [d for d in documents 
                if d['system_under_test']['operating_system']['distribution'] == 'ubuntu']

# Get all Amazon Linux 2023 tests
al2023_tests = [d for d in documents 
                if d['system_under_test']['operating_system']['distribution'] == 'amazon'
                and d['system_under_test']['operating_system']['version'] == '2023']
```

### Compare Across Distributions
```python
# Compare performance across distributions for same test
from collections import defaultdict

results_by_os = defaultdict(list)
for doc in documents:
    if doc['test']['name'] == 'coremark' and doc['results']['status'] == 'PASS':
        os_dist = doc['system_under_test']['operating_system']['distribution']
        os_ver = doc['system_under_test']['operating_system']['version']
        os_key = f"{os_dist} {os_ver}"
        metric_value = doc['results']['primary_metric']['value']
        results_by_os[os_key].append(metric_value)

# Calculate averages
for os_key, values in sorted(results_by_os.items()):
    avg = sum(values) / len(values)
    print(f"{os_key}: {avg:.2f} (n={len(values)})")
```

## Verification

All changes have been tested and verified:
- ✅ Synthetic data generates with all 4 distributions
- ✅ All 13 OS versions are represented
- ✅ Kernel versions are distribution-appropriate
- ✅ Data structure is consistent across distributions
- ✅ Documentation updated with new examples
- ✅ Data loads correctly through existing processing pipeline

## Next Steps

The dashboard and visualization components should automatically handle the new distributions through the existing data processing pipeline, as they use the `os_distribution` and `os_version` fields which are now properly populated.

To regenerate the dataset:
```bash
python src/synthetic_data.py
```

This will create 800 documents covering all 4 distributions and 13 versions.

