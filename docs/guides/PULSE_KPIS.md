# Pulse KPI definitions (P2-A)

**Status:** Draft — engineering catalog; **product must confirm** metric correctness and what executives should see.  
**Code:** `src/pulse_kpis.py` (`PulseKpiBundle`, `PULSE_KPI_DEFINITION_VERSION`), `src/query_service.py` (OpenSearch bodies), overview UI in `app.py` (`update_server_snapshot`).  
**Policy:** All Pulse aggregations validate against `TPL_CATEGORY_ROLLUP` via `validate_pulse_request` (index-wide descriptive counts, not baseline-vs-candidate cohort comparisons). See `docs/guides/COMPARISON_POLICY.md` §3.

---

## Bundle contents

| ID | Name | What it measures | OpenSearch / synthetic source |
|----|------|------------------|------------------------------|
| `KPI_PULSE_INDEX_TOTAL` | Results overview | Total hit count on `zathras-results` and document counts **per** `metadata.cloud_provider` (descriptive only). | `build_results_overview_aggregation_body` — `terms` on `metadata.cloud_provider.keyword`; synthetic: groupby on `cloud_provider`. |
| `KPI_PULSE_CATEGORY_MIX` | Benchmark mix by category | Documents **per dashboard category**, derived by mapping each `test.name` through `data/benchmark_categories.json` (`category_for_test_name`). | `build_results_test_name_terms_aggregation_body` — bounded `terms` on `test.name.keyword`, then rollup in `parse_test_name_buckets_to_category_counts`; synthetic: same mapping on loaded `test_name`. |
| `KPI_PULSE_ACTIVITY_MONTHLY` | Activity by month | Count of documents per **calendar month** by run timestamp. | `build_results_monthly_activity_histogram_body` — `date_histogram` on `metadata.test_timestamp` (`calendar_interval: 1M`); synthetic: `timestamp` column month buckets. |
| `KPI_PULSE_SCOPE` | Scope footnote | Min/max run date (UTC) and count of documents with a value on the timestamp field (`stats` on OpenSearch; aligns with P2-C soundbite metadata). | `build_results_run_timestamp_stats_body`; synthetic: min/max of parseable `timestamp`. |

---

## Review checklist (product / exec)

1. **Field correctness** — Confirm `metadata.test_timestamp`, `metadata.cloud_provider`, and `test.name` mappings match operational expectations for the connected cluster.
2. **Category mapping** — Categories depend on `benchmark_categories.json`; unlisted tests appear under **Other** by design.
3. **Executive narrative** — These KPIs describe **volume and coverage**, not regression or cross-provider performance. Any future “health” or delta KPIs need separate templates and policy review.
4. **Versioning** — When aggregation semantics change, bump `PULSE_KPI_DEFINITION_VERSION` in `src/pulse_kpis.py` and update this document.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-04-16 | Initial P2-A catalog tied to `PulseKpiBundle` |
