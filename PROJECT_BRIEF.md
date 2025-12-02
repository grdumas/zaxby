# Performance Engineering Dashboard Project

You are helping build a Python Dash dashboard for visualizing software performance benchmark results. This is a greenfield project - start from scratch following the specifications below.

## Quick Start Context
- **Purpose**: Track performance regressions across OS versions and hardware configurations
- **Data Source**: OpenSearch v3 (internally hosted) with results from Zathras test orchestration
- **Key Question**: "Did performance regress, improve, or stay the same between X and Y?"
- **Tech Stack**: Python Dash + Plotly + opensearch-py
- **Environment**: Local development, venv for isolation

## Critical Requirements

### 1. Environment & Workflow
- Use Python venv for all package installations
- Enable hot reload (debug=True) during development
- Include AI attribution in commits: `Co-authored-by: Claude <claude@anthropic.com>`
- Store OpenSearch credentials (username/password) in `.env` using python-dotenv
- Never commit `.env` - provide `.env.example` template instead

### 2. OpenSearch Connection
**IMPORTANT**: Refer to `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md` for:
- Connection configuration details
- Authentication setup
- Query examples and patterns
- Index structure information
- Any environment-specific requirements

Use this guide as the authoritative source for OpenSearch integration details.

### 3. Data Strategy (Discovery-First Approach)

**Phase 1 - OpenSearch Integration & Schema Discovery**:
- Connect to OpenSearch following `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md`
- Query the index to retrieve existing test results
- Analyze and document the actual schema in `docs/guides/SCHEMA.md`:
  - Document structure and field types
  - Benchmark types present in the data
  - OS versions and hardware configurations found
  - Metadata fields (timestamps, job IDs, system info)
  - Score/metric formats and ranges
- Identify what benchmark types are actually being tested
- Note any patterns, conventions, or quirks in the data

**Phase 2 - Synthetic Data Generation**:
- Based on discovered schema and benchmark types from Phase 1
- Generate expanded synthetic dataset that mirrors real data structure
- Use actual benchmark types found in OpenSearch (don't assume SPEC CPU, stress-ng, etc.)
- Extend coverage beyond what's currently in OpenSearch:
  - Additional OS versions in same families found
  - More hardware configurations in similar patterns
  - More test runs over time
  - Performance patterns: regressions (20-40% drops), improvements (15-30% gains), stable (±5%)
- Save to `data/synthetic/` as JSON files
- Document generation approach in `data/synthetic/README.md`

**Phase 3 - Dashboard Development**:
- Build data processing layer to handle real OpenSearch schema
- Develop visualizations based on actual metric types
- Implement filtering for dimensions present in real data
- Test with both real and synthetic data

**Phase 4 - Refinement**:
- Add configuration flag to switch between OpenSearch and synthetic data modes
- Optimize queries based on actual data patterns
- Polish visualizations based on real data characteristics

### 4. Dashboard Features

**Multi-Axis Filtering** (Critical):
- OS version (multi-select for comparisons)
- Hardware/system type
- Benchmark type
- Date range picker
- "Comparison mode" toggle

**Note**: Filter options should be derived from what actually exists in OpenSearch data, not predetermined lists.

**Visualizations** (Plotly):
1. Side-by-side performance comparison charts
2. Time series trends
3. Regression heatmap (OS × hardware grid)
4. Detailed metrics table (consider dash-ag-grid)

**Visualization design should adapt to**:
- Actual metric types found in data (throughput, latency, scores, etc.)
- Number and type of benchmarks present
- Granularity of system metadata available

**Performance Optimizations**:
- Use `dcc.Store` to cache OpenSearch results client-side
- Fetch broad datasets, filter via callbacks
- Use `prevent_initial_call=True` where appropriate
- Minimize server round-trips

### 5. Testing
- pytest for data processing logic
- Test edge cases: missing data, outliers, empty results
- Mock OpenSearch responses in unit tests based on real schema

## Project Structure
```
performance-dashboard/
├── .env.example
├── .gitignore                   # Must include: .env, venv/, __pycache__
├── README.md
├── docs/
│   ├── guides/
│   │   ├── OPENSEARCH_CONNECTION_GUIDE.md  # Your OpenSearch configuration reference
│   │   └── SCHEMA.md                    # Document discovered schema here
├── requirements.txt
├── app.py                       # Main Dash app
├── data/
│   └── synthetic/
│       ├── README.md            # Document generation approach
│       └── *.json
├── src/
│   ├── opensearch_client.py     # Connection & queries
│   ├── data_processing.py       # Transform for visualization
│   ├── synthetic_data.py        # Data generator
│   └── components/
│       ├── filters.py
│       └── visualizations.py
├── tests/
│   ├── test_data_processing.py
│   └── test_opensearch_client.py
└── assets/
    └── style.css
```

## Implementation Order (Discovery-First)

1. **Setup**: venv, requirements.txt, .env.example, .gitignore, basic project structure

2. **OpenSearch Integration** (START HERE):
   - Review `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md`
   - Implement `opensearch_client.py` with connection and basic queries
   - Connect to live OpenSearch and retrieve sample documents
   - Analyze the data structure thoroughly
   - Document findings in `docs/guides/SCHEMA.md` with examples
   - Create utility functions to query and explore the index

3. **Synthetic Data Generation**:
   - Implement `synthetic_data.py` based on discovered schema
   - Mirror the exact structure and field names from OpenSearch
   - Use actual benchmark types and metric formats found
   - Generate expanded dataset with more scenarios
   - Include realistic score ranges based on observed data
   - Document any assumptions or extrapolations made

4. **Data Processing Layer**:
   - Implement `data_processing.py` to handle real schema
   - Transform/aggregation logic for discovered metric types
   - Comparison calculations (deltas, percentage changes)
   - Unit tests using real schema patterns

5. **Dashboard Core**:
   - Create `app.py` with basic layout
   - Implement single visualization with real OpenSearch data
   - Test callback pattern and hot reload
   - Add mode switching (live vs synthetic)

6. **Filtering System**:
   - Build multi-axis filter components based on actual data dimensions
   - Populate filter options dynamically from OpenSearch
   - Wire up callbacks with dcc.Store caching
   - Test with both data sources

7. **Visualizations**:
   - Implement comparison charts for actual benchmark types
   - Add trend lines appropriate to metric types
   - Build regression heatmap
   - Iterate on interactivity

8. **Polish & Testing**:
   - Complete test coverage
   - Documentation updates
   - Performance optimization
   - Code cleanup

## Technical Notes

**Dash Framework Rationale**:
- Chosen for team standardization across multiple dashboard projects
- Alternative considered: React + TypeScript + Plotly.js
  - Would offer: instant client-side filtering, richer components, better multi-axis performance
  - If Dash proves inadequate for complex requirements, React remains viable alternative

**OpenSearch Client**:
- Use opensearch-py library
- Follow connection details in `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md`
- Implement flexible query builder for filtering
- Handle connection errors gracefully
- Example connection pattern in `opensearch_client.py`:
```python
from opensearchpy import OpenSearch
from dotenv import load_dotenv
import os

load_dotenv()

# Refer to docs/guides/OPENSEARCH_CONNECTION_GUIDE.md for specific configuration
client = OpenSearch(
    hosts=[os.getenv('OPENSEARCH_HOST')],
    http_auth=(os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASS')),
    use_ssl=True,
    verify_certs=True
)
```

**Schema Discovery Approach**:
- Query multiple documents to understand variations
- Look for common fields vs optional fields
- Identify any nested structures or arrays
- Note data types and formats (timestamps, numbers, strings)
- Check for any naming conventions or patterns
- Document edge cases or inconsistencies

**Comparison Logic**:
- Support comparisons across multiple dimensions simultaneously:
  - OS version A vs B on same hardware
  - Same OS on hardware X vs Y
  - Different OS distributions at similar versions
- Calculate percentage deltas for regression detection
- Highlight significant changes (>10-15% threshold)

## User Context
- User is new to OpenSearch - document queries clearly
- Part of larger Continuous Performance Testing initiative with Zathras orchestration
- Focus: regression detection is paramount for performance engineers
- Will integrate with multi-product dashboard (other teams also use Dash)
- Current OpenSearch index has limited data, but represents actual test structure

## Success Criteria
✓ Successfully connects to OpenSearch and retrieves real data
✓ Schema is thoroughly documented with examples
✓ Synthetic data accurately mirrors real OpenSearch structure
✓ Dashboard works with both real and synthetic data seamlessly
✓ Multi-axis filtering works smoothly without lag
✓ Clear identification of regressions/improvements between configs
✓ Well-tested with pytest
✓ Follows Python/Dash best practices

---

**Next Steps**: 
1. Set up project environment (venv, dependencies)
2. Review `docs/guides/OPENSEARCH_CONNECTION_GUIDE.md` for connection details
3. **Immediately connect to OpenSearch and explore the data**
4. Document actual schema before making any assumptions
5. Ask clarifying questions based on what you discover in the real data