# Quick Start Guide

Get the Performance Engineering Dashboard running in 5 minutes!

## Prerequisites

- Python 3.9+ (including Python 3.14+)
- Access to OpenSearch instance (or use synthetic data mode)

## Installation Steps

### 1. Clone and Navigate

```bash
cd /path/to/zaxby
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Connection

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimal `.env` configuration:**

```env
# For OpenSearch mode
OPENSEARCH_HOST=your-opensearch-host
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=your-username
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_INDEX=zathras-results
# Recommended: set both so your environment matches production Zathras clusters
OPENSEARCH_INDEX_RESULTS=zathras-results
OPENSEARCH_INDEX_TIMESERIES=zathras-timeseries
OPENSEARCH_USE_SSL=true
DATA_MODE=opensearch

# OR for synthetic data mode (no OpenSearch needed)
DATA_MODE=synthetic
```

**Dual-index note:** `zathras-results` holds one document per test run (thousands of docs). `zathras-timeseries` holds point-level rows (much larger). The app loads run documents for the main dashboard; timeseries is for bounded, on-demand queries only. See `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md`.

### 4. Run the Dashboard

```bash
python app.py
```

The dashboard will be available at: **http://127.0.0.1:8050**

## Using the Dashboard

The UI is organized around **three analyses** (RHEL regression vs peers, cloud scaling, etc.), with **advanced filters** and an **investigation drill-down** when you open a specific comparison. A **server snapshot** panel (when using OpenSearch) shows index-level counts without loading full datasets into the browser.

This replaces older quick-start text that listed Overview / Comparisons / Time Series / Heatmap / Table **tabs**; those screens are not the current layout. Some sections still use **nested tabs** (for example benchmark breakdown views) inside an analysis.

### Main Features

1. **Filters** — OS version, instance type, benchmark, cloud, date range, status (use **Show advanced filters** if collapsed).
2. **Sections** — Expand RHEL regression, competitive performance, or cloud scaling; open an investigation to see detail charts and tables.
3. **OpenSearch Discover** — If `OPENSEARCH_DASHBOARDS_BASE_URL` is set, the investigation view can link to the matching run in Dashboards.

### Tips

- **Reset Filters**: Click "Reset Filters" button to restore defaults
- **Multi-Select**: Hold Ctrl/Cmd to select multiple items in dropdowns
- **Hover Data**: Hover over charts for detailed information
- **Date Range**: Use date picker for time-based filtering

## Data Modes

### Synthetic Mode (Default)

Perfect for testing and development without OpenSearch access.

```bash
# In .env
DATA_MODE=synthetic
```

- Uses 150 pre-generated test results
- Covers RHEL 9.3-9.6
- Multiple cloud providers and instance types
- Includes performance regressions and improvements

### OpenSearch Mode

Connect to live OpenSearch instance for real data.

```bash
# In .env
DATA_MODE=opensearch
OPENSEARCH_HOST=your-host
OPENSEARCH_INDEX=zathras-results
OPENSEARCH_INDEX_RESULTS=zathras-results
OPENSEARCH_INDEX_TIMESERIES=zathras-timeseries
# Optional: OPENSEARCH_DASHBOARDS_BASE_URL=https://your-dashboards-host:5601
# ... credentials, SSL, etc.
```

Migrating from a **single-index** setup: keep `OPENSEARCH_INDEX` pointed at your run/results index, then add `OPENSEARCH_INDEX_RESULTS` and `OPENSEARCH_INDEX_TIMESERIES` as above. See **Migration from single-index setups** in `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md`.

**OpenSearch load failure:** With `DATA_MODE=opensearch`, a failed connection or scroll does **not** automatically switch to synthetic data (you would otherwise risk confusing offline samples with live cluster data). The UI shows the error and recovery options. To load synthetic data only after that failure, set `ZAXBY_USE_SYNTHETIC_AFTER_OPENSEARCH_FAILURE=1` in `.env` and restart; the header indicates synthetic data loaded under this opt-in. Alternatively set `DATA_MODE=synthetic` for offline work.

## Troubleshooting

### Dashboard Won't Start

**Issue**: `AttributeError: module 'pkgutil' has no attribute 'find_loader'`
```bash
# Solution: Upgrade Dash to a version compatible with Python 3.14+
pip install --upgrade dash dash-ag-grid dash-bootstrap-components
```

**Issue**: `ModuleNotFoundError`
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Issue**: OpenSearch connection failed
```bash
# Solution 1: Check credentials in .env
# Solution 2: Switch to synthetic mode temporarily
DATA_MODE=synthetic python app.py
```

### No Data Showing

**Issue**: Callback error: "Invalid comparison between dtype=datetime64[ns, UTC] and datetime"
```bash
# Solution: This has been fixed in app.py
# The date filter now correctly uses timezone-aware datetime objects
# If you see this error, ensure you have the latest version of app.py
```

**Issue**: Filters too restrictive
```bash
# Solution: Click "Reset Filters" in the dashboard
```

**Issue**: Empty OpenSearch index
```bash
# Solution: Verify index name and contents
python explore_opensearch.py
```

### Port Already in Use

**Issue**: Port 8050 is busy
```bash
# Solution: Use different port
PORT=8051 python app.py
```

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Explore OpenSearch Schema

```bash
python explore_opensearch.py
```

### Generate New Synthetic Data

```bash
python src/synthetic_data.py
```

### Hot Reload

The dashboard runs in debug mode by default, enabling hot reload:
- Edit any Python file
- Save changes
- Dashboard automatically reloads

## Next Steps

1. **Customize Filters**: Edit `src/components/filters.py`
2. **Add Visualizations**: Extend `src/components/visualizations.py`
3. **Query Optimization**: Modify `src/opensearch_client.py`
4. **Styling**: Update `assets/style.css`

## Support

For issues or questions:
1. Check `docs/guides/SCHEMA.md` for data structure details
2. Review `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md` for connection help
3. Examine test files in `tests/` for usage examples
4. See `docs/README.md` for complete documentation index

---

**Happy Performance Engineering! 🚀**

