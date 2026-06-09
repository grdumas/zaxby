# Track Mode Guide

Track mode provides an exception-oriented view for CPT (Component Performance Testing) and release owners to monitor performance regressions between a stable baseline and nightly builds.

## Overview

Track mode is designed for continuous performance monitoring workflows where:
- You have a **stable baseline** (e.g., released version or previous stable build)
- You run **nightly builds** or continuous integration benchmarks
- You want to **track exceptions** (regressions, improvements, missing/new benchmarks)
- You need **quick triaging** of performance issues

Unlike traditional performance analysis that shows all results, Track mode filters to show only **exceptions** that require attention.

## Target Audience

- **CPT (Component Performance Testing) Engineers**: Daily monitoring of performance test results
- **Release Owners**: Pre-release validation and regression tracking
- **QE Teams**: Continuous integration performance gates
- **Performance Engineers**: Long-term performance trend analysis

## Workflow

### 1. Define Your Baseline

A baseline represents the "known good" state you're comparing against. This is typically:

- **Released version**: RHEL 9.5 GA builds
- **Previous stable build**: Last passing nightly from previous sprint
- **Release candidate**: RC1 for comparison with RC2
- **Tagged snapshot**: Specific git tag or build number

### 2. Configure Baseline in Track Mode

**Option A: Use the UI (Ad-hoc Analysis)**

1. Navigate to Track mode (click "Track" in the header or overview)
2. In the Configuration section:
   - Set "Baseline Date Range" to define baseline data window
   - Enter a "Baseline ID" (e.g., "rhel-9.5-ga" or "sprint-23-baseline")
   - Set "Nightly Run" date range to select comparison data
3. Click "Run Comparison"

**Option B: Use Environment Variables (Automated Scheduling)**

Configure `.env` for scheduled daily comparisons:

```bash
# Baseline configuration
TRACK_BASELINE_ID=rhel-9.5-ga
TRACK_BASELINE_START_DATE=2025-01-01T00:00:00
TRACK_BASELINE_END_DATE=2025-01-31T23:59:59

# Scheduler configuration
TRACK_SCHEDULER_ENABLED=true
TRACK_SCHEDULER_HOUR=6  # Run at 6 AM daily
TRACK_SCHEDULER_MINUTE=0
```

The scheduler will automatically:
- Fetch baseline data from the configured date range
- Fetch latest nightly results
- Calculate deltas
- Persist results to `track_results/` directory
- Log execution metadata

### 3. Interpret Results

Track mode shows four categories of exceptions:

#### Regressions
Benchmarks where performance **decreased** beyond the regression threshold.

**Example:**
```
Benchmark: coremark
Baseline: 100.0 iterations/sec
Nightly:  90.0 iterations/sec
Change:   -10.0% (REGRESSION)
```

**Action:** Investigate recent changes, file bug, bisect commits.

#### Improvements
Benchmarks where performance **increased** beyond the threshold.

**Example:**
```
Benchmark: streams
Baseline: 50000 MB/s
Nightly:  55000 MB/s
Change:   +10.0% (Improvement)
```

**Action:** Validate improvement is real (not measurement error), document in release notes.

#### Missing Benchmarks
Benchmarks present in baseline but **absent** from nightly.

**Example:**
```
Benchmark: pyperf
Baseline: 1.5 seconds
Nightly:  (not run)
Status:   REMOVED
```

**Action:** Check if test was intentionally removed, verify CI configuration, investigate failures.

#### New Benchmarks
Benchmarks **absent** from baseline but present in nightly.

**Example:**
```
Benchmark: specjbb
Baseline: (not run)
Nightly:  5000 ops/sec
Status:   ADDED
```

**Action:** Review if expected, validate results, consider adding to baseline for future comparisons.

### 4. Summary Metrics

Track mode provides high-level metrics:

- **Total Benchmarks**: All benchmarks in comparison
- **Changed**: Benchmarks with different values (changed status)
- **Regressions**: Subset of changed that exceed regression threshold
- **Improvements**: Subset of changed that exceed improvement threshold
- **Regression Rate**: Percentage of changed benchmarks that are regressions
- **Added**: New benchmarks not in baseline
- **Removed**: Baseline benchmarks missing from nightly

**Example Summary:**
```
Total: 100 benchmarks
Changed: 25 (25%)
  - Regressions: 3 (12% of changed)
  - Improvements: 5 (20% of changed)
  - Neutral changes: 17
Added: 2
Removed: 1
Unchanged: 72
```

## Baseline Configuration Best Practices

### Choosing a Baseline Window

**Short window (1-7 days):**
- Pro: Recent, representative of current state
- Con: May include anomalies or incomplete coverage
- Use for: Sprint-to-sprint comparisons, rapid iteration

**Medium window (2-4 weeks):**
- Pro: Smooths out daily variance, good coverage
- Con: May include some instability
- Use for: Release-to-release comparisons, stable baselines

**Long window (1-3 months):**
- Pro: Very stable, comprehensive coverage
- Con: May be outdated, less representative
- Use for: Major version comparisons, long-term trends

### Baseline Stability Criteria

A good baseline should:
1. **Pass consistently**: Filter to PASS status only
2. **Cover all benchmarks**: Run full suite, not subset
3. **Stable environment**: Same hardware, OS, configuration
4. **Sufficient samples**: Multiple runs per benchmark (≥3 preferred)
5. **No known issues**: No active bugs or infrastructure problems

### Baseline ID Naming Conventions

Use descriptive, versioned naming:

**Good:**
- `rhel-9.5-ga` - Clear version, milestone
- `sprint-23-stable` - Sprint number, indicates stability
- `2025-01-baseline` - Date-based for monthly snapshots
- `v9.5.0-rc2` - Specific release candidate

**Bad:**
- `baseline` - Not descriptive, hard to track
- `test` - Ambiguous purpose
- `jan` - Unclear which year, too vague

### Updating Baselines

When to update your baseline:

1. **After a release**: New GA becomes new baseline
2. **Sprint boundaries**: End of sprint if stable
3. **Major improvements**: After validated performance wins
4. **Infrastructure changes**: After hardware/config updates

**Migration pattern:**
```bash
# Old baseline (keep for reference)
TRACK_BASELINE_ID=rhel-9.4-ga
TRACK_BASELINE_START_DATE=2024-11-01T00:00:00
TRACK_BASELINE_END_DATE=2024-11-30T23:59:59

# New baseline (after 9.5 GA)
TRACK_BASELINE_ID=rhel-9.5-ga
TRACK_BASELINE_START_DATE=2025-01-01T00:00:00
TRACK_BASELINE_END_DATE=2025-01-31T23:59:59
```

## Exception Interpretation Guidelines

### When to Act on Regressions

**Immediate action required:**
- Regression > 20%
- Critical benchmark (boot time, throughput, latency)
- Multiple related benchmarks regressing
- Regression in release candidate

**Investigate when convenient:**
- Regression 5-10%
- Single isolated benchmark
- Known noisy benchmark
- Non-critical workload

**Monitor but don't panic:**
- Regression < 5%
- Benchmark has high variance
- Single occurrence (not persistent)
- Already under investigation

### When to Celebrate Improvements

**Validate and document:**
- Improvement > 10%
- Unexpected improvement (no recent optimizations)
- Critical benchmark improvement
- Multiple related benchmarks improving

**Expected improvements:**
- After optimization work
- Following known fix
- Hardware upgrade
- Configuration tuning

### Handling Missing Benchmarks

**Red flags:**
- Critical benchmarks missing
- Multiple benchmarks from same suite missing
- No explanation for removal

**Acceptable:**
- Deprecated benchmark intentionally removed
- Test moved to different suite
- Known infrastructure issue (with ticket)

### Handling New Benchmarks

**Validate:**
- Results look reasonable
- Matches expected performance characteristics
- Properly configured and documented

**Red flags:**
- Unexpected benchmark appears
- Results seem anomalous
- No documentation or rationale

## Automated Workflows

### Daily Morning Report

Configure scheduler to run at 6 AM:

```bash
TRACK_SCHEDULER_ENABLED=true
TRACK_SCHEDULER_HOUR=6
TRACK_SCHEDULER_MINUTE=0
```

Results available in:
- **UI**: Navigate to Track mode to see latest comparison
- **JSON**: `track_results/comparison_{baseline_id}_{timestamp}.json`
- **Logs**: `track_results/execution_log.jsonl`

### CI/CD Integration

Use on-demand execution in CI pipeline:

```python
from src.track_scheduler import get_scheduler
from src.track_kpis import BaselineConfig
from datetime import datetime

# Configure baseline
baseline_config = BaselineConfig(
    baseline_id="ci-baseline",
    date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
    benchmark_filter=None,
)

# Run comparison
scheduler = get_scheduler(opensearch_client)
result = scheduler.run_on_demand_comparison(baseline_config)

# Check for regressions
if result.summary['regressions'] > 0:
    print(f"FAIL: {result.summary['regressions']} regressions detected")
    exit(1)
else:
    print("PASS: No regressions detected")
    exit(0)
```

### Weekly Summary Report

Parse execution log for weekly trends:

```bash
# Extract last week's results
grep "$(date -d '7 days ago' +%Y-%m)" track_results/execution_log.jsonl | \
  jq -r '[.timestamp, .regressions, .total_benchmarks] | @csv'
```

## Troubleshooting

### Empty Baseline

**Symptom:** "Baseline dataset is empty"

**Causes:**
- Date range doesn't match any data
- Filters too restrictive
- OpenSearch connectivity issue

**Solutions:**
1. Verify date range covers actual test runs
2. Check OpenSearch connection
3. Remove or relax filters
4. Verify index contains data for that period

### All Benchmarks Marked as Regressions

**Symptom:** Every benchmark shows regression

**Causes:**
- Baseline and nightly are swapped
- Measurement units changed
- Infrastructure change (different hardware)

**Solutions:**
1. Verify baseline is older than nightly
2. Check for schema changes
3. Review recent infrastructure changes
4. Recalibrate baseline if environment changed

### No Exceptions Showing

**Symptom:** All benchmarks show "unchanged"

**Causes:**
- Baseline and nightly are identical (same data)
- Results are genuinely stable
- Regression thresholds too high

**Solutions:**
1. Verify nightly data is actually new
2. Check if runs are happening
3. Review regression threshold settings
4. Confirm comparison is working correctly

### High Variance in Results

**Symptom:** Results fluctuate wildly between runs

**Causes:**
- Insufficient samples in baseline
- Noisy benchmark
- Infrastructure instability
- Thermal throttling or resource contention

**Solutions:**
1. Increase baseline window to get more samples
2. Exclude known noisy benchmarks
3. Investigate infrastructure stability
4. Use median instead of mean (future enhancement)

## Integration with Other Modes

### Pulse Mode
- **Purpose**: Executive overview, coverage tracking
- **Transition**: Click "Track" to drill into exceptions
- **Use together**: Pulse for health check, Track for detailed triage

### Investigate Mode
- **Purpose**: Deep-dive into specific benchmarks
- **Transition**: Click on exception to investigate
- **Use together**: Track identifies issues, Investigate analyzes root cause

## Advanced Topics

### Custom Regression Thresholds

Regression detection uses test-specific thresholds (see `src/regression_detection.py`):

```python
# Default threshold: 5% degradation
# Some benchmarks have custom thresholds:
- coremark: 3% (low variance, tight threshold)
- pyperf: 10% (higher variance, looser threshold)
```

To customize, modify `is_regression_for_test_name()` in `regression_detection.py`.

### Filtering by Benchmark Suite

Apply filters to focus on specific suites:

```python
baseline_config = BaselineConfig(
    baseline_id="coremark-baseline",
    date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
    benchmark_filter={
        "test.name.keyword": ["coremark", "coremark_pro"]
    }
)
```

### Multi-Baseline Comparison

Compare against multiple baselines:

1. Run Track mode with baseline A (e.g., RHEL 9.4)
2. Export results
3. Run Track mode with baseline B (e.g., RHEL 9.5 RC1)
4. Compare delta changes between baselines

## References

- **Implementation**: `src/track_kpis.py` - Delta calculation logic
- **Scheduler**: `src/track_scheduler.py` - Automated execution
- **UI Components**: `src/track_ui.py` - Track mode interface
- **Query Service**: `src/query_service.py` - Baseline comparison queries
- **Regression Detection**: `src/regression_detection.py` - Threshold logic
- **Tests**: `tests/test_track_kpis.py`, `tests/test_track_scheduler.py`

## FAQ

**Q: How often should I run Track mode comparisons?**

A: For active development, daily (automated via scheduler). For stable releases, weekly or on-demand when investigating issues.

**Q: What if my baseline is outdated?**

A: Update your baseline after major milestones (releases, sprint boundaries). Keep old baseline configs for historical comparison.

**Q: Can I compare across different OS versions?**

A: Yes, but ensure benchmarks are comparable. Some benchmarks may not exist in both versions.

**Q: How do I handle benchmarks that only run on specific hardware?**

A: Use `benchmark_filter` to scope comparisons to compatible configurations, or accept "missing" status for hardware-specific tests.

**Q: What's the difference between Track mode and Pulse mode?**

A: Pulse shows overall health and coverage (executive view). Track shows exceptions and deltas (engineering view).

**Q: Can I export Track mode results?**

A: Yes, results are automatically persisted to `track_results/` as JSON files. Parse with any JSON tool.
