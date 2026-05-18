# Documentation Index

This directory contains organized documentation for the Performance Engineering Dashboard project.

## 📖 Quick Start

**New to the project?** Start here:
- [Main README](../README.md) - Project overview and features
- [Quick Start Guide](../QUICKSTART.md) - Get running in 5 minutes
- [Project Brief](../PROJECT_BRIEF.md) - Original requirements and design decisions

## 📚 Documentation Categories

### Technical Guides (`guides/`)

Essential technical documentation for working with the dashboard:

- **[OPENSEARCH_CONNECTION_GUIDE.md](guides/OPENSEARCH_CONNECTION_GUIDE.md)**  
  How to connect to OpenSearch, authentication, query patterns, and index structure

- **[PHASE_1_AGENT_HANDOFF.md](guides/PHASE_1_AGENT_HANDOFF.md)**  
  Handoff for Phase 1 implementation: read order, Phase 0 inventory, P1-A–P1-F scope, conventions, paste-ready agent prompt

- **[SCHEMA.md](guides/SCHEMA.md)**  
  Complete data schema documentation including field types, benchmark types, and data patterns

- **[PULSE_KPIS.md](guides/PULSE_KPIS.md)**  
  Pulse (executive) KPI bundle: index overview, category mix, monthly activity, scope metadata — definitions and product review checklist (P2-A)

- **[UI_SUMMARY.md](guides/UI_SUMMARY.md)** ⭐ NEW  
  Executive summary of UI modernization proposal - start here! (Dec 2025)

- **[UI_MODERNIZATION_PROPOSAL.md](guides/UI_MODERNIZATION_PROPOSAL.md)** 🎨 NEW  
  Comprehensive proposal for modernizing the dashboard UI/UX with professional design patterns (Dec 2025)

- **[UI_QUICK_WINS.md](guides/UI_QUICK_WINS.md)** ⚡ NEW  
  Quick, high-impact CSS and component improvements that can be implemented in hours (Dec 2025)

- **[UI_IMPLEMENTATION_GUIDE.md](guides/UI_IMPLEMENTATION_GUIDE.md)** 🛠️ NEW  
  Step-by-step implementation guide with code examples and testing checklist (Dec 2025)

- **[DARK_MODE_GUIDE.md](guides/DARK_MODE_GUIDE.md)** 🌓 NEW  
  Dark mode implementation guide with toggle button and theme persistence (Dec 2025)

- **[CATEGORY_DRILLDOWN_GUIDE.md](guides/CATEGORY_DRILLDOWN_GUIDE.md)** 🔍 NEW  
  Interactive drill-down functionality for Competitive Performance section - click categories to explore benchmarks (Dec 2025)

- **[COMPARISON_POLICY.md](guides/COMPARISON_POLICY.md)** 📐 NEW  
  Canonical comparison templates and policy for baseline vs candidate comparisons (Apr 2026)

- **[REGRESSION_DETECTION.md](guides/REGRESSION_DETECTION.md)** 📊 NEW  
  Regression detection thresholds, directionality, and metric resolution specification (Apr 2026)

- **[UI_COLOR_REFERENCE.md](guides/UI_COLOR_REFERENCE.md)** 🎨 NEW  
  Complete color palette reference for dashboard UI including status colors, sections, and accessibility guidelines (Dec 2025)

### Bug Fixes & Issues (`fixes/`)

Documentation of bugs that have been identified and resolved:

- **[COLLAPSIBLE_SECTIONS_UPDATE.md](fixes/COLLAPSIBLE_SECTIONS_UPDATE.md)** ✨ NEW  
  Made all major dashboard sections (RHEL Regression, Competitive Performance, Cloud Scaling) collapsible for better navigation (Dec 2025)

- **[STATUS_BOX_MISLEADING_UX_FIX.md](fixes/STATUS_BOX_MISLEADING_UX_FIX.md)** ⭐  
  Fixed misleading green success boxes for "no data" conditions - now shows warning status (Dec 2025)

- **[DATE_FILTER_BUG_FIX.md](fixes/DATE_FILTER_BUG_FIX.md)**  
  Fixed date filter excluding end-of-day records, causing only 3-5 benchmarks to appear instead of all 12 (Dec 2025)

- **[OS_REGRESSION_FIX.md](fixes/OS_REGRESSION_FIX.md)**  
  Fixed OS version regression analysis to compare within same OS distribution only (Dec 2025)

- **[SYNTHETIC_DATA_HARDWARE_CONSISTENCY_FIX.md](fixes/SYNTHETIC_DATA_HARDWARE_CONSISTENCY_FIX.md)**  
  Fixed hardware configuration consistency in synthetic data generation

### Historical Documentation (`archive/`)

Older documentation kept for reference but superseded by current docs:

#### Implementation History
- **IMPLEMENTATION_SUMMARY.md** - Original implementation notes (see PROJECT_SUMMARY.md for current)
- **DASHBOARD_REDESIGN.md** - Dashboard redesign documentation
- **BEFORE_AFTER_COMPARISON.md** - Before/after comparison of changes

#### Feature Development
- **SYNTHETIC_DATA_ENHANCEMENTS.md** - Synthetic data v2.0 enhancements
- **SYNTHETIC_DATA_IMPROVEMENT.md** - Earlier synthetic data improvements
- **DETERMINISTIC_DATA_GENERATION_UPDATE.md** - Deterministic generation updates
- **FINAL_DATA_COVERAGE_VERIFICATION.md** - Data coverage verification
- **HARDWARE_FILTERING_UPDATE.md** - Hardware filtering feature updates
- **OS_EXPANSION_SUMMARY.md** - OS expansion work summary
- **VISUALIZATION_IMPROVEMENTS.md** - Visualization enhancements

#### Planning Documents
- **DASHBOARD_REDESIGN_AND_DATA_PLAN.md** - Dashboard redesign strategy and data plan (Apr 2026, implemented)
- **IMPLEMENTATION_PLAN.md** - Execution roadmap for dashboard redesign (Apr 2026, Phase 0 complete)

#### Deprecated Guides
- **QUICK_START_NEW_DASHBOARD.md** - Superseded by QUICKSTART.md
- **QUICK_START_SIMPLIFIED_REGRESSION.md** - Superseded by QUICKSTART.md
- **HARDWARE_AWARE_QUICK_REF.md** - Quick reference (archived)
- **RHEL_REGRESSION_SIMPLIFICATION.md** - Regression simplification notes

#### Historical Fixes
- **FIX_SUMMARY.md** - Missing benchmarks in RHEL regression (synthetic data, incorporated)
- **SCALE_FIX_SUMMARY.md** - Visualization scaling issues (incorporated)
- **BUGFIX_RHEL_REGRESSION_NO_DATA.md** - RHEL regression no-data issue (incorporated)

## 🗂️ Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── guides/                      # Technical guides
│   ├── OPENSEARCH_CONNECTION_GUIDE.md
│   ├── SCHEMA.md
│   ├── CATEGORY_DRILLDOWN_GUIDE.md
│   ├── COMPARISON_POLICY.md
│   ├── REGRESSION_DETECTION.md
│   ├── UI_MODERNIZATION_PROPOSAL.md
│   ├── UI_IMPLEMENTATION_GUIDE.md
│   ├── UI_COLOR_REFERENCE.md
│   └── DARK_MODE_GUIDE.md
├── fixes/                       # Bug fix documentation
│   ├── COLLAPSIBLE_SECTIONS_UPDATE.md
│   ├── STATUS_BOX_MISLEADING_UX_FIX.md
│   ├── DATE_FILTER_BUG_FIX.md
│   ├── OS_REGRESSION_FIX.md
│   └── SYNTHETIC_DATA_HARDWARE_CONSISTENCY_FIX.md
└── archive/                     # Historical/superseded documentation
    ├── IMPLEMENTATION_SUMMARY.md
    ├── DASHBOARD_REDESIGN.md
    ├── DASHBOARD_REDESIGN_AND_DATA_PLAN.md
    ├── IMPLEMENTATION_PLAN.md
    ├── BEFORE_AFTER_COMPARISON.md
    ├── SYNTHETIC_DATA_ENHANCEMENTS.md
    ├── SYNTHETIC_DATA_IMPROVEMENT.md
    ├── DETERMINISTIC_DATA_GENERATION_UPDATE.md
    ├── FINAL_DATA_COVERAGE_VERIFICATION.md
    ├── HARDWARE_FILTERING_UPDATE.md
    ├── OS_EXPANSION_SUMMARY.md
    ├── VISUALIZATION_IMPROVEMENTS.md
    ├── FIX_SUMMARY.md
    ├── SCALE_FIX_SUMMARY.md
    ├── BUGFIX_RHEL_REGRESSION_NO_DATA.md
    ├── QUICK_START_NEW_DASHBOARD.md
    ├── QUICK_START_SIMPLIFIED_REGRESSION.md
    ├── HARDWARE_AWARE_QUICK_REF.md
    └── RHEL_REGRESSION_SIMPLIFICATION.md
```

## 📁 Root Documentation

Core project documentation remains in the project root for easy access:

- **[README.md](../README.md)** - Main project README
- **[QUICKSTART.md](../QUICKSTART.md)** - Quick start guide
- **[PROJECT_BRIEF.md](../PROJECT_BRIEF.md)** - Original project requirements
- **[PROJECT_SUMMARY.md](../PROJECT_SUMMARY.md)** - Implementation summary and status

## 🔍 Finding What You Need

### I want to...

- **Get started quickly** → [QUICKSTART.md](../QUICKSTART.md)
- **Understand the project** → [README.md](../README.md) or [PROJECT_BRIEF.md](../PROJECT_BRIEF.md)
- **Connect to OpenSearch** → [guides/OPENSEARCH_CONNECTION_GUIDE.md](guides/OPENSEARCH_CONNECTION_GUIDE.md)
- **Understand the data schema** → [guides/SCHEMA.md](guides/SCHEMA.md)
- **Learn about a specific bug fix** → Check [fixes/](fixes/)
- **Review historical changes** → Check [archive/](archive/)
- **See implementation status** → [PROJECT_SUMMARY.md](../PROJECT_SUMMARY.md)

## 📝 Documentation Guidelines

> **For AI Assistants**: See [`../.cursorrules`](../.cursorrules) for complete project rules including automatic documentation organization guidelines.

When adding new documentation:

1. **Technical Guides** → `docs/guides/`
   - OpenSearch configuration
   - Data schemas
   - API documentation
   - Development setup

2. **Bug Fixes** → `docs/fixes/`
   - Include problem description
   - Root cause analysis
   - Solution implemented
   - Verification steps

3. **Historical/Deprecated** → `docs/archive/`
   - Superseded guides
   - Old implementation notes
   - Feature development history

4. **Active Project Docs** → Stay in root
   - README.md
   - QUICKSTART.md
   - PROJECT_BRIEF.md
   - PROJECT_SUMMARY.md

## 🔗 External Resources

- **Dash Documentation**: https://dash.plotly.com/
- **Plotly Documentation**: https://plotly.com/python/
- **OpenSearch Python Client**: https://opensearch.org/docs/latest/clients/python/
- **Pandas Documentation**: https://pandas.pydata.org/docs/

---

**Last Updated**: May 18, 2026  
**Project Status**: Active Development  
**Version**: v2.0

