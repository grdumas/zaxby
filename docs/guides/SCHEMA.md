# OpenSearch Schema Documentation

**Index**: `zathras-results`  
**Total Documents**: 5,659  
**OpenSearch Version**: 3.2.0  
**Last Updated**: 2026-05-29

## Overview

The `zathras-results` index contains performance benchmark test results from the Zathras test orchestration system. Each document represents a single test execution with comprehensive system configuration, test results, and performance metrics.

## Document Structure

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `metadata` | object | Core metadata about the test execution |
| `test` | object | Information about the test/benchmark that was run |
| `test_configuration` | object | Configuration parameters for the test execution |
| `system_under_test` | object | Detailed hardware and OS information |
| `runtime_info` | object | Runtime execution details |
| `results` | object | Test execution results and metrics |
| `_export_metadata` | object | Metadata about export to OpenSearch |

---

## Detailed Field Descriptions

### 1. `metadata` Object

Core identification and context for the test execution.

```json
{
  "document_id": "coremark_bf2d1fa468096fc7",
  "document_type": "zathras_test_result",
  "zathras_version": "1.0",
  "test_timestamp": "2025-11-18T12:08:59Z",
  "processing_timestamp": "2025-11-18T18:43:41.497Z",
  "collection_timestamp": "2025-11-18T12:08:59Z",
  "os_vendor": "rhel",
  "cloud_provider": "aws",
  "instance_type": "m5.24xlarge",
  "iteration": 0,
  "scenario_name": "rhel_95"
}
```

**Key Fields for Dashboard:**
- `os_vendor`: Operating system vendor (e.g., "rhel")
- `cloud_provider`: Cloud platform (e.g., "aws", "azure", "ibm", "gcp")
- `instance_type`: Hardware configuration identifier (e.g., "m5.24xlarge", "bx2-16x64")
- `test_timestamp`: When the test was executed (ISO 8601 format)
- `scenario_name`: Test scenario identifier (e.g., "rhel_95", "RHEL-10.2-20260507.1-x86_64")
- `iteration`: Test iteration number

**Observed Cloud Providers** (as of 2026-05-29):
- AWS: 3,851 documents (68% of total)
- Azure: 1,519 documents (27% of total)
- IBM Cloud: 274 documents (5% of total)
- GCP: 12 documents
- local: 3 documents

### 2. `test` Object

Information about the benchmark/test executed.

```json
{
  "name": "coremark",
  "version": "v1.22.zip",
  "wrapper_version": "v1.22.zip"
}
```

**Observed Test Names** (as of 2026-05-29):
- `pyperf` - Python performance benchmarks (4,856 documents, 86% of total)
- `coremark_pro` - CoreMark-PRO benchmark suite (172 documents)
- `coremark` - CoreMark CPU benchmark (147 documents)
- `streams` - STREAM memory bandwidth benchmark (128 documents)
- `phoronix` - Phoronix Test Suite (74 documents)
- `auto_hpl` - High-Performance Linpack (67 documents)
- `passmark` - PassMark Performance Test (60 documents)
- `specjbb` - SPECjbb Java benchmark (59 documents)
- `uperf` - Network performance tool (46 documents)
- `pig` - Apache Pig benchmark (31 documents)
- `fio` - Flexible I/O tester (10 documents)
- `speccpu2017` - SPEC CPU 2017 (7 documents)
- `iozone` - Filesystem benchmark (2 documents)

### 3. `system_under_test` Object

Comprehensive system configuration information.

#### 3.1 `system_under_test.hardware.cpu`

```json
{
  "vendor": "GenuineIntel",
  "model": "Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz",
  "architecture": "x86_64",
  "cores": 96,
  "threads_per_core": 2,
  "sockets": 2,
  "numa_nodes": 2,
  "cache_l3": "71.5 MiB (2 instances)",
  "flags": { ... }
}
```

#### 3.2 `system_under_test.hardware.memory`

```json
{
  "total_gb": 373,
  "total_kb": 391500104,
  "available_kb": 388185644
}
```

#### 3.3 `system_under_test.operating_system`

```json
{
  "distribution": "rhel",
  "version": "9.5",
  "kernel_version": "5.14.0-503.11.1.el9_5.x86_64",
  "hostname": "ip-170-0-29-189.us-east-2.compute.internal"
}
```

**Key Fields for Dashboard:**
- `distribution`: OS distribution (e.g., "rhel")
- `version`: OS version (e.g., "9.5", "10.2")
- `kernel_version`: Linux kernel version

**Observed OS Versions** (as of 2026-05-29):
- RHEL 9.5: 3,616 documents (most common)
- RHEL 10.2: 1,223 documents
- RHEL 9.6: 588 documents
- RHEL 9.8: 172 documents
- RHEL 10.0: 42 documents
- RHEL 9.7: 15 documents
- RHEL 10.3: 3 documents

### 4. `results` Object

Test execution results and performance metrics.

```json
{
  "status": "PASS",
  "total_runs": 0,
  "primary_metric": {
    "name": "mean",
    "value": 0.45533642190000023,
    "unit": "seconds"
  },
  "runs": {
    "run_0": { ... }
  }
}
```

#### 4.1 `results.primary_metric`

The main performance metric for the test.

- `name`: Metric name (e.g., "mean", "SUMM_CPU", "gflops")
- `value`: Numeric metric value
- `unit`: Unit of measurement (e.g., "seconds", "BOPs", "MB/s")

#### 4.2 `results.runs.run_X.metrics`

Detailed metrics from each test run. **Highly variable based on test type**.

**Example Metric Patterns:**
- CoreMark-PRO: `CPU_*`, `ME_*`, `SUMM_*` metrics (BOPs)
- STREAM: `*_mb_per_sec` (memory bandwidth)
- HPL: `gflops` (floating point operations)
- Pyperf: `benchmark_name`, `mean`, timings in seconds
- PassMark: Score-based metrics

**Common Metric Suffixes:**
- `_max`: Maximum value across runs
- `_mean`: Mean/average value
- `_min`: Minimum value across runs
- `_stddev`: Standard deviation

### 5. `test_configuration` Object

Test execution configuration and parameters.

```json
{
  "iterations_requested": 1,
  "parameters": {
    "os_vendor": "rhel",
    "system_type": "aws",
    "host_config": "m5.24xlarge",
    "cloud_region": "us-east-2a",
    "test_to_run": ["auto_hpl", "coremark", ...],
    ...
  }
}
```

---

## Dashboard Filter Dimensions

Based on the schema analysis, the following dimensions are suitable for multi-axis filtering:

### Primary Filters

1. **OS Version**
   - Field: `system_under_test.operating_system.version`
   - Type: String (e.g., "9.5", "9.4")
   - Can also combine with `system_under_test.operating_system.distribution`

2. **Hardware/Instance Type**
   - Field: `metadata.instance_type`
   - Type: String (e.g., "m5.24xlarge", "m5.12xlarge")
   - Alternative: `test_configuration.parameters.host_config`

3. **Benchmark/Test Type**
   - Field: `test.name`
   - Type: String (e.g., "coremark", "passmark", "streams")

4. **Cloud Provider**
   - Field: `metadata.cloud_provider`
   - Type: String (e.g., "aws", "azure", "gcp")

5. **Date Range**
   - Field: `metadata.test_timestamp`
   - Type: ISO 8601 datetime string

6. **Scenario Name**
   - Field: `metadata.scenario_name`
   - Type: String (e.g., "rhel_95", "rhel_94")

### Secondary Filters (Advanced)

- **Test Status**: `results.status` (PASS/FAIL)
- **CPU Architecture**: `system_under_test.hardware.cpu.architecture`
- **CPU Vendor**: `system_under_test.hardware.cpu.vendor`
- **NUMA Nodes**: `system_under_test.hardware.cpu.numa_nodes`
- **Cloud Region**: `test_configuration.parameters.cloud_region`

---

## Metric Extraction Strategy

### Per-Test Metric Mapping

Different tests store their primary metrics in different locations:

| Test Type | Primary Metric Location | Example Value |
|-----------|-------------------------|---------------|
| CoreMark | `results.runs.run_0.metrics.multicore_score` | Float (BOPs) |
| CoreMark-PRO | `results.runs.run_0.metrics.SUMM_CPU_mean` | Float (BOPs) |
| PassMark | `results.runs.run_0.metrics.multicore_score` | Float (score) |
| STREAM | `results.runs.run_0.metrics.copy__mb_per_sec` | Float (MB/s) |
| HPL | `results.runs.run_0.metrics.gflops` | Float (GFLOPS) |
| Pyperf | `results.primary_metric.value` | Float (seconds) |

### Fallback Strategy

1. Check `results.primary_metric` first
2. Look for test-specific patterns in `results.runs.run_0.metrics`
3. Identify metrics with `_mean` suffix for aggregated values

---

## Data Characteristics

### Volume
- **Total documents**: 5,659
- **Field count**: 4,856 mapped fields across all documents
- **Nested depth**: Up to 5-6 levels

### Data Quality Notes
- All observed documents have `status: "PASS"`
- Timestamps are consistent (ISO 8601 format)
- Metric values are numeric (float/int)
- Some fields are test-specific (only present for certain test types)

### Temporal Coverage
- Date range: August 2025 - May 2026 (2025-08-14 to 2026-05-28)
- Actively updated with current data

---

## Comparison Scenarios

The dashboard should support comparisons across:

1. **OS Version Comparison**: Same hardware, different OS versions
   - Example: RHEL 9.5 vs RHEL 9.4 on m5.24xlarge

2. **Hardware Comparison**: Same OS, different hardware
   - Example: m5.24xlarge vs m5.12xlarge on RHEL 9.5

3. **Time-Series Regression**: Same config over time
   - Track performance changes across test runs

4. **Cross-Cloud Comparison**: Same config, different providers
   - Example: AWS vs Azure vs GCP

---

## Query Examples

### Get all unique OS versions
```json
{
  "size": 0,
  "aggs": {
    "os_versions": {
      "terms": {
        "field": "system_under_test.operating_system.version",
        "size": 100
      }
    }
  }
}
```

### Get all test types
```json
{
  "size": 0,
  "aggs": {
    "test_types": {
      "terms": {
        "field": "test.name",
        "size": 100
      }
    }
  }
}
```

### Filter by OS and hardware
```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"system_under_test.operating_system.version": "9.5"}},
        {"term": {"metadata.instance_type": "m5.24xlarge"}},
        {"term": {"test.name": "coremark"}}
      ]
    }
  }
}
```

**Note**: The index fields work without `.keyword` suffix for aggregations and term queries.

---

## Notes for Synthetic Data Generation

When generating synthetic data, maintain:

1. **Realistic metric ranges** based on observed data
2. **Field consistency** - same structure as real data
3. **Test-specific metrics** - different tests have different metric sets
4. **Performance patterns**:
   - Regressions: 20-40% decrease in scores
   - Improvements: 15-30% increase in scores
   - Stable: ±5% variation

5. **Temporal distribution**: Spread data across multiple days/weeks (current range: Aug 2025 - May 2026)

6. **Hardware variations**: Multiple instance types across cloud providers:
   - AWS: m5.*, m6.*, c5.*, etc.
   - Azure: Standard_D*, Standard_E*, etc.
   - IBM Cloud: bx2-*, cx2-*, mx2-*, etc.
   - GCP: n2-*, c2-*, etc.

7. **OS versions**: Multiple RHEL versions (9.5, 9.6, 9.7, 9.8, 10.0, 10.2, 10.3)

