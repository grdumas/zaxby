# Comparison policy — draft

**Status:** Draft (Phase 0, P0-E)  
**Companion:** [REGRESSION_DETECTION.md](REGRESSION_DETECTION.md), [DASHBOARD_REDESIGN_AND_DATA_PLAN.md](DASHBOARD_REDESIGN_AND_DATA_PLAN.md) §7.4, [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §2.5  

This document defines a **closed set of comparison templates** for investigations and guardrails for **Pulse** (executive) mode. Product and performance engineering still own final sign-off; implementers should treat template IDs and rules below as the contract to implement `validate_comparison_request(template_id, params)` and tests.

---

## 1. Vocabulary

| Term | Meaning |
|------|---------|
| **Baseline** | The reference configuration or time window against which change is measured. |
| **Candidate** | The configuration or window being evaluated (sometimes called “comparison” in code). |
| **Fixed dimensions** | Fields that must match (or be held constant) for a template; documented per template. |
| **Template** | A named pattern: allowed axes of variation, required parameters, and Pulse eligibility. |

Naming in UI and APIs should use **baseline** / **candidate** so explanations are portable outside the codebase (the processor may still use internal names like `comparison_mean`).

---

## 2. Modes: Pulse vs Investigate

| Mode | Intent | Policy |
|------|--------|--------|
| **Pulse** | Directional health, small KPI set, exec-safe narratives | Only templates marked **Pulse-allowed** may be used. Aggregations must not construct **forbidden** comparisons (see §4). |
| **Investigate** | Scoped engineering questions, drill-down, tables | May use any template in §5 when parameters are valid. Forbidden comparisons remain **blocked** unless a future policy adds an explicit override path (not in scope for this draft). |

---

## 3. Pulse — forbidden axes (non-negotiable for default surfaces)

These restrictions apply to **Pulse** queries, KPIs, and any server-side aggregation that **compares** cohorts (not raw OpenSearch row retrieval for a single document).

1. **No cross–public-cloud comparative deltas**  
   Do not aggregate or present **baseline vs candidate** where `metadata.cloud_provider` (or equivalent) differs between the two cohorts (e.g. AWS vs Azure, AWS vs GCP).  
   **Allowed in Pulse:** single-provider views, or global counts that **do not** imply A-vs-B performance between providers.

2. **No implicit cross-provider “equivalence”**  
   Pulse must not map instance SKUs across providers or show ranked provider lists for the same metric unless a future **explicit** equivalence table and template exist (out of scope here).

3. **No multi-distribution OS regression without template**  
   Comparing **RHEL vs SLES** (or other peers) is **Investigate-only** via the peer template (TPL_PEER_OS), not a default Pulse tile.

4. **Scenario name discipline**  
   When `metadata.scenario_name` is part of the grain, Pulse must not blend unrelated scenario families (e.g. `rhel_95*` vs `az_*`) into one comparative KPI without an explicit template that defines the join rule.

**Investigate** may still request **within-one-provider** comparisons and **peer OS** comparisons using the templates in §5, subject to validation.

---

## 4. Validation contract (exit criterion)

Implementations should expose:

```text
validate_comparison_request(template_id: str, params: dict) -> ValidationResult
```

- **Accept** only `template_id` values from §5.  
- **Reject** unknown IDs, missing required parameters, or parameter values that violate fixed dimensions (e.g. two different `cloud_provider` values when the template requires equality).  
- **Enforce Pulse:** if caller mode is Pulse, reject any template not marked Pulse-allowed, and reject any params that imply forbidden axes in §3.

---

## 5. Canonical templates (10–15)

Each row is one **template_id**. Parameters are the minimal fields callers supply; **fixed** means equality required across baseline and candidate cohorts unless listed under **Varies**.

| ID | Description | Fixed dimensions (match across cohorts) | Varies (baseline vs candidate) | Pulse-allowed |
|----|-------------|------------------------------------------|--------------------------------|---------------|
| `TPL_RHEL_MINOR_SAME_HW` | RHEL minor release A vs B on same hardware and workload | `os_distribution`, `cloud_provider`, `instance_type`, `test.name`, `scenario_name` (if present), `cpu.architecture` | `operating_system.version` | Yes |
| `TPL_RHEL_MAJOR_SAME_HW` | RHEL 9.x vs 10.x (or other major) with same constraints as minor | Same as `TPL_RHEL_MINOR_SAME_HW` | Major/minor per product rules | Yes (single provider) |
| `TPL_OS_SEQUENTIAL_MINOR` | Generic: adjacent minors within **one** OS distribution | `os_distribution`, `cloud_provider`, `instance_type`, `test.name` | Sequential `os_version` pair | Yes |
| `TPL_PEER_OS` | Baseline OS (e.g. RHEL) vs peer (e.g. SLES) on comparable scope | `cloud_provider`, `instance_type`, `test.name`, `scenario_name` | `os_distribution` / version per role | No |
| `TPL_CLOUD_SCALE_SAME_OS` | Instance size sweep **within one provider** | `os_distribution`, `os_version`, `test.name`, `scenario_name` | `instance_type` (ordered sizes) | Yes |
| `TPL_TIME_WINDOW` | Same scope, two time windows (CPT / drift) | `cloud_provider`, `instance_type`, `test.name`, `os_distribution`, `os_version` | `test_timestamp` window | Yes |
| `TPL_ITERATION_REPEATABILITY` | Same config, different `metadata.iteration` | All identity fields including iteration cohort | `iteration` | No (noise / variance, not regression) |
| `TPL_ARCH_EXPLICIT` | x86_64 vs aarch64 **explicit** comparison | `cloud_provider`, `test.name`, `scenario_name`, matched policy for instance mapping | `cpu.architecture`, paired instance types per policy | No |
| `TPL_SCENARIO_ABLATION` | Same OS/hardware, different `scenario_name` only | `cloud_provider`, `instance_type`, `os_distribution`, `os_version`, `test.name` | `scenario_name` | No |
| `TPL_CATEGORY_ROLLUP` | Category-level roll-up with drill-down to leaf | Category definition, time bounds | N/A (aggregation semantics) | Yes if single-provider and no cross-cloud delta |
| `TPL_SINGLE_RUN_LOOKUP` | No comparative delta; fetch one run / document | `metadata.document_id` | N/A | Yes |
| `TPL_PROVIDER_INTERNAL_REGION` | Same provider, different region (if data supports) | `cloud_provider`, `test.name`, `instance_type`, OS | `region` (if field exists) | Yes |
| `TPL_GEN_UPLIFT` | CPU generation change, same nominal tier | Provider-specific equivalence table | Generation | No until equivalence exists |

**Notes**

- **TPL_PEER_OS** and **TPL_ARCH_EXPLICIT** are **Investigate-only** to avoid partner and misinterpretation risk on exec surfaces.
- **TPL_CATEGORY_ROLLUP** Pulse-allowed only when the implementation proves the aggregation cannot produce cross-provider comparative metrics (e.g. single provider filter enforced server-side).
- **TPL_ITERATION_REPEATABILITY** is for variance, not “regression” labeling; see [REGRESSION_DETECTION.md](REGRESSION_DETECTION.md).

---

## 6. Mapping to OpenSearch fields (reference)

Typical bindings (see [SCHEMA.md](SCHEMA.md) for full schema):

- `test.name` → `test.name`
- OS → `system_under_test.operating_system.distribution`, `system_under_test.operating_system.version`
- Cloud / hardware → `metadata.cloud_provider`, `metadata.instance_type`, `system_under_test.hardware.cpu.architecture`
- Workload grain → `metadata.scenario_name`, `metadata.iteration`
- Time → `metadata.test_timestamp`

---

## 7. Revision log

| Date | Change |
|------|--------|
| 2026-04-06 | Initial draft for P0-E exit: templates + Pulse forbidden axes + validation contract |
