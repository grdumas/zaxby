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
