# Agent handoff — Phase 1 (dashboard redesign)

**For:** The next engineer or AI agent implementing **Phase 1** of the RHEL Multi-Architecture Performance Dashboard redesign.  
**Assumes:** **Phase 0** is complete (see `IMPLEMENTATION_PLAN.md` §2–2.6 on `main`).

---

## 1. Read first (in order)

1. **[DASHBOARD_REDESIGN_AND_DATA_PLAN.md](DASHBOARD_REDESIGN_AND_DATA_PLAN.md)** — Product context, two-index model (`zathras-results` vs `zathras-timeseries`), Pulse / Investigate / Track, partner constraints.
2. **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** — §3 Phase 1 work packages (P1-A–P1-F), exit criteria, testing strategy §6, suggested sequencing §8.
3. **[COMPARISON_POLICY.md](COMPARISON_POLICY.md)** — Template IDs, Pulse forbidden axes, validation contract.
4. **[REGRESSION_DETECTION.md](REGRESSION_DETECTION.md)** — Thresholds, directionality; required before **shipping** user-visible “regression” labels.

---

## 2. What Phase 0 already delivered (do not redo)

| Area | Location |
|------|----------|
| Dual-index env + client routing | `src/opensearch_client.py` — `search_results`, `search_timeseries`, `scroll_results`, `fetch_timeseries_for_document` |
| Bounded aggregation prototype | `src/query_service.py` — `fetch_results_overview_aggregates`; `app.py` server snapshot callback (not `dcc.Store`-driven for that panel) |
| Discover deep links | `src/opensearch_links.py` — run-level `metadata.document_id`; timeseries `metadata.timeseries_id` helper |
| Template / Pulse allowlist (code) | `src/comparison_policy.py` — `validate_comparison_request`; extend with **params** in Phase 1 |

**Global rule from `IMPLEMENTATION_PLAN.md`:** Do **not** ship UI that labels **“regression”** until `REGRESSION_DETECTION.md` criteria are implemented **and** covered by tests.

---

## 3. Phase 1 work packages (primary reference: `IMPLEMENTATION_PLAN.md` §3.1)

| ID | Focus | Notes |
|----|--------|--------|
| **P1-A** | Template engine | Map UI investigation → `template_id` + params; build OpenSearch queries from template; reject invalid combos. |
| **P1-B** | Policy enforcement | Pulse vs Investigate; tests that Pulse cannot emit forbidden comparisons (e.g. cross–public-cloud per `COMPARISON_POLICY`). |
| **P1-C** | Category → leaf | `test.name` → category mapping (config/JSON); UI breadcrumbs / drill to leaf benchmarks. |
| **P1-D** | Regression surfacing | Implement `REGRESSION_DETECTION.md` in processor or dedicated module; labels + deep links only when spec is met. |
| **P1-E** | Metric registry | Formalize `_resolve_primary_metric` per `test.name`; document in `REGRESSION_DETECTION` or `SCHEMA.md`. |
| **P1-F** | OpenSearch load failure UX | If `DATA_MODE=opensearch` and load fails: **no silent fallback** to synthetic; explicit error + opt-in to synthetic. **Independent** of other P1 items; can be its own PR. |

**Suggested sequencing (illustrative, from plan §8):** P1-A, P1-B, P1-E → then P1-C, P1-D; P1-F can slot in parallel (e.g. S4b).

---

## 4. Known technical debt (context only)

- Most of the app still loads a **capped scroll** of results into **`dcc.Store`** for filtering — scaling work continues in later phases.
- **`load_initial_benchmark_documents()`** in `src/data_bootstrap.py` (wired from `app.py`): when `DATA_MODE=opensearch`, **no silent synthetic fallback** unless `ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE=1` — **P1-F** complete.

---

## 5. Repository conventions (must follow)

- **Documentation:** New technical docs in `docs/guides/`; update `docs/README.md` index. Do **not** add arbitrary `.md` files in repo root (see `.cursorrules`).
- **PR / branch naming:** Use **descriptive** branch names (`feat/template-engine-investigate`, `fix/opensearch-load-error-ux`). Avoid reusing **P0-A / P1-B**-style IDs in PR **titles** if they collide with older merged PRs — put work-package IDs in the **description** if needed.
- **Tests:** `pytest`; mock OpenSearch in unit tests; add policy tests when building Pulse query builders.
- **Commits:** Descriptive messages; AI attribution if assisted (see `README.md`).

---

## 6. Paste-ready prompt (open a new session with this)

Use the block below as the **first user message** to the next agent (edit branch/PR context if needed):

```text
You are working on Phase 1 of the Zaxby (RHEL Multi-Arch Performance) Dash dashboard redesign.

Ground truth:
- Read docs/guides/DASHBOARD_REDESIGN_AND_DATA_PLAN.md, docs/guides/IMPLEMENTATION_PLAN.md §3 (Phase 1), docs/guides/COMPARISON_POLICY.md, and docs/guides/REGRESSION_DETECTION.md.
- Phase 0 is done: dual-index client (src/opensearch_client.py), query_service + server snapshot (src/query_service.py, app.py), opensearch_links, comparison_policy.

Constraints:
- Do not ship user-visible “regression” labels until REGRESSION_DETECTION.md is implemented and tested (IMPLEMENTATION_PLAN dependency rule).
- Follow .cursorrules for docs paths and repo hygiene.
- Use descriptive branch names; avoid confusing P1-* IDs in PR titles.

Task:
- [Describe the specific Phase 1 slice: e.g. “Implement P1-F OpenSearch load failure UX” or “Start P1-A template engine for investigations”.]
- Work on a single focused branch; run pytest before opening a PR.
```

---

## 7. Revision log

| Date | Change |
|------|--------|
| 2026-04-11 | Initial handoff after Phase 0 exit criteria recorded in IMPLEMENTATION_PLAN.md |
