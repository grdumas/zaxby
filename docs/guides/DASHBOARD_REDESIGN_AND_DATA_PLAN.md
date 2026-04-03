# RHEL Multi-Architecture Performance Dashboard — Redesign & Data Strategy Plan

**Status:** Draft — for human and AI review  
**Branch:** `plan/dashboard-redesign-and-data-strategy`  
**Last updated:** 2026-04-01  

This document captures **product context**, **live OpenSearch findings**, a **proposed direction** for the dashboard (without committing to stack or implementation), and a **non-final** catalog of **comparison rules** to refine later. It exists so reviewers (including other models) can suggest improvements, risks, and missing requirements.

**Review feedback (2026-04-01)** from two AI reviews has been **processed into the body** of this document (see §10 for synthesis). The full exploratory catalog in §7 remains for long-term trimming; **§6 and §7.4** now record the reviewers’ point that a **small allowlist / template set** is required before meaningful Phase 1 implementation—not a contradiction, but a **bridge** between “everything plausible” and “what we ship first.”

---

## 1. Purpose of this document

- Align stakeholders on **why** the product exists and **what constraints** are non-negotiable.
- Record **what data** is actually available in OpenSearch today (two indices, rough volumes, key dimensions).
- Propose a **high-level information architecture** (modes, deep linking, policy) independent of whether the app stays on Dash or moves to another stack.
- **§7** retains a **wide** catalog of plausible comparison types for future policy work; **§7.4** defines the **minimum** comparison policy artifact needed to unblock implementation (templates + allowlist), without pretending the full catalog is decided.

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

Benchmarks may be rolled up to **high-level categories** (e.g. networking, HPC, memory, Python, Java, storage). Users must **always** be able to drill from category → **individual benchmarks** (leaf metrics), not only a rolled-up score. Moving from today’s **OS-first** layouts to **category → leaf** implies a **structural navigation change** (breadcrumbs or nested IA), not only new charts.

---

## 3. Current implementation (high level, subject to change)

- Today the repo ships a **Python Dash** application with OpenSearch and synthetic modes.
- Documentation and env templates historically emphasized a **single** results index; production reality includes **two** indices (see below).
- **Architectural debt (review consensus):**
  - **`app.py`** loads filtered data into **`dcc.Store`** and drives many callbacks from browser-held payloads. That pattern **does not scale** to **`zathras-timeseries`** volume (~hundreds of thousands of documents) and is already heavy for large **`zathras-results`** pulls.
  - **`src/opensearch_client.py`** uses a single **`OPENSEARCH_INDEX`** (or equivalent) — **no index routing** for Pulse vs point-level drill-down.
  - **`BenchmarkDataProcessor._resolve_primary_metric()`** in **`src/data_processing.py`** already implements **fallback** when `results.primary_metric` is incomplete (e.g. pulling from nested `runs` / test-specific keys). Any **server-side aggregation** or KPI layer **must preserve** this semantics (or replace it with an explicit per-`test.name` metric registry).

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

### 4.4 Query-layer expectations (not yet implemented)

- **Index routing:** e.g. `route_index(query_kind) -> zathras-results | zathras-timeseries` for Pulse/KPI vs Investigate/point queries.
- **Equivalence tables** (instance generation / size / cross-vendor “tier” matching) are a **significant** modeling effort; Phase 1 should start from a **minimal** documented allowlist, not full automation.

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

### 5.4 Framework note (Dash vs alternatives)

- **Dash / Plotly** fit the current team stack and investigation-style charts; **modes** (Pulse vs Investigate) require **custom routing/state** (already partially present via navigation stores).
- **Risks:** heavy **server-side aggregation** and bookmarkable deep links are less turnkey than in many SPA frameworks; **prototype Pulse with server-side aggregations** in Dash before committing to a full rewrite.
- **Escape hatch:** a thin **FastAPI** (or similar) layer serving aggregated JSON + a future alternate frontend remains compatible with the same OpenSearch contracts.

---

## 6. Phasing (suggested, updated after review)

**Phase 0 — Platform prerequisites (reviewers: blocks safe Phase 1 if skipped)**

1. **Index-aware data access:** extend the OpenSearch integration so callers can target **`zathras-results`** vs **`zathras-timeseries`** by query type (Pulse/KPI vs narrow Investigate / point).
2. **Server-side aggregation path:** introduce endpoints or server callbacks that **do not** depend on shipping full result sets to `dcc.Store` for Pulse-style views; cap Investigate payloads with **pagination** or strict filters.
3. **Environment / docs:** document both index names (e.g. in `.env.example`) and migration notes for operators moving from single-index configs.
4. **Deep link utility:** `generate_opensearch_link(document_id | timeseries_id, index)` — prove on **one** visualization before broad rollout.
5. **Minimal comparison policy artifact:** **10–15 canonical comparison templates** (dimensions fixed per template) documented as the first **`COMPARISON_POLICY`** companion (see §10.3); full §7 catalog remains for later trimming.

**Phase 1 — Trust and scope**

- Investigation scoping aligned to templates, category → leaf drill-down, OpenSearch deep links for any **regression**-class signal, **partner-safe** guardrails in **backend** (not only copy).

**Phase 2 — Pulse**

- KPI surfaces on top of aggregation contracts; exec-safe summaries.

**Phase 3 — Track / CPT**

- Exception feeds; caching, optional rollup indices; load testing against timeseries scale.

---

## 7. Comparison rules — catalog only (not finalized)

**Wide catalog:** this section lists **plausible** comparison dimensions and patterns observed from **`zathras-results`** data. The team will **trim** to an allowlist/blocklist over time.

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
- Same `test.name`, different `metadata.scenario_name`: valid for pyperf-style per-scenario micro-workloads; needs aggregation rules if rolled up.
- Different `test.name`: only via **category rollups** with defined aggregation — not raw point-to-point.

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

- Canonical **metric field** per `test.name` (primary vs nested) — may converge to a **registry** used by aggregations.
- **Equivalence tables** for instance types across generations or sizes.
- Whether **cross-arch** comparisons are ever **auto-suggested** or only **manual** with warnings.
- Final **partner** wording and what is allowed in **Pulse** vs **Investigate**.

### 7.4 Minimum policy for implementation (review input)

Implementing **Investigate** with arbitrary combinatorial filters **without** policy risks accidental forbidden comparisons. **Before** UI work that encodes comparisons:

- Define **10–15 canonical templates** (e.g. “same cloud + same `instance_type` + same `test.name` + same `scenario_name`: RHEL X vs Y”).
- Encode **baseline vs candidate** explicitly per template.
- Validate **Pulse** queries in **tests** (e.g. no cross–public-cloud aggregations in Pulse mode unless explicitly out-of-scope for v1).

The full catalog in §7.2 remains the long-term menu; **templates** are the **narrow** first slice.

---

## 8. Success criteria (draft, expanded)

- An exec can grasp **directional** health vs an agreed baseline using **KPIs** without wading through global filters.
- An engineer can answer a **scoped** question with only relevant runs and open **OpenSearch** to the **correct** document (run or timeseries point) from any surfaced regression.
- Category rollups always expose a path to **leaf benchmarks**.
- The product does **not** default to **forbidden** comparison types (e.g. cross–public-cloud where policy says no).
- **Regression signal (when labeled):** documented definition — threshold, **directionality** per test/unit, handling of **UNKNOWN/FAIL**, variance — see **non-functional / spec** gaps in §9.
- **Partner safety:** automated checks or tests that **Pulse** cannot emit blocked comparison classes (exact mechanism TBD).

---

## 9. Non-functional and operational gaps (review input)

These were underspecified in the first draft; **targets remain TBD** unless product sets numbers.

| Area | Open questions |
|------|----------------|
| **Performance** | P95 budget for Pulse load; max rows per Investigate query before pagination; cache TTL for repeated aggregations (e.g. “last CPT window”). |
| **Regression math** | What constitutes “regression” (delta %, statistical test, min sample size); alignment with existing `baseline_std` / DataFrame fields if used. |
| **Auth / tenancy** | Single-tenant assumption? Row-level restrictions beyond UI (e.g. partner data)? Audit logging for exec exports? |
| **Testing** | Golden “known-good” comparison fixtures; load test plan for timeseries index; **pytest** (or similar) for policy violations on query builders. |
| **Synthetic data** | Extend or mirror **`zathras-timeseries`** shape if Investigate point drill-down is tested offline. |

---

## 10. Processed review synthesis (2026-04-01)

Two independent AI reviews (Gemini 2.5 Pro via Gemini CLI; Claude Sonnet 4.5 via Claude Code) were merged into this document. Below: **consensus**, **actions taken in this revision**, and **remaining owner actions**.

### 10.1 Consensus (both reviewers)

- **Two-index model** is sound; **bulk client-side** processing of timeseries is **not** viable.
- **Index routing** and **server-side aggregation** are prerequisites for Pulse and safe scale-up.
- **Partner / cross-cloud** risk requires **enforcement in logic**, not only documentation.
- **Equivalence / hardware matching** is hard; start **small** and explicit.
- **Category → leaf** navigation implies **real IA work** (breadcrumbs / nested patterns), not a cosmetic tweak.
- **Dash** can remain viable if **Pulse aggregations** are prototyped early; **rewrite** is optional contingency.

### 10.2 Incorporated into this document (this edit)

- §3: **implementation debt** (`dcc.Store`, single index env, `_resolve_primary_metric`).
- §4.4: **query-layer** and equivalence expectations.
- §5.4: **framework** tradeoffs and prototype recommendation.
- §6: **Phase 0** with concrete prerequisites (index routing, server-side path, env/docs, deep links, **minimal templates**).
- §7.4: **bridge** between wide catalog and **minimum** policy for build.
- §8–§9: **regression definition** placeholder, **NFR** table, **testing/synthetic** gaps.

### 10.3 Planned companion documents (not created in this pass)

| Document | Purpose |
|----------|---------|
| `docs/guides/COMPARISON_POLICY.md` | Canonical **templates** + allowlist/blocklist; owner: product + perf lead. |
| `docs/guides/REGRESSION_DETECTION.md` | Thresholds, directionality, status handling, acceptance criteria for “regression” labels. |

Create these when Phase 0 kicks off; keep this plan as the **umbrella**.

### 10.4 Approval stance (reviewers)

- **Strategic direction:** approved with recommendations.
- **Implementation:** approved **contingent** on Phase 0 (policy artifact + backend/query refactor + regression spec before shipping **regression** labels broadly). Exact “approval conditions” wording from the Claude review is **reflected** in §6 Phase 0 and §10.3 rather than duplicated verbatim.

### 10.5 Review provenance

| Reviewer | Tooling note | Original stance |
|----------|----------------|-----------------|
| Gemini 2.5 Pro | Gemini CLI | Approved with recommendations — index routing, equivalence workshop, drill-down UI |
| Claude Sonnet 4.5 | Claude Code | Approved with significant implementation concerns — Phase 0 dependencies, regression spec, partner tests, performance/auth gaps |

---

## 11. Feedback requested from reviewers

- Missing **stakeholder** or **compliance** constraints.
- **Risks** in the two-index model (query cost, consistency, drift).
- **MVP** scope that preserves traceability and partner-safe Pulse with minimal engineering.
- Suggested **acceptance tests** or **metrics** for launch.

---

## Document history

| Date | Change |
|------|--------|
| 2026-04-01 | Initial draft on branch `plan/dashboard-redesign-and-data-strategy` |
| 2026-04-01 | Processed AI review feedback: Phase 0, §7.4 templates, implementation debt, NFR table, companion doc plan, §10 synthesis |
