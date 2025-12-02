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

- **[SCHEMA.md](guides/SCHEMA.md)**  
  Complete data schema documentation including field types, benchmark types, and data patterns

### Bug Fixes & Issues (`fixes/`)

Documentation of bugs that have been identified and resolved:

- **[OS_REGRESSION_FIX.md](fixes/OS_REGRESSION_FIX.md)**  
  Fixed OS version regression analysis to compare within same OS distribution only (Dec 2025)

- **[FIX_SUMMARY.md](fixes/FIX_SUMMARY.md)**  
  Fixed missing benchmarks in RHEL regression comparison (synthetic data generation issue)

- **[SCALE_FIX_SUMMARY.md](fixes/SCALE_FIX_SUMMARY.md)**  
  Fixed scaling visualization issues

- **[BUGFIX_RHEL_REGRESSION_NO_DATA.md](fixes/BUGFIX_RHEL_REGRESSION_NO_DATA.md)**  
  Resolved issue with missing data in RHEL regression analysis

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

#### Deprecated Guides
- **QUICK_START_NEW_DASHBOARD.md** - Superseded by QUICKSTART.md
- **QUICK_START_SIMPLIFIED_REGRESSION.md** - Superseded by QUICKSTART.md
- **HARDWARE_AWARE_QUICK_REF.md** - Quick reference (archived)
- **RHEL_REGRESSION_SIMPLIFICATION.md** - Regression simplification notes

## 🗂️ Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── guides/                      # Technical guides
│   ├── OPENSEARCH_CONNECTION_GUIDE.md
│   └── SCHEMA.md
├── fixes/                       # Bug fix documentation
│   ├── OS_REGRESSION_FIX.md
│   ├── FIX_SUMMARY.md
│   ├── SCALE_FIX_SUMMARY.md
│   ├── BUGFIX_RHEL_REGRESSION_NO_DATA.md
│   └── SYNTHETIC_DATA_HARDWARE_CONSISTENCY_FIX.md
└── archive/                     # Historical/superseded documentation
    ├── IMPLEMENTATION_SUMMARY.md
    ├── DASHBOARD_REDESIGN.md
    ├── BEFORE_AFTER_COMPARISON.md
    ├── SYNTHETIC_DATA_ENHANCEMENTS.md
    ├── SYNTHETIC_DATA_IMPROVEMENT.md
    ├── DETERMINISTIC_DATA_GENERATION_UPDATE.md
    ├── FINAL_DATA_COVERAGE_VERIFICATION.md
    ├── HARDWARE_FILTERING_UPDATE.md
    ├── OS_EXPANSION_SUMMARY.md
    ├── VISUALIZATION_IMPROVEMENTS.md
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

**Last Updated**: December 2, 2025  
**Project Status**: Active Development  
**Version**: v2.0

