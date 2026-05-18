# Track KPIs - Baseline Comparison Module

**Module**: `src/track_kpis.py`  
**Test Suite**: `tests/test_track_kpis.py`  
**Feature**: RPOPC-1162

## Overview

The Track KPIs module provides baseline vs nightly comparison functionality for performance benchmarks. It computes metric deltas, applies regression detection, and handles missing benchmarks between baseline and nightly datasets.

## Core Components

### 1. BaselineConfig

Configuration dataclass for baseline comparison:

```python
@dataclass(frozen=True)
class BaselineConfig:
    baseline_id: str                              # Unique baseline identifier
    date_range: tuple[datetime, datetime]        # Baseline data collection period
    benchmark_filter: Optional[Dict[str, Any]]   # Optional filters for benchmarks
```

**Example:**
```python
config = BaselineConfig(
    baseline_id="v1.0_baseline",
    date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
    benchmark_filter={"cloud_provider": "aws"}
)
```

### 2. BenchmarkDelta

Delta calculation for a single benchmark:

```python
@dataclass(frozen=True)
class BenchmarkDelta:
    benchmark_name: str              # Test name (e.g., "coremark")
    metric_name: str                 # Metric name (e.g., "iterations/sec")
    baseline_mean: Optional[float]   # Baseline mean value
    nightly_mean: Optional[float]    # Nightly mean value
    percent_change: Optional[float]  # Percentage change (baseline → nightly)
    absolute_change: Optional[float] # Absolute change (nightly - baseline)
    is_regression: bool              # Regression flag from regression_detection.py
    status: str                      # 'unchanged', 'added', 'removed', 'changed'
```

### 3. TrackKpiResult

Result bundle containing all deltas and summary statistics:

```python
@dataclass(frozen=True)
class TrackKpiResult:
    baseline_config: BaselineConfig    # Baseline configuration used
    nightly_timestamp: datetime        # Timestamp of nightly run
    deltas: List[BenchmarkDelta]      # Per-benchmark deltas
    summary: Dict[str, Any]            # Summary statistics
    source: str                        # 'opensearch' or 'synthetic'
    error: Optional[str]               # Error message if calculation failed
```

## Key Functions

### fetch_baseline_results()

Retrieves baseline dataset from OpenSearch based on configuration:

```python
def fetch_baseline_results(
    client: Any,
    config: BaselineConfig,
) -> pd.DataFrame
```

- Applies date range filter from `config.date_range`
- Applies optional benchmark filters from `config.benchmark_filter`
- Returns DataFrame with normalized benchmark data

### fetch_nightly_results()

Retrieves latest nightly run from OpenSearch:

```python
def fetch_nightly_results(
    client: Any,
    benchmark_filter: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame
```

- Sorts by `metadata.test_timestamp` descending to get latest results
- Applies optional benchmark filters
- Returns DataFrame with normalized benchmark data

### calculate_delta()

Computes metric changes between baseline and nightly datasets:

```python
def calculate_delta(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    config: BaselineConfig,
) -> TrackKpiResult
```

**Processing Steps:**
1. Filters both datasets to PASS status only (via `filter_dataframe_for_regression_math`)
2. Groups by `test_name` and calculates mean values
3. Computes percentage change and absolute change for each benchmark
4. Applies regression detection via `is_regression_for_test_name()`
5. Flags benchmark status: 'added', 'removed', 'changed', or 'unchanged'
6. Generates summary statistics

### calculate_delta_from_dataframes()

Wrapper for synthetic/testing use cases with pre-loaded DataFrames:

```python
def calculate_delta_from_dataframes(
    baseline_df: pd.DataFrame,
    nightly_df: pd.DataFrame,
    baseline_id: str = "synthetic",
) -> TrackKpiResult
```

## Benchmark Status Handling

The module handles four benchmark statuses:

1. **added**: Benchmark exists in nightly but not in baseline
   - `baseline_mean = None`
   - `percent_change = None`
   - `is_regression = False`

2. **removed**: Benchmark exists in baseline but not in nightly
   - `nightly_mean = None`
   - `percent_change = None`
   - `is_regression = False`

3. **changed**: Benchmark exists in both, values changed
   - Both means calculated
   - Percentage change and absolute change computed
   - Regression detection applied

4. **unchanged**: Benchmark exists in both with identical values
   - Both means calculated
   - No significant change detected

## Regression Detection Integration

The module integrates with `src/regression_detection.py` for threshold checks:

- Uses `is_regression_for_test_name()` to apply per-metric directionality
- Respects higher-is-better metrics (throughput, scores)
- Respects lower-is-better metrics (latency, duration)
- Default thresholds:
  - Higher-is-better: `-5.0%` (REGRESSION_THRESHOLD_REL)
  - Lower-is-better: `+5.0%` (REGRESSION_THRESHOLD_LATENCY)

**Example:**
```python
# coremark (higher-is-better): baseline=100, nightly=94 → -6% → regression
# pyperf (lower-is-better): baseline=1.5s, nightly=1.6s → +6.67% → regression
```

## Summary Statistics

The summary dictionary contains:

```python
{
    "total_benchmarks": int,    # Total benchmarks in comparison
    "added": int,               # Benchmarks added in nightly
    "removed": int,             # Benchmarks removed in nightly
    "changed": int,             # Benchmarks changed (both datasets)
    "unchanged": int,           # Benchmarks unchanged
    "regressions": int,         # Count of regressions detected
    "regression_rate": float,   # regressions / changed (0.0 if no changed)
}
```

## Usage Examples

### 1. OpenSearch Baseline Comparison

```python
from datetime import datetime
from src.opensearch_client import BenchmarkDataSource
from src.track_kpis import BaselineConfig, fetch_baseline_results, fetch_nightly_results, calculate_delta

# Create client
client = BenchmarkDataSource()

# Configure baseline
config = BaselineConfig(
    baseline_id="v1.0_baseline",
    date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
    benchmark_filter={"cloud_provider": "aws"}
)

# Fetch data
baseline_df = fetch_baseline_results(client, config)
nightly_df = fetch_nightly_results(client)

# Calculate delta
result = calculate_delta(baseline_df, nightly_df, config)

# Access results
print(f"Total benchmarks: {result.summary['total_benchmarks']}")
print(f"Regressions: {result.summary['regressions']}")

for delta in result.deltas:
    if delta.is_regression:
        print(f"{delta.benchmark_name}: {delta.percent_change:.2f}% change")
```

### 2. Synthetic Data Testing

```python
import pandas as pd
from src.track_kpis import calculate_delta_from_dataframes

# Create synthetic datasets
baseline_df = pd.DataFrame([
    {"test_name": "coremark", "status": "PASS", "primary_metric_value": 100.0, "primary_metric_name": "score"},
    {"test_name": "streams", "status": "PASS", "primary_metric_value": 50000.0, "primary_metric_name": "MB/s"},
])

nightly_df = pd.DataFrame([
    {"test_name": "coremark", "status": "PASS", "primary_metric_value": 95.0, "primary_metric_name": "score"},
    {"test_name": "streams", "status": "PASS", "primary_metric_value": 52000.0, "primary_metric_name": "MB/s"},
])

# Calculate delta
result = calculate_delta_from_dataframes(baseline_df, nightly_df, baseline_id="test_baseline")

# Check for regressions
regressions = [d for d in result.deltas if d.is_regression]
print(f"Found {len(regressions)} regression(s)")
```

## Error Handling

The module handles errors gracefully:

1. **OpenSearch failures**: Returns empty DataFrame, logs error
2. **Calculation errors**: Returns TrackKpiResult with `error` field set
3. **Zero baseline**: Skips percentage change, still calculates absolute change
4. **Missing metrics**: Handles via None values

## Testing

Comprehensive test suite with 23 tests covering:

- ✅ Baseline configuration creation and immutability
- ✅ Delta calculation with synthetic datasets
- ✅ Regression detection (higher-is-better and lower-is-better metrics)
- ✅ Added/removed/changed benchmark handling
- ✅ PASS-only filtering
- ✅ Summary statistics generation
- ✅ Percentage and absolute change calculations
- ✅ Zero baseline handling
- ✅ Empty dataset handling
- ✅ OpenSearch client integration (mocked)
- ✅ Exception handling

**Run tests:**
```bash
pytest tests/test_track_kpis.py -v
```

## Integration Points

### Dependencies

- `src/regression_detection.py`: Threshold checks and directionality
- `src/opensearch_client.py`: OpenSearch data retrieval
- `pandas`: Data processing

### Used By

- Track mode dashboards (future)
- Nightly regression reports (future)
- CI/CD pipeline integration (future)

## Design Decisions

1. **Immutable dataclasses**: All result types use `frozen=True` for safety
2. **PASS-only filtering**: Only PASS status included in calculations (via `filter_dataframe_for_regression_math`)
3. **Graceful degradation**: Errors logged but don't crash; returns empty/error states
4. **Metric directionality**: Delegates to `regression_detection.py` for consistent logic
5. **Flexible configuration**: BaselineConfig supports arbitrary filters

## Future Enhancements

- [ ] Support for multiple baseline comparisons
- [ ] Trend analysis across multiple nightly runs
- [ ] Customizable regression thresholds per benchmark
- [ ] Historical delta tracking
- [ ] Visualization integration with Dash dashboard

## See Also

- `docs/guides/REGRESSION_DETECTION.md`: Regression detection methodology
- `docs/guides/PULSE_KPIS.md`: Pulse KPI definitions (descriptive metrics)
- `docs/guides/SCHEMA.md`: OpenSearch schema documentation
