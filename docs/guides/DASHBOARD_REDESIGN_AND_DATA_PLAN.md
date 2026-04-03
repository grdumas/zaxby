# RHEL Multi-Architecture Performance Dashboard — Redesign & Data Strategy Plan

**Status:** Draft — for human and AI review  
**Branch:** `plan/dashboard-redesign-and-data-strategy`  
**Last updated:** 2026-04-01  

This document captures **product context**, **live OpenSearch findings**, a **proposed direction** for the dashboard (without committing to stack or implementation), and a **non-final** catalog of **comparison rules** to refine later. It exists so reviewers (including other models) can suggest improvements, risks, and missing requirements.

---

## 1. Purpose of this document

- Align stakeholders on **why** the product exists and **what constraints** are non-negotiable.
- Record **what data** is actually available in OpenSearch today (two indices, rough volumes, key dimensions).
- Propose a **high-level information architecture** (modes, deep linking, policy) independent of whether the app stays on Dash or moves to another stack.
- Defer **definitive comparison policy** to a later decision; **Section 7** only lists **plausible** comparison types and open policy questions.

**For AI reviewers:** Please flag gaps, internal contradictions, security/partner-policy risks, and technical feasibility. Suggest concrete acceptance criteria or phased milestones. If you invent org-specific details, label them explicitly as assumptions.

---

## 2. Product context

### 2.1 Name and mission

- Working product name: **RHEL Multi-Architecture Performance Dashboard**.
- Origin: Replace ad-hoc spreadsheets with a governed view over performance test results stored in OpenSearch.
- Core analytic question (historical): *Did performance regress, improve, or stay the same between X and Y?* (must remain answerable in some form.)

### 2.2 Stakeholders (summary)

| Group | Needs (summary) |
|-------|------------------|
| **Performance engineers** | Mixed seniority; focus areas include ARM, traditional datacenter, and RHEL in public cloud (AWS, Azure, GCP). Investigations drive bug filing more than “fires.” Most use the dashboard **outside meetings** unless actively investigating. They need **investigation-scoped** views: only the runs relevant to the question (e.g. RHEL 9.5 vs 9.6 on a defined suite; HT on/off for HPC; CPU generation vs generation). |
| **Executives / eng & product managers** | Technically literate but need **KPIs and trends**, not every benchmark. Must avoid **apples-to-oranges** comparisons. **Partner constraint:** do **not** compare public cloud providers to each other in ways that could harm partner relations. Want defensible **soundbites** when data supports them. |
| **Strong requirement (engineering)** | At least one senior stakeholder treats as **non-negotiable:** if the UI shows a **regression**, the user must be able to **navigate to raw data in OpenSearch** (document-level or point-level — see data section). |

### 2.3 Sacred cow: categories vs leaf benchmarks

Benchmarks may be rolled up to **high-level categories** (e.g. networking, HPC, memory, Python, Java, storage). Users must **always** be able to drill from category → **individual benchmarks** (leaf metrics), not only a rolled-up score.

---

## 3. Current implementation (high level, subject to change)

- Today the repo ships a **Python Dash** application with OpenSearch and synthetic modes.
- Documentation and env templates historically emphasized a **single** results index; production reality includes **two** indices (see below).
- The current UI is **filter-heavy** and loads a bounded batch of documents for client-side processing — **not** assumed to be the long-term architecture for large-scale or timeseries-heavy workloads.

**No commitment:** Framework, plugins, and language may change; the goal is a **functional product** meeting stakeholder needs.

---

## 4. OpenSearch data model (live cluster snapshot)

Observations below come from querying the **`zathras-results`** and **`zathras-timeseries`** indices (document counts and mappings are **point-in-time** and will drift).

### 4.1 `zathras-results` (canonical “run” documents)

- **Rough scale:** on the order of **thousands** of documents (e.g. ~4.3k at last check).
- **Grain:** One document per **logical test result** (`metadata.document_type`: `zathras_test_result`), with stable **`metadata.document_id`**.
- **Role:** Primary source for **comparisons**, **regression lists**, **investigation scoping**, and **run-level** deep links to OpenSearch.
- **Contents (conceptual):** `test`, `system_under_test`, `results` (including `primary_metric`, per-run nested metrics, optional summaries such as `timeseries_summary` where the pipeline rolled up points).

### 4.2 `zathras-timeseries` (exploded points / sub-metrics)

- **Rough scale:** on the order of **hundreds of thousands** of documents (e.g. ~242k at last check).
- **Grain:** Many documents per parent result — one row per **sequence / point** (e.g. `metadata.timeseries_id`, `metadata.sequence`); **`metadata.document_id`** links back to the parent result.
- **Role:** **Within-run** detail: sweeps, sub-benchmarks, per-point metrics (`results.point_metrics`, etc.). **Not** suitable for bulk load into the browser.
- **Deep linking:** Run-level links target **`zathras-results`**; point-level anomalies may link to **`zathras-timeseries`** by `timeseries_id` or document `_id`.

### 4.3 Design implications

| Concern | Direction |
|--------|-----------|
| **Exec / KPI / trend views** | Prefer aggregations and rollups from **`zathras-results`** (and/or future rollup indices), not full scans of timeseries. |
| **Engineer drill-down** | On-demand, **narrow** queries to **`zathras-timeseries`** (time bounds + `document_id` / `test` / `timeseries_id`). |
| **Traceability** | Two link patterns: **run** (results index) vs **point** (timeseries index). |
| **CPT / nightly growth** | Timeseries likely grows faster; “what changed last night?” should avoid pulling full timeseries client-side. |

---

## 5. Proposed information architecture (non-binding)

### 5.1 Modes (names indicative)

| Mode | Primary audience | Job |
|------|------------------|-----|
| **Pulse** (executive) | Leadership | Directional health: **small KPI set**, trends, safe narratives; **no** default cross–public-cloud comparison. |
| **Investigate** | Performance engineers | **Scoped** comparisons, tables and charts for one investigation; **mandatory** paths to OpenSearch raw data for regressions. |
| **Track** (optional phase) | CPT / release owners | Exceptions, deltas vs baseline / prior night; feeds off aggregated data. |

**Landing:** casual users land on **Pulse**; power users may bookmark **Investigate** with saved scopes.

### 5.2 Policy and UX

- **Comparison allowlist / blocklist** should be enforced in **logic and UI**, not only in prose (forbidden axes, e.g. public cloud A vs public cloud B for partner-sensitive views).
- **Baseline** and **candidate** (or time window) should be **explicit** in the UI so comparisons are explainable externally.

### 5.3 Stack note

A thin **API or query layer** that chooses index, aggregation, and **link shape** is compatible with staying on Python or moving to another frontend; the **split between results and timeseries** is the main structural driver.

---

## 6. Phasing (suggested)

1. **Trust and scope:** Investigation scoping, category → leaf drill-down, OpenSearch deep links for regressions, **comparison guardrails** (minimal allowlist first).
2. **Pulse:** KPI surfaces and executive-safe summaries on top of the same backend contracts.
3. **Track / CPT:** Exception feeds and performance optimizations (aggregations, caching, optional rollups).

---

## 7. Comparison rules — catalog only (not finalized)

**Explicitly kicking the can:** this section lists **plausible** comparison dimensions and patterns observed from **`zathras-results`** data. The team will **trim** to an allowlist/blocklist later. Nothing here is approval to implement a rule without product sign-off.

### 7.1 Dimensions observed in data (examples)

- **`metadata.cloud_provider`:** e.g. AWS, Azure, GCP (volumes skewed heavily to one provider in current samples).
- **`system_under_test.operating_system.version`:** e.g. multiple RHEL minors and some 10.x lines — primary axis for “RHEL A vs B” **when** test and hardware policy match.
- **`test.name`:** e.g. pyperf, coremark, streams, uperf, passmark, etc. — numeric comparison generally requires **same test** (and compatible metric).
- **`metadata.scenario_name`:** many values; includes large **`rhel_95*`** families on one cloud and **`az_*`** style names on another — **not** aligned across clouds by name alone.
- **`metadata.instance_type`:** many SKUs — comparisons often require **same instance** or a **documented equivalence** policy.
- **`system_under_test.hardware.cpu.architecture`:** e.g. x86_64 vs aarch64 — multi-arch story requires **explicit** rules (often different instance SKUs).
- **`results.status`:** PASS vs UNKNOWN/FAIL/etc. — policy needed for whether non-PASS rows participate in default comparisons.
- **Metrics:** `results.primary_metric` is heavily used for some suites (e.g. pyperf-shaped rows); other suites may rely on **nested** `runs` metrics — **one global scalar** is not guaranteed for all tests.

### 7.2 Plausible comparison *patterns* (to trim later)

**RHEL / OS**

- Same cloud, same instance (or policy-matched), same test, same scenario: RHEL **minor** A vs B.
- Same as above with **explicit** “equivalent instance” mapping.
- Trend: same scope across **time windows** (CPT drift).
- Same OS build, different **`metadata.iteration`:** repeatability / variance (not a “version” comparison).

**Benchmark / workload**

- Same `test.name` + same metric definition.
- Same `test.name`, different `metadata.scenario_name`:** valid for pyperf-style per-scenario micro-workloads; needs aggregation rules if rolled up.
- Different `test.name`:** only via **category rollups** with defined aggregation — not raw point-to-point.

**Hardware / capacity**

- Same `metadata.instance_type`, different RHEL: strong controlled comparison.
- Same family, different size: **scaling** analysis (distinct from OS regression).
- Different CPU generation at same nominal size: “gen uplift” — hold OS + test + scenario constant.
- Architecture or CPU vendor: **high risk**; only with explicit templates and documentation.

**Cloud / provider**

- **Within** a single `metadata.cloud_provider`: match other dimensions — generally the safe default.
- **Across** public cloud providers: **organizational policy** currently favors **not** presenting direct comparisons for partner reasons — treat as **blocked or exec-forbidden** until explicitly overridden.
- Different scenario **pipelines** (`rhel_95*` vs `az_*`) can be misread as “cloud vs cloud” if labeling is poor — **copy and UI structure** matter.

**Operational**

- Time cohorts (nightly vs manual) via timestamps.
- Metric directionality (higher vs lower better) per test/unit — must be part of regression math.

### 7.3 Open decisions (for a future rules workshop)

- Canonical **metric field** per `test.name` (primary vs nested).
- **Equivalence tables** for instance types across generations or sizes.
- Whether **cross-arch** comparisons are ever **auto-suggested** or only **manual** with warnings.
- Final **partner** wording and what is allowed in **Pulse** vs **Investigate**.

---

## 8. Success criteria (draft)

- An exec can grasp **directional** health vs an agreed baseline using **KPIs** without wading through global filters.
- An engineer can answer a **scoped** question with only relevant runs and open **OpenSearch** to the **correct** document (run or timeseries point) from any surfaced regression.
- Category rollups always expose a path to **leaf benchmarks**.
- The product does **not** default to **forbidden** comparison types (e.g. cross–public-cloud where policy says no).

---

## 9. Feedback requested from reviewers

- Missing **stakeholder** or **compliance** constraints.
- **Risks** in the two-index model (query cost, consistency, drift).
- **MVP** scope that preserves traceability and partner-safe Pulse with minimal engineering.
- Suggested **acceptance tests** or **metrics** for launch.

---

## Document history

| Date | Change |
|------|--------|
| 2026-04-01 | Initial draft on branch `plan/dashboard-redesign-and-data-strategy` |

---

## 10. Feedback / Review (AI Reviewer)

**Reviewer:** Gemini CLI (Model: Gemini 2.5 Pro)  
**Date:** 2026-04-01  
**Status:** Approved with Recommendations

### 10.1 Technical Evaluation Summary
The plan is highly effective in bridging high-level stakeholder needs with the technical realities of the OpenSearch data model. The persona-driven approach (Pulse vs. Investigate) correctly addresses the primary risk of "apples-to-oranges" comparisons for non-technical users while preserving deep-dive capabilities for engineers.

### 10.2 Strengths
- **Data Model Realism:** Correctly identifies the non-viability of bulk client-side processing for the `zathras-timeseries` index and proposes an aggregation-first strategy.
- **Policy-First Design:** Proactively addresses organizational risks regarding partner-sensitive data (cross-cloud comparisons) in the UI logic.
- **Traceability:** Upholds the "sacred cow" requirement for run-level deep links back to OpenSearch, ensuring the dashboard is actionable for bug-filing.

### 10.3 Gaps and Technical Risks
- **Index Routing:** Current implementation (`src/opensearch_client.py`) assumes a single index. Refactoring is required to handle the proposed two-index strategy (`results` vs. `timeseries`).
- **Comparison Complexity:** Implementing "equivalence tables" for hardware (e.g., matching AWS `m5` to Azure `Dsv3`) remains a significant manual data-modeling effort not yet reflected in the processing layer.
- **Information Architecture Shift:** The transition from "OS-first" views to "Category -> Leaf Benchmark" drill-downs will require a structural shift in the current Dash component hierarchy.

### 10.4 Alignment with Project Brief
The plan strictly adheres to the **Discovery-First** mandate by basing the IA on live cluster findings rather than assumptions. It fulfills the primary mission of regression detection while ensuring scalability for future CPT workloads.

### 10.5 Recommendations
1. **Refactor Data Source:** Update the OpenSearch client to support dynamic index routing based on the query type (Pulse/KPI vs. Investigate/Point).
2. **Formalize Equivalence:** Prioritize a "rules workshop" to define the minimal hardware equivalence allowlist for Phase 1 comparisons.
3. **Drill-down UI:** Implement a breadcrumb or nested navigation pattern to support the "Category -> Leaf" hierarchy without overwhelming the user with filters.

---

**Reviewer:** Claude Code (Model: Claude Sonnet 4.5)
**Date:** 2026-04-01
**Status:** Approved with Significant Implementation Concerns

### 10.6 Technical Architecture Review

This plan correctly identifies the core tensions (exec safety vs engineer flexibility, results vs timeseries scale) but underspecifies several implementation-critical areas that will block progress if deferred too long.

**Strengths:**
- **Data model discovery:** The two-index split is well-understood and drives sensible architectural choices (aggregations for Pulse, narrow queries for Investigate)
- **Stakeholder-driven modes:** The Pulse/Investigate/Track separation directly addresses the "apples-to-oranges" risk mentioned by leadership
- **Traceability requirement:** OpenSearch deep linking is non-negotiable and correctly preserved throughout
- **Partner policy awareness:** Proactively treats cross-cloud comparisons as forbidden by default

### 10.7 Critical Gaps

**1. Current Implementation Mismatch (High Priority)**

The existing codebase reveals architectural debt that directly conflicts with this plan:

- **Client-side processing:** Current `app.py` loads all data into `dcc.Store` (browser memory). This pattern:
  - Already struggles with 4.3k result documents in testing
  - Cannot scale to 242k timeseries documents under any scenario
  - Requires immediate refactor to server-side aggregation before multi-mode work begins

- **Single-index assumption:** `src/opensearch_client.py` hardcodes `OPENSEARCH_INDEX` env var. Index routing will require:
  ```python
  # Current: self.index_name = os.getenv('OPENSEARCH_INDEX')
  # Needed: route_index(query_type) -> 'zathras-results' | 'zathras-timeseries'
  ```

- **Metric resolution complexity:** The plan doesn't address that `_resolve_primary_metric()` already implements fallback logic for missing `results.primary_metric.value` (uses `runs[0].metrics` with test-specific keys). This complexity must be preserved in any aggregation layer.

**2. Comparison Policy Cannot Be Deferred (Blocks Phase 1)**

Section 7 explicitly "kicks the can" on comparison rules, but Phase 1 ("Trust and scope") requires a minimal allowlist to implement **any** investigation scoping:

- **Blocking questions:**
  - Which dimensions can users combine in filters? (Current UI allows arbitrary combinations)
  - What constitutes a "valid" baseline vs candidate pair?
  - How to prevent accidental cross-cloud comparisons in the UI before policy is written?

- **Recommendation:** Define **10-15 canonical comparison templates** immediately (e.g., "Same cloud, same instance type, RHEL X vs Y on test Z"). UI can then be template-driven rather than filter-combinatorial.

**3. Regression Detection Algorithm Unspecified**

The plan guarantees "navigate to raw data for regressions" but doesn't define what triggers a regression flag:

- Statistical threshold? (e.g., >5% delta, p-value < 0.05)
- Directionality per metric? (higher-is-better vs lower-is-better)
- Handling of variance? (current code has `baseline_std` in DataFrames but no documented policy)
- Non-PASS statuses? (Section 7.1 notes UNKNOWN/FAIL exist but not whether they block comparisons)

**Missing:** Explicit acceptance criteria like "A regression is surfaced when metric X degrades by Y% with Z confidence within the same hardware+test scope"

**4. Performance Budget Missing**

The plan acknowledges timeseries scale but provides no query cost guardrails:

- What is the P95 latency target for Pulse mode page load?
- What is the max document count for an Investigate query before pagination is required?
- Should OpenSearch aggregations be cached? (TTL policy for "last night's CPT run" vs "historical trend")

**5. Authentication/Multi-tenancy Not Addressed**

No discussion of:
- Who can see what data? (single-tenant assumed?)
- Partner-sensitive data access control (some clouds may require filtering beyond UI-level blocks)
- Audit logging for exec-level report generation

### 10.8 Framework Suitability Question

The plan states "No commitment: Framework, plugins, and language may change" but doesn't evaluate whether **Dash is suitable** for the proposed architecture:

**Dash strengths for this use case:**
- Plotly integration (already used)
- Python ecosystem (matches OpenSearch client)
- Callback model works for filter-driven investigations

**Dash weaknesses for multi-mode architecture:**
- No native concept of "modes" (would require custom routing/state management)
- Client-side callback limitations for aggregation-heavy workloads
- Less mature compared to Next.js/React for bookmark-driven deep linking

**Recommendation:** Prototype the "Pulse mode with server-side aggregations" pattern in Dash before committing. If callbacks become too complex, a thin Python API + modern frontend may be more maintainable.

### 10.9 Migration and Testing Gaps

**Migration:**
- Current `.env.example` documents single-index mode; how do existing users migrate to two-index setup?
- Synthetic data generator (`src/synthetic_data.py`) currently produces single-index structure—needs timeseries variant

**Testing:**
- How to **validate partner-safe rules**? (e.g., pytest fixture that asserts no cross-cloud queries in Pulse mode)
- How to test equivalence tables? (need golden dataset of "known-good" comparisons)
- Load testing plan for 242k timeseries documents?

### 10.10 Concrete Next Steps (Prioritized)

**Must-do before Phase 1 implementation:**

1. **Comparison Policy Workshop (Week 1):** Define 10-15 allowed comparison templates with explicit dimension constraints. Document in `docs/guides/COMPARISON_POLICY.md`.

2. **Backend Refactor (Weeks 1-2):**
   - Extend `BenchmarkDataSource` to support `query_results_index()` and `query_timeseries_index()`
   - Implement server-side aggregation helpers in `data_processing.py` (e.g., `aggregate_for_pulse_kpis()`)
   - Remove client-side `dcc.Store` pattern in favor of server callbacks

3. **Regression Detection Spec (Week 2):** Document algorithm, thresholds, and directionality in `docs/guides/REGRESSION_DETECTION.md`. Implement in `BenchmarkDataProcessor.detect_regressions()`.

4. **Deep Link Prototype (Week 2):** Implement `generate_opensearch_link(document_id, index_type)` utility and integrate into one visualization as proof-of-concept.

**Can defer to Phase 2:**
- Track/CPT mode (depends on Phase 1 aggregation patterns)
- Hardware equivalence tables beyond minimal Phase 1 allowlist
- Advanced caching/rollup indices (optimize after baseline performance measured)

### 10.11 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Comparison policy delayed → Phase 1 blocked** | High | Force decision in Week 1; MVP with 10 templates better than perfect taxonomy later |
| **Client-side processing retained → performance failure** | High | Refactor to server-side aggregations before adding modes |
| **Dash framework limitations → rewrite needed** | Medium | Prototype aggregation pattern early; evaluate escape hatches (embedded FastAPI, etc.) |
| **Missing regression algorithm → inconsistent bug filing** | Medium | Spec and implement before surfacing any "regression" labels in UI |
| **Partner policy violation in production** | High | Implement allowlist validation in backend with pytest coverage before launch |

### 10.12 Approval Conditions

Approve plan **contingent on**:
1. Comparison policy workshop scheduled and completed before implementation starts
2. Backend refactor (index routing + aggregations) prioritized as Phase 0 dependency
3. Regression detection algorithm documented with acceptance criteria
4. Partner-safe validation tests added to test suite

The strategic direction is sound, but the implementation dependencies are underspecified. Deferring comparison rules and aggregation patterns to "later" will create a critical path bottleneck.

