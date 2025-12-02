# Performance Engineering Dashboard

A Python Dash dashboard for visualizing software performance benchmark results from OpenSearch. Track performance regressions across OS versions and hardware configurations.

## Features

- **Multi-axis Filtering**: Filter by OS version, hardware, benchmark type, and date range
- **Performance Comparisons**: Side-by-side comparisons across configurations
- **Regression Detection**: Visual identification of performance improvements and regressions
- **Time Series Analysis**: Track performance trends over time
- **Dual Data Mode**: Works with live OpenSearch data and synthetic test data

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure OpenSearch Connection

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your OpenSearch credentials
nano .env  # or use your preferred editor
```

Required environment variables:
- `OPENSEARCH_HOST`: Your OpenSearch hostname
- `OPENSEARCH_PORT`: Port number (default: 9200)
- `OPENSEARCH_USERNAME`: Authentication username
- `OPENSEARCH_PASSWORD`: Authentication password
- `OPENSEARCH_INDEX`: Index name containing benchmark results
- `DATA_MODE`: Set to 'opensearch' or 'synthetic'

### 3. Run the Dashboard

```bash
python app.py
```

The dashboard will be available at http://127.0.0.1:8050

## Project Structure

```
performance-dashboard/
├── .env.example              # Environment template
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── OPENSEARCH_CONNECTION_GUIDE.md  # OpenSearch configuration
├── SCHEMA.md                # Discovered data schema
├── requirements.txt         # Python dependencies
├── app.py                   # Main Dash application
├── data/
│   └── synthetic/          # Synthetic test data
│       ├── README.md       # Data generation docs
│       └── *.json         # Generated datasets
├── src/
│   ├── opensearch_client.py    # OpenSearch connection
│   ├── data_processing.py      # Data transformation
│   ├── synthetic_data.py       # Synthetic data generator
│   └── components/
│       ├── filters.py          # Filter components
│       └── visualizations.py   # Visualization components
├── tests/
│   ├── test_data_processing.py
│   └── test_opensearch_client.py
└── assets/
    └── style.css              # Custom styling
```

## Data Sources

### OpenSearch Mode
Connect to live OpenSearch instance to query real benchmark results. See `OPENSEARCH_CONNECTION_GUIDE.md` for configuration details.

Set `DATA_MODE=opensearch` in your `.env` file.

### Synthetic Mode (Enhanced v2.0)
Use locally generated synthetic data for development and testing. The synthetic data generator creates a robust, realistic dataset that goes beyond simple test data:

**Dataset Highlights:**
- **800 benchmark results** across 100 unique scenarios
- **12 benchmark types**: coremark, coremark_pro, passmark, streams, auto_hpl, pyperf, phoronix, uperf, pig, specjbb, fio, sysbench
- **31 hardware configurations** across AWS, Azure, and GCP
- **5 RHEL versions**: 9.2, 9.3, 9.4, 9.5, 9.6
- **6 months of temporal data** with realistic trends
- **Realistic failures** (~8%) with multiple failure types
- **Correlated metrics** within test types for realism
- **Hardware-specific performance** characteristics

**Advanced Features:**
- ✅ Temporal trends (linear and seasonal patterns)
- ✅ Metric correlations for realistic co-variance
- ✅ Hardware tier performance scaling
- ✅ Five performance patterns (stable, minor improvement, improvement, minor regression, regression)
- ✅ Realistic failure scenarios (timeout, crash, validation, OOM)

Set `DATA_MODE=synthetic` in your `.env` file (default).

**Documentation:**
- `data/synthetic/README.md`: Complete generation approach and features
- `data/synthetic/USAGE_GUIDE.md`: Code examples and usage patterns

**Regenerate Data:**
```bash
source venv/bin/activate
python src/synthetic_data.py
```

## Development

### Running Tests

```bash
pytest tests/
```

### Hot Reload
The dashboard runs with `debug=True` by default, enabling hot reload during development.

## Documentation

- `OPENSEARCH_CONNECTION_GUIDE.md`: OpenSearch connection details and patterns
- `SCHEMA.md`: Documented schema from OpenSearch data discovery
- `data/synthetic/README.md`: Synthetic data generation approach

## Tech Stack

- **Framework**: Python Dash 2.14+ with Plotly
- **Data Source**: OpenSearch 3.x via opensearch-py
- **Data Processing**: Pandas + NumPy
- **Testing**: pytest
- **Grid Component**: dash-ag-grid

## Recent Fixes

### OS Version Regression Analysis (Dec 2025)
- **Fixed:** OS version regression analysis now correctly compares versions within the same OS distribution only
- **Previous Behavior:** The analysis was comparing versions alphabetically across all OS distributions (e.g., RHEL 9.6 → SLES 15.4)
- **Current Behavior:** Comparisons are now limited to versions within the same OS (e.g., RHEL 9.5 → RHEL 9.6)
- **Details:** See `OS_REGRESSION_FIX.md` for full technical details

## Contributing

When committing changes, include AI attribution if assisted:
```
Co-authored-by: Claude <claude@anthropic.com>
```

## License

Internal use only.

