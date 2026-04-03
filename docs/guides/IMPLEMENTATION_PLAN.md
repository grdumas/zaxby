# Dashboard Redesign — Implementation Plan

**Status:** Draft — execution roadmap  
**Umbrella:** [DASHBOARD_REDESIGN_AND_DATA_PLAN.md](DASHBOARD_REDESIGN_AND_DATA_PLAN.md)  
**Last updated:** 2026-04-01  

This document turns the umbrella strategy into **ordered work packages**, **exit criteria**, and **file-level touchpoints**. It does not replace product sign-off on comparison templates or regression thresholds; those live (or will live) in `COMPARISON_POLICY.md` and `REGRESSION_DETECTION.md` once authored.

---

## 1. Dependency overview

```text
COMPARISON_POLICY (templates + allowlist)     REGRESSION_DETECTION (spec)
           \                                           /
            v                                         v
    OpenSearch: dual index + routing    <--->    Metric registry / directionality
            |                                         |
            v                                         v
    Server-side query + aggregation layer    -->    Tests (policy + math)
            |
            +--> Deep link utility (OpenSearch Discover / doc id)
            |
            +--> Dash: Pulse prototype (server callbacks)
            |
            +--> Dash: Investigate (templates, pagination, drill-down)
            |
            v
         Phase 2–3: KPI UX, Track/CPT, caching, load tests
```

**Rule:** Do not ship UI that labels “regression” until **REGRESSION_DETECTION** acceptance criteria exist and are covered by tests.

---

## 2. Phase 0 — Platform prerequisites

**Goal:** Two-index awareness, bounded payloads, policy artifacts started, one vertical slice (deep link) proven.

### 2.1 Work package P0-A — Configuration and documentation

| Item | Action |
|------|--------|
| `.env.example` | Add `OPENSEARCH_INDEX_RESULTS` (`zathras-results`) and `OPENSEARCH_INDEX_TIMESERIES` (`zathras-timeseries`); keep legacy `OPENSEARCH_INDEX` as optional alias for results during migration. |
| `README.md` / `QUICKSTART.md` | Document dual-index expectation and migration from single-index setups. |
| `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md` | Update index list and when to query which index. |

**Exit:** New clone can point at both indices without ambiguity; docs describe routing intent.

### 2.2 Work package P0-B — OpenSearch client refactor

**Primary file:** `src/opensearch_client.py`

| Deliverable | Notes |
|-------------|--------|
| Named index resolution | Resolve results vs timeseries from env; single `BenchmarkDataSource` or small facade that exposes `client`, `results_index`, `timeseries_index`. |
| `search_results(body)` / `search_timeseries(body)` | Thin wrappers that apply correct index name; avoid scattering string literals. |
| `get_all_documents` | Deprecate or restrict: default cap, or rename to `scroll_results` with explicit max; **never** use for timeseries bulk load in app startup. |
| Point query helper | e.g. `fetch_timeseries_for_document(document_id, …)` with required filters + size limit. |

**Exit:** Unit tests with mocked OpenSearch verify index name on `search` calls; no code path loads full timeseries index into memory for “init”.

### 2.3 Work package P0-C — Server-side data path (prototype)

**Primary files:** `app.py`, `src/data_processing.py` (or new `src/query_service.py` if you want a clean seam)

| Deliverable | Notes |
|-------------|--------|
| One **server-side** aggregation or filtered query | e.g. small KPI or count-by-field for Pulse prototype — OpenSearch `search` with `size: 0` + `aggs`, or filtered query returning **bounded** hits. |
| Dash callback pattern | Callback reads aggregated JSON from server function, **not** from a preloaded multi-thousand-row `dcc.Store` for that view. |
| Investigate pagination contract | Define max `size`, `search_after` or offset strategy for large result sets. |

**Exit:** Demonstrate one view where expanding data volume does not linearly grow browser payload for that view.

### 2.4 Work package P0-D — Deep links

**New module (suggested):** `src/opensearch_links.py` (or under `src/opensearch_client.py`)

| Deliverable | Notes |
|-------------|--------|
| `opensearch_discover_url(index, document_id)` or query-string builder | Use base URL from env (`OPENSEARCH_DASHBOARDS_BASE_URL` or cluster URL pattern — **document chosen convention** in README). |
| Wire **one** chart/table row | “View in OpenSearch” for `zathras-results`; optional second for `zathras-timeseries` by `timeseries_id`. |

**Exit:** Click-through works from a real row; link format documented for operators.

### 2.5 Work package P0-E — Policy artifacts (minimal)

| Deliverable | Owner | Notes |
|-------------|--------|--------|
| `docs/guides/COMPARISON_POLICY.md` | Product + perf | **10–15** templates: fixed dimensions per template, baseline/candidate language, explicit **Pulse** forbidden axes (e.g. no cross–public-cloud). |
| `docs/guides/REGRESSION_DETECTION.md` | Eng + product | Thresholds, directionality per `test.name`/unit, UNKNOWN/FAIL handling; reference `BenchmarkDataProcessor` behavior. |

**Exit:** Implementers can code `validate_comparison_request(template_id, params)` and tests against a closed set of templates.

### 2.6 Phase 0 exit criteria (all must pass)

- [ ] Both indices configurable; client routes queries by intent.
- [ ] No startup load of full `zathras-timeseries`.
- [ ] At least one server-driven aggregation or bounded query path in the app (prototype).
- [ ] At least one working OpenSearch deep link from the UI.
- [ ] `COMPARISON_POLICY.md` and `REGRESSION_DETECTION.md` exist as **drafts** with enough detail to write tests.

---

## 3. Phase 1 — Trust, scope, Investigate

**Goal:** Template-driven investigations, category → leaf navigation, regression labels only per spec, partner guardrails in code.

### 3.1 Work packages

| ID | Package | Key actions |
|----|---------|-------------|
| P1-A | **Template engine** | Map UI “investigation” to a template id + parameters; backend builds OpenSearch query from template; reject invalid combos. |
| P1-B | **Policy enforcement** | Central module: Pulse vs Investigate allowed templates; pytest: Pulse cannot request cross-cloud comparisons. |
| P1-C | **Category → leaf** | Data: test-name → category mapping (config or small JSON); UI: breadcrumb or nested nav; charts drill to leaf benchmarks. |
| P1-D | **Regression surfacing** | Implement `REGRESSION_DETECTION.md` in `BenchmarkDataProcessor` (or dedicated module); wire labels only when criteria met; each label links via P0-D. |
| P1-E | **Metric registry** | Formalize what `_resolve_primary_metric` does per `test.name`; document in `REGRESSION_DETECTION` or `SCHEMA.md` appendices. |

**Exit:** Investigate flows use templates; forbidden comparisons are impossible via Pulse API; regressions are defined and testable.

---

## 4. Phase 2 — Pulse (executive)

**Goal:** KPI surfaces using **only** aggregation contracts from Phase 0–1; exec-safe copy and disclaimers.

| ID | Package | Key actions |
|----|---------|-------------|
| P2-A | **KPI definitions** | Small set of aggregations (by category, by trend window) — all from `zathras-results` initially. |
| P2-B | **Pulse layout** | Default landing: KPI cards + trend sparklines; no raw filter combinatorics. |
| P2-C | **Soundbite metadata** | Store baseline id, date range, benchmark count on any narrative snippet to avoid overclaiming. |

**Exit:** Exec persona can complete primary workflow without advanced filters; KPIs cite scope.

---

## 5. Phase 3 — Track / CPT and scale

**Goal:** Exception-oriented views, performance and operational hardening.

| ID | Package | Key actions |
|----|---------|-------------|
| P3-A | **Baseline vs last night** | Scheduled or on-demand aggregation queries; optional rollup index (future). |
| P3-B | **Caching** | TTL for expensive aggregations; invalidate on date range change. |
| P3-C | **Load / performance tests** | Scripted queries against timeseries volume; define P95 targets in `REGRESSION_DETECTION` or NFR appendix. |
| P3-D | **Synthetic data** | Extend `src/synthetic_data.py` (and fixtures) to cover timeseries shapes for offline tests. |

---

## 6. Testing strategy (cross-cutting)

| Layer | What to test |
|-------|----------------|
| **Unit** | Index routing; `validate_comparison_request`; metric directionality; regression delta math on fixed fixtures. |
| **Integration** | Mocked OpenSearch: assert query body contains expected filters and index name. |
| **Policy** | Pulse query builder never emits cross–public-cloud `terms` on `metadata.cloud_provider` with multiple providers (example rule — align with `COMPARISON_POLICY`). |
| **E2E (optional)** | Smoke: load Pulse, open one deep link (staging cluster). |

---

## 7. Risk register (implementation-focused)

| Risk | Mitigation |
|------|------------|
| Policy docs slip | Phase 0 **exit** is blocked without drafts; ship P0 with “draft” watermark if needed. |
| Dash callback complexity | Introduce small Python service layer callable from callbacks; consider FastAPI later without blocking P0. |
| Metric inconsistency | Registry + tests per `test.name` before wide regression labeling. |
| Operator URL patterns for deep links | Coordinate early; feature-flag link style if cluster uses different Discover base path. |

---

## 8. Suggested sequencing (sprints — illustrative)

| Sprint focus | P0 packages | Notes |
|--------------|-------------|--------|
| **S1** | P0-A, P0-B, start P0-E drafts | Config + client only; no UI change yet. |
| **S2** | P0-C, P0-D, finish P0-E | Vertical slice + policy drafts complete Phase 0. |
| **S3** | P1-A, P1-B, P1-E | Templates + enforcement. |
| **S4** | P1-C, P1-D | IA + regression labels. |
| **S5+** | P2*, P3* | Pulse then Track per product priority. |

Adjust lengths to team size; **P0 must complete** before treating Phase 1 as committed.

---

## 9. Document history

| Date | Change |
|------|--------|
| 2026-04-01 | Initial implementation plan aligned with `DASHBOARD_REDESIGN_AND_DATA_PLAN.md` |
