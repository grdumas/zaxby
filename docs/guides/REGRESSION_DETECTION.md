# Regression detection — draft

**Status:** Draft (Phase 0, P0-E)  
**Companion:** [COMPARISON_POLICY.md](COMPARISON_POLICY.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §2.5, [DASHBOARD_REDESIGN_AND_DATA_PLAN.md](DASHBOARD_REDESIGN_AND_DATA_PLAN.md) §8–9  

This document specifies **thresholds**, **directionality**, and **status handling** for labeling performance regressions in line with `BenchmarkDataProcessor` in `src/data_processing.py`. Product still sets final numbers; this draft is enough to write tests and a future dedicated module (see P1-D in the implementation plan).

**Rule:** Do not ship UI that labels “regression” for end users until acceptance criteria here (or a superseding product sign-off) are implemented and covered by tests.

---

## 1. Role of `BenchmarkDataProcessor`

The processor flattens OpenSearch documents into a DataFrame and resolves a scalar **`primary_metric_value`** per row. Regression logic in the current codebase operates on that column.

### 1.1 Primary metric resolution

`_resolve_primary_metric()` chooses a numeric value in order: `results.primary_metric.value`, then lookup by `primary_metric.name` in `results.runs[*].metrics`, then test-specific keys from `PRIMARY_METRIC_FALLBACK_KEYS` in `src/metric_registry.py` (Phase 1, P1-E; e.g. `pyperf` → `mean`, `streams` → triad throughput keys). See:

```49:91:src/data_processing.py
    def _resolve_primary_metric(
        self,
        primary_metric: Any,
        run_0_metrics: Dict[str, Any],
        test_name: Optional[str],
    ) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        ...
```

If resolution fails, `primary_metric_value` may be **null**; regression math must define behavior (§5).

#### 1.1.1 Canonical `test.name` → run-metric keys

Authoritative data structure: `PRIMARY_METRIC_FALLBACK_KEYS` in `src/metric_registry.py`. Helper: `fallback_keys_for_test(test_name)`. Summary:

| test.name | Run metric keys (order tried in `results.runs[*].metrics`) |
|-----------|------------------------------------------------------------|
| `coremark` | `iterations_per_second`, `score` |
| `coremark_pro` | `multicore_score`, `SUMM_CPU` |
| `streams` | `triad__mb_per_sec`, `triad_mb_per_sec`, `add__mb_per_sec` |
| `auto_hpl` | `gflops` |
| `specjbb` | `MULTICORE_THROUGHPUT` |
| `sysbench` | `events_per_second`, `total_events` |
| `fio` | `read_iops`, `write_iops`, `read_bw`, `write_bw` |
| `uperf` | `throughput_gbps`, `throughput_mb_per_sec` |
| `passmark` | `cpu_mark`, `mark` |
| `phoronix` | `result`, `value` |
| `pyperf` | `mean` |

Benchmarks not listed rely on `primary_metric` / run metrics only (no test-specific fallback list).

### 1.2 Percent change (current implementation)

For paired OS / hardware comparisons, percent change is:

\[
\text{pct\_change} = \frac{\text{candidate\_mean} - \text{baseline\_mean}}{\text{baseline\_mean}} \times 100
\]

**Interpretation:** positive **pct_change** means the candidate mean is **higher** than the baseline mean. Whether that is “good” or “bad” depends on **directionality** (§3). The code paths below compare `pct_change` to a **negative** threshold for “regression” when **higher is better** (see §3.1).

Relevant implementations:

- `_compare_two_versions()` — same `test_name`, matching `cloud_provider` + `instance_type` across baseline and candidate OS versions; skips zero or NaN baselines:

```699:722:src/data_processing.py
                if len(baseline_hw_data) > 0 and len(comparison_hw_data) > 0:
                    baseline_mean = baseline_hw_data.mean()
                    comparison_mean = comparison_hw_data.mean()
                    if pd.isna(baseline_mean) or pd.isna(comparison_mean):
                        continue
                    if baseline_mean == 0:
                        continue
                    pct_change = ((comparison_mean - baseline_mean) / baseline_mean) * 100
                    ...
                        'is_regression': pct_change < regression_threshold
```

- `analyze_os_version_regressions()` — sequential version pairs; **does not** require hardware matching across arbitrary rows (aggregates all rows for that test/version):

```829:842:src/data_processing.py
                if len(baseline_data) > 0 and len(current_data) > 0:
                    baseline_mean = baseline_data.mean()
                    current_mean = current_data.mean()
                    pct_change = ((current_mean - baseline_mean) / baseline_mean) * 100
                    ...
                        'is_regression': pct_change < regression_threshold
```

- `calculate_comparison()` — uses the same percent-change formula and applies **fixed band** labels for “Regression” / “Improvement” / “Stable” (§2.2).

---

## 2. Thresholds (draft defaults aligned with code)

| Symbol | Default | Where used | Meaning |
|--------|---------|------------|---------|
| `REGRESSION_THRESHOLD_REL` | **-5.0** | `analyze_rhel_simplified_regressions`, `analyze_os_version_regressions`, `_compare_two_versions` via `regression_threshold` | For **higher-is-better** metrics: candidate is flagged as regression if `pct_change < -5%`. |
| `STABILITY_BAND_PCT` | **10.0** | `calculate_comparison` → `change_category` | `pct_change < -10` → “Regression”; `> +10` → “Improvement”; else “Stable”. |

**Inconsistency note:** `-5%` vs `-10%` bands coexist today (`regression_threshold` vs `change_category`). Product should either unify or document which surface uses which. Tests for “regression” labels should assert the intended threshold **per view**.

**Future:** statistical tests, minimum sample size (`baseline_count` / `comparison_count`), and use of `baseline_std` are **not** implemented in the flag above; see §6.

---

## 3. Directionality per `test.name` / unit

### 3.1 Convention in current code

The existing `is_regression` checks use **`pct_change < regression_threshold`** with **negative** thresholds (e.g. -5). That assumes **higher primary metric value is better** (throughput, score, marks). **Lower-is-better** metrics (e.g. latency seconds, some duration) would invert the inequality; the current generic paths do **not** invert automatically.

### 3.2 Draft direction table (to be confirmed by product)

| Kind | Examples (`test.name` or family) | Better direction | Regression when (using pct_change as in §1.2) |
|------|-----------------------------------|------------------|-----------------------------------------------|
| Throughput / score | `streams`, `coremark`, `pyperf`, `uperf`, `sysbench`, `specjbb`, `auto_hpl`, `passmark` | Higher | `pct_change < -T` |
| Storage IOPS / BW | `fio` (read/write iops/bw) | Higher | `pct_change < -T` |
| Latency / time | *(if primary is latency)* | Lower | `pct_change > +T` (invert) |

**Action:** maintain a **metric registry** (P1-E) mapping `test.name` + `primary_metric.name` → `{higher_better: bool}` and apply in one place before labeling.

---

## 4. `results.status` — PASS / UNKNOWN / FAIL (draft policy)

**Current behavior:** `documents_to_dataframe()` copies `results.status` to column `status`. Regression functions shown in §1.2 **do not filter** on `status` before computing means.

**Draft policy for labeled regressions**

| Status | Include in default regression math? | Notes |
|--------|-----------------------------------|--------|
| PASS | Yes | Default participating row. |
| UNKNOWN | No (default) | Exclude from means unless user opts in to “include incomplete runs.” |
| FAIL | No (default) | Exclude; may still appear in raw Investigate tables. |
| (missing) | Treat as UNKNOWN | Explicit handling in aggregation layer. |

Implementations should log counts of excluded rows per cohort when status filtering is added.

---

## 5. Missing or invalid primary metric

| Condition | Draft behavior |
|-----------|----------------|
| `primary_metric_value` null / NaN for a row | Exclude row from means; if a cohort has **no** valid rows after exclusion, **no** regression label for that cohort. |
| `baseline_mean == 0` | Skip comparison (`_compare_two_versions` already skips). |
| Mismatched units between baseline and candidate | Do not compute until registry validates unit compatibility. |

---

## 6. Acceptance criteria (for implementers and tests)

1. **Threshold:** For a given surface, tests assert one explicit threshold (e.g. -5% vs -10%) and the same formula as §1.2.  
2. **Directionality:** For at least one lower-is-better fixture, tests assert inverted regression logic once the registry exists.  
3. **Status:** Rows with FAIL/UNKNOWN are excluded from default regression aggregation when policy in §4 is enabled.  
4. **Hardware matching:** Templates that require same hardware (`TPL_RHEL_MINOR_SAME_HW`) align with `_compare_two_versions` pairing behavior; sequential `analyze_os_version_regressions` behavior is documented as **looser** and may not be used for the same claims without filtering.  
5. **Traceability:** Any surfaced regression links to raw OpenSearch data per P0-D / P1-D (document id or scoped query).

---

## 7. Revision log

| Date | Change |
|------|--------|
| 2026-04-06 | Initial draft: thresholds, directionality table, status handling, tie-in to `BenchmarkDataProcessor` |
| 2026-04-12 | P1-E: primary metric registry in `src/metric_registry.py`; §1.1.1 table |
