# Performance Testing Guide

This document describes the performance testing framework for the Zaxby dashboard, including function-level benchmarks and HTTP load tests.

## Overview

The performance testing framework uses a two-tier approach:

1. **Function-level benchmarks (pytest-benchmark)**: Measures latency and throughput of individual data pipeline functions
2. **HTTP load tests (Locust)**: Simulates concurrent users interacting with the dashboard

Both tiers use synthetic data mode for consistent, repeatable baselines without production dependencies.

## Setup

Install performance testing dependencies:

```bash
pip install -r tests/performance/requirements.txt
```

This installs:
- `pytest-benchmark` (≥4.0.0): Statistical benchmarking with p50/p95/p99 metrics
- `locust` (≥2.20.0): HTTP load testing with parameterized concurrency
- `psutil` (≥5.9.0): Optional resource monitoring (CPU, memory)

## Function-Level Benchmarks

### Quick Start

Run all benchmarks:
```bash
pytest tests/performance/ --benchmark-only -v
```

Run specific test file:
```bash
pytest tests/performance/test_query_service_benchmark.py --benchmark-only -v
```

Filter by data scale:
```bash
# Only 1K scale (fast)
pytest tests/performance/ -k "1k" --benchmark-only

# Only 10K and 100K scales
pytest tests/performance/ -k "10k or 100k" --benchmark-only
```

### Baseline Comparison

Save a baseline:
```bash
pytest tests/performance/ --benchmark-only --benchmark-save=baseline_v1
```

Compare against baseline:
```bash
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline_v1
```

This shows performance deltas (faster/slower) compared to the saved baseline.

### Test Structure

#### Query Service Benchmarks (`test_query_service_benchmark.py`)

Tests synthetic-mode aggregation functions called by Dash callbacks:

| Function | Description | Expected Latency (1K) |
|----------|-------------|-----------------------|
| `aggregate_results_overview_from_dataframe` | Groupby cloud_provider | ~1-2ms |
| `aggregate_category_kpis_from_dataframe` | Test name groupby + category mapping | ~2-5ms |
| `aggregate_activity_timeline_from_dataframe` | Monthly date histogram | ~2-5ms |
| `aggregate_pulse_scope_footnote_from_dataframe` | Document count + date range | <1ms |
| `aggregate_baseline_comparison_from_dataframe` | Baseline vs nightly with regression detection | ~50-100ms |
| `aggregate_recent_nightly_runs_from_dataframe` | Nightly run grouping | ~10-20ms |

#### Data Processing Benchmarks (`test_data_processing_benchmark.py`)

Tests data transformation and analysis methods:

| Method | Description | Expected Latency (1K) |
|--------|-------------|-----------------------|
| `documents_to_dataframe` | Document-to-DataFrame conversion (startup) | ~25-35ms |
| `filter_data` | DataFrame filtering (no filters) | ~1-2ms |
| `filter_data` | Single filter (OS version) | ~2-5ms |
| `filter_data` | Multi-filter (OS + cloud + date) | ~5-10ms |
| `analyze_rhel_simplified_regressions` | Three regression comparisons | ~100-200ms |
| `analyze_peer_os_comparison` | Peer OS comparison | ~50-100ms |
| `analyze_cloud_scaling` | Cloud instance scaling analysis | ~50-100ms |

### Data Scales

Tests run against three data scales:

| Scale | Documents | DataFrame Rows | Generation Time |
|-------|-----------|----------------|-----------------|
| 1K    | ~912      | ~912           | ~0.04s          |
| 10K   | ~10,032   | ~10,032        | ~0.42s          |
| 100K  | ~100,320  | ~100,320       | ~4.57s          |

Session-scoped fixtures ensure expensive data generation happens only once per test run.

### Interpreting Results

pytest-benchmark output includes:

- **Min/Max**: Best and worst run times
- **Mean**: Average latency across all runs
- **StdDev**: Standard deviation (lower = more consistent)
- **Median (p50)**: 50th percentile (typical performance)
- **IQR**: Interquartile range (middle 50% spread)
- **OPS**: Operations per second (1 / Mean)

Focus on **Median** for typical performance and **p95/p99** (via --benchmark-histogram) for tail latency.

### Resource Monitoring

The optional `resource_monitor` fixture logs CPU time and memory delta for each test:

```
CPU time: 0.125s, Memory delta: +12.3 MB
```

This helps identify memory-hungry operations. Requires `psutil` installed.

## HTTP Load Tests

### Prerequisites

Start the app in synthetic mode before running load tests:

```bash
DATA_MODE=synthetic python app.py
```

The app should be running on port 8050 (default).

### Quick Start

Run headless load test with 10 users for 60 seconds:

```bash
locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050
```

Parameters:
- `-u 10`: 10 concurrent users
- `-r 2`: Spawn rate (2 users per second)
- `-t 60s`: Run duration (60 seconds)
- `--host`: Dashboard URL

### Parameterized Concurrency

Test different load levels as specified in RPOPC-1173:

**Single user baseline:**
```bash
locust -f tests/performance/locustfile.py --headless -u 1 -r 1 -t 60s --host http://localhost:8050
```

**Light load (10 users):**
```bash
locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050
```

**Medium load (50 users):**
```bash
locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 120s --host http://localhost:8050
```

**Stress test (100 users):**
```bash
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 180s --host http://localhost:8050
```

### Multi-Process Mode

For 50+ user tests, the Dash development server (single-threaded Werkzeug) becomes a bottleneck. Use gunicorn with multiple workers:

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 worker processes
gunicorn -w 4 -b 0.0.0.0:8050 "app:server"
```

Then run Locust tests against this multi-process server.

### Web UI Mode

For interactive load testing with real-time charts:

```bash
locust -f tests/performance/locustfile.py --host http://localhost:8050
```

Open http://localhost:8089 in a browser, set user count and spawn rate, then click "Start swarming".

### User Tasks

The `DashboardUser` class simulates realistic user behavior with weighted tasks:

| Task | Weight | Description |
|------|--------|-------------|
| `load_page` | 1x | GET / (initial page load) |
| `fetch_pulse_kpis` | 3x | POST to fetch Pulse KPI bundle (4 aggregations) |
| `update_filters` | 5x | POST with varied filter combos (most common) |
| `analyze_data` | 2x | POST to trigger RHEL regression analysis |
| `fetch_nightly_runs` | 1x | POST for nightly run grouping |

Wait time between tasks: 1-5 seconds (realistic think time).

### Interpreting Results

Locust output includes:

| Metric | Description | Target |
|--------|-------------|--------|
| **Response Time (p50)** | Median latency | <500ms for filter updates, <2s for analysis |
| **Response Time (p95)** | 95th percentile latency | <1s for filters, <5s for analysis |
| **Response Time (p99)** | 99th percentile latency | <2s for filters, <10s for analysis |
| **Requests/s** | Throughput | Varies by concurrency; higher is better |
| **Failures** | Error count | Should be 0% |

At test completion, a summary table shows these metrics per task type.

## CI Integration (Future)

To integrate performance tests into CI pipelines:

1. **Function benchmarks**: Run on every PR, compare against `main` baseline:
   ```bash
   pytest tests/performance/ --benchmark-only --benchmark-compare=main
   ```

2. **Load tests**: Run nightly or on release branches:
   ```bash
   # Start app in background
   DATA_MODE=synthetic python app.py &
   APP_PID=$!
   sleep 5  # Wait for app startup

   # Run load test
   locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8050

   # Cleanup
   kill $APP_PID
   ```

3. **Baseline drift alerts**: Fail CI if performance degrades >20%:
   ```bash
   pytest tests/performance/ --benchmark-only --benchmark-compare=baseline --benchmark-compare-fail=mean:20%
   ```

## Troubleshooting

### "App not reachable" error in Locust

Ensure the app is running before starting Locust:
```bash
# Terminal 1: Start app
DATA_MODE=synthetic python app.py

# Terminal 2: Run Locust
locust -f tests/performance/locustfile.py --headless -u 5 -r 1 -t 30s --host http://localhost:8050
```

### Slow 100K benchmark generation

The 100K-scale fixture takes ~5 seconds to generate. This is normal and only happens once per session. To skip 100K tests in quick runs:

```bash
pytest tests/performance/ -k "not 100k" --benchmark-only
```

### High error rate in Locust tests

If you see >5% failures:
1. Check app logs for exceptions
2. Reduce concurrency (`-u 5` instead of `-u 100`)
3. Verify DATA_MODE=synthetic is set
4. Ensure sufficient system resources (CPU, memory)

### pytest-benchmark missing

If you see "unrecognized arguments: --benchmark-only":
```bash
pip install pytest-benchmark>=4.0.0
```

## Best Practices

1. **Always use synthetic mode** for performance tests to avoid production impact
2. **Run benchmarks before and after changes** to detect regressions
3. **Save baselines after verified improvements** to track progress
4. **Test at multiple scales** (1K/10K/100K) to understand scaling behavior
5. **Use gunicorn for 50+ user load tests** to avoid single-process bottleneck
6. **Monitor resource usage** with the resource_monitor fixture to identify memory leaks
7. **Run load tests for sufficient duration** (60s minimum, 120-180s for stress tests) to reach steady state

## References

- pytest-benchmark docs: https://pytest-benchmark.readthedocs.io/
- Locust docs: https://docs.locust.io/
- Dash callback wire format: https://dash.plotly.com/basic-callbacks
