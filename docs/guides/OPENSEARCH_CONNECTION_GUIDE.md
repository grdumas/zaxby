# OpenSearch Connection Guide for Dash Dashboard

This document provides essential information for connecting to OpenSearch from the Python Dash dashboard project. This information is based on the proof-of-concept OpenSearch downloader implementation.

## Overview

The dashboard visualizes benchmark results from OpenSearch. Production **Zathras** clusters typically expose **two** indices: a **run/results** index (`zathras-results`) and a **timeseries** index (`zathras-timeseries`). Configure both in `.env` so behavior matches production; the connection guide below describes when each index is queried.

## Required Python Packages

```
opensearch-py==2.4.2
python-dotenv==1.0.0
requests==2.31.0
urllib3==1.26.18
certifi==2024.2.2
```

**Note:** Always use a virtual environment when installing packages. Never install globally.

## OpenSearch Client Configuration

### Basic Connection Setup

```python
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{'host': 'your-host', 'port': 9200}],
    http_auth=('username', 'password'),
    use_ssl=False,              # Set to True for HTTPS connections
    verify_certs=False,         # Set to False for self-signed certificates
    ssl_show_warn=False,        # Suppress SSL warnings
    timeout=30,                 # Connection timeout in seconds
    max_retries=3,              # Number of retry attempts
    retry_on_timeout=True       # Retry on timeout errors
)
```

### Environment Variables

Use environment variables for configuration (managed via `.env` file with python-dotenv):

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OPENSEARCH_HOST` | Hostname or IP address | `localhost` | `opensearch.example.com` |
| `OPENSEARCH_PORT` | Port number | `9200` | `9200` or `443` |
| `OPENSEARCH_USERNAME` | Authentication username | `admin` | `your-username` |
| `OPENSEARCH_PASSWORD` | Authentication password | `admin` | `your-password` |
| `OPENSEARCH_USE_SSL` | Use HTTPS | `false` | `true` or `false` |
| `OPENSEARCH_VERIFY_CERTS` | Verify SSL certificates | `false` | `true` or `false` |
| `OPENSEARCH_INDEX` | Legacy / primary name for the **run/results** index (run-level benchmark documents) | (empty) | `zathras-results` |
| `OPENSEARCH_INDEX_RESULTS` | Canonical **run** index; if set, overrides `OPENSEARCH_INDEX` for results routing in `BenchmarkDataSource` | (empty) | `zathras-results` |
| `OPENSEARCH_INDEX_TIMESERIES` | **Timeseries / point-level** index (large volume; never bulk-loaded at app startup) | (empty) | `zathras-timeseries` |
| `OPENSEARCH_DASHBOARDS_BASE_URL` | Base URL for OpenSearch Dashboards (Discover deep links from the app UI) | (empty) | `https://dashboards.example.com:5601` |

**Migration from single-index setups:** If you previously set only `OPENSEARCH_INDEX`, keep that variable pointed at your run/results index (typically `zathras-results`). Add `OPENSEARCH_INDEX_RESULTS` and `OPENSEARCH_INDEX_TIMESERIES` with the values above so configuration matches production.

**Client behavior:** `BenchmarkDataSource` in `src/opensearch_client.py` resolves the run index from `OPENSEARCH_INDEX_RESULTS` or, if unset, `OPENSEARCH_INDEX`. It exposes `search_results()` / `scroll_results()` for that index only. It exposes `search_timeseries()` and `fetch_timeseries_for_document()` against `OPENSEARCH_INDEX_TIMESERIES` when that variable is set (required for those calls; omit timeseries env vars only if you never invoke timeseries APIs).

### Two-index model (Zathras production)

Zathras clusters expose at least two relevant indices:

| Index (typical name) | Role | Scale (order of magnitude) |
|----------------------|------|----------------------------|
| **`zathras-results`** | One document per logical test result; comparisons, regression lists, run-level deep links | Thousands |
| **`zathras-timeseries`** | Many documents per parent result (sequence/point rows); within-run drill-down | Hundreds of thousands |

**Query intent (target architecture):** Pulse-style KPIs and aggregations should target **results** (and optional future rollups), not full scans of **timeseries**. Narrow, filtered queries against **timeseries** are for engineer drill-down (e.g. by `metadata.document_id`, time bounds, `timeseries_id`). See [DASHBOARD_REDESIGN_AND_DATA_PLAN.md](DASHBOARD_REDESIGN_AND_DATA_PLAN.md) §4.

Configure both names in `.env` for production parity; avoid loading the full timeseries index into the app (use bounded `fetch_timeseries_for_document` or narrow `search_timeseries` queries only).

### Discover deep links

When `OPENSEARCH_DASHBOARDS_BASE_URL` is set, the investigation drill-down shows **View in OpenSearch Discover (most recent run)** using `src/opensearch_links.py::opensearch_discover_url_for_document`. The link targets **Discover** with a Kuery filter on `metadata.document_id` and uses the configured results index name (`OPENSEARCH_INDEX_RESULTS` or `OPENSEARCH_INDEX`).

For **point-level** rows in `zathras-timeseries`, the same module provides `opensearch_discover_url_for_timeseries_id` (Kuery on `metadata.timeseries_id`) and `timeseries_index_name()` (reads `OPENSEARCH_INDEX_TIMESERIES`). Wire these when the UI surfaces a `timeseries_id`; index pattern must match your timeseries index name in Dashboards.

**Operator notes:**

- Use the **Dashboards base URL only** (scheme + host + port), not the full `/app/discover` path.
- Your **index pattern** in OpenSearch Dashboards must match the linked name (often `zathras-results`). If the pattern title differs from the raw index, align `.env` or create a matching index pattern in Dashboards.
- Dashboards versions differ slightly in URL state; if a link opens Discover but filters look wrong, copy a working Discover URL from your cluster and compare `_a` / `_g` fragments to adjust `opensearch_links.py` if needed.

### Loading Configuration

```python
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'host': os.getenv('OPENSEARCH_HOST', 'localhost'),
    'port': int(os.getenv('OPENSEARCH_PORT', '9200')),
    'username': os.getenv('OPENSEARCH_USERNAME', 'admin'),
    'password': os.getenv('OPENSEARCH_PASSWORD', 'admin'),
    'use_ssl': os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true',
    'verify_certs': os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true',
    'index': os.getenv('OPENSEARCH_INDEX', ''),
    'index_results': os.getenv('OPENSEARCH_INDEX_RESULTS', '') or os.getenv('OPENSEARCH_INDEX', ''),
    'index_timeseries': os.getenv('OPENSEARCH_INDEX_TIMESERIES', ''),
}
```

## Connection Verification

Always verify the connection on initialization:

```python
from opensearchpy import exceptions
import sys

try:
    info = client.info()
    print(f"✓ Connected to OpenSearch cluster: {info['cluster_name']}")
    print(f"  Version: {info['version']['number']}")
except exceptions.ConnectionError as e:
    print(f"✗ Failed to connect to OpenSearch: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error during connection: {e}", file=sys.stderr)
    sys.exit(1)
```

## Common Operations

### Get Index Information

```python
# Get document count
count = client.count(index='your-index')
total_docs = count['count']

# Get index statistics
stats = client.indices.stats(index='your-index')
size_bytes = stats['_all']['primaries']['store']['size_in_bytes']
```

### List All Indices

```python
indices = client.indices.get_alias(index="*")
# Filter out system indices (those starting with '.')
user_indices = [idx for idx in indices.keys() if not idx.startswith('.')]
```

### Query Data (Basic Search)

```python
# Match all query
response = client.search(
    index='your-index',
    body={
        "query": {
            "match_all": {}
        },
        "size": 100  # Limit results
    }
)

hits = response['hits']['hits']
for hit in hits:
    doc_id = hit['_id']
    source = hit['_source']  # The actual document
```

### Query with Filtering

```python
# Example: Filter by date range or specific fields
response = client.search(
    index='your-index',
    body={
        "query": {
            "bool": {
                "must": [
                    {"range": {"timestamp": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
                    {"term": {"status": "completed"}}
                ]
            }
        },
        "size": 1000
    }
)
```

### Scroll API for Large Result Sets

When downloading large amounts of data (as done in the POC):

```python
# Initial search with scroll
response = client.search(
    index='your-index',
    scroll='2m',  # Keep scroll context alive for 2 minutes
    size=1000,    # Batch size
    body={"query": {"match_all": {}}}
)

scroll_id = response['_scroll_id']
hits = response['hits']['hits']
all_records = hits.copy()

# Continue scrolling
while len(hits) > 0:
    response = client.scroll(
        scroll_id=scroll_id,
        scroll='2m'
    )
    scroll_id = response['_scroll_id']
    hits = response['hits']['hits']
    all_records.extend(hits)

# Clean up (optional, will auto-expire)
try:
    client.clear_scroll(scroll_id=scroll_id)
except Exception:
    pass
```

## Document Structure

Each document retrieved from OpenSearch has the following structure:

```json
{
  "_index": "index-name",
  "_id": "document-id",
  "_score": 1.0,
  "_source": {
    // Actual document data
    // Fields will vary based on benchmark results structure
  }
}
```

For the dashboard, you'll primarily work with the `_source` field which contains the actual benchmark data.

## Error Handling

Common exceptions to handle:

```python
from opensearchpy import exceptions

try:
    # Your OpenSearch operation
    pass
except exceptions.ConnectionError as e:
    # Network/connection issues
    print(f"Connection error: {e}")
except exceptions.NotFoundError as e:
    # Index or document not found
    print(f"Not found: {e}")
except exceptions.RequestError as e:
    # Invalid query or request
    print(f"Request error: {e}")
except exceptions.AuthenticationException as e:
    # Authentication failed
    print(f"Authentication error: {e}")
except Exception as e:
    # Catch-all for unexpected errors
    print(f"Unexpected error: {e}")
```

## Security Best Practices

1. **Never commit credentials** - Always use `.env` files and add `.env` to `.gitignore`
2. **Use SSL in production** - Set `OPENSEARCH_USE_SSL=true` for production environments
3. **Verify certificates** - Only disable certificate verification for development/internal servers
4. **Least privilege** - Use read-only credentials for the dashboard if possible
5. **Environment isolation** - Use separate credentials for dev/staging/production

## Performance Considerations

1. **Pagination** - Use `from` and `size` parameters for paginated results in the dashboard
2. **Caching** - Consider caching frequent queries to reduce load on OpenSearch
3. **Aggregations** - Use OpenSearch aggregations for summary statistics rather than processing all documents client-side
4. **Connection pooling** - The opensearch-py client handles connection pooling automatically
5. **Batch operations** - Use scroll API or `from`/`size` for large datasets

## Troubleshooting

### Common Issues

**302 Redirect Error:**
- Connecting to dashboard URL instead of API endpoint
- Solution: Remove `-dashboards` from hostname

**Connection Timeout:**
- Increase `timeout` parameter in client configuration
- Check network connectivity and firewall rules

**SSL Certificate Errors:**
- For self-signed certificates: `verify_certs=False`, `ssl_show_warn=False`
- For production: Install proper CA certificates

**Authentication Failures:**
- Verify credentials in `.env` file
- Check if IP is whitelisted (if applicable)

**Index Not Found:**
- Verify index name (case-sensitive)
- Use `client.indices.get_alias(index="*")` to list available indices

## Example: Dashboard Connection Class

The project implementation lives in `src/opensearch_client.py`. Below is the same **index resolution pattern** that module uses (module-level helpers, stripped env values, `results_index` plus backward-compatible `index_name`).

```python
from opensearchpy import OpenSearch, exceptions
from dotenv import load_dotenv
import os
import logging

def _resolve_results_index() -> str:
    return (os.getenv("OPENSEARCH_INDEX_RESULTS") or os.getenv("OPENSEARCH_INDEX") or "").strip()

def _resolve_timeseries_index() -> str:
    return (os.getenv("OPENSEARCH_INDEX_TIMESERIES") or "").strip()

class BenchmarkDataSource:
    """Data source connector for OpenSearch benchmark results."""
    
    def __init__(self):
        load_dotenv()

        self.results_index = _resolve_results_index()
        self.timeseries_index = _resolve_timeseries_index()
        self.index_name = self.results_index  # backward-compatible alias (run documents)
        self.client = OpenSearch(
            hosts=[{
                'host': os.getenv('OPENSEARCH_HOST', 'localhost'),
                'port': int(os.getenv('OPENSEARCH_PORT', '9200'))
            }],
            http_auth=(
                os.getenv('OPENSEARCH_USERNAME', 'admin'),
                os.getenv('OPENSEARCH_PASSWORD', 'admin')
            ),
            use_ssl=os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true',
            verify_certs=os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true',
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        self._verify_connection()
        
    def _verify_connection(self):
        """Verify connection to OpenSearch."""
        try:
            info = self.client.info()
            logging.info(f"Connected to OpenSearch: {info['cluster_name']}")
        except Exception as e:
            logging.error(f"Failed to connect to OpenSearch: {e}")
            raise
    
    def get_benchmark_results(self, filters=None, limit=1000):
        """
        Fetch benchmark results with optional filtering.
        
        Args:
            filters: Dictionary of filters to apply
            limit: Maximum number of results to return
            
        Returns:
            List of benchmark result documents
        """
        query = {"query": {"match_all": {}}}
        
        if filters:
            # Build query based on filters
            # Implementation depends on your data structure
            pass
        
        try:
            response = self.client.search(
                index=self.results_index,
                body=query,
                size=limit
            )
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception as e:
            logging.error(f"Error fetching benchmark results: {e}")
            return []
```

## Data Format Note

The proof-of-concept downloaded benchmark results are stored in a JSON file with the format:

```json
[
  {
    "_index": "...",
    "_id": "...",
    "_score": ...,
    "_source": {
      // Benchmark result data
    }
  },
  // ... more records
]
```

Each record's `_source` field contains the actual performance benchmark data that should be visualized in the dashboard.

## Additional Resources

- [OpenSearch Python Client Documentation](https://opensearch.org/docs/latest/clients/python-high-level/)
- [OpenSearch Query DSL](https://opensearch.org/docs/latest/query-dsl/)
- [OpenSearch Aggregations](https://opensearch.org/docs/latest/aggregations/)

---

**Project Guidelines:**
- Always use virtual environments (`python3 -m venv venv`)
- Follow PEP 8 style guidelines
- Include comprehensive error handling
- Log operations for debugging
- Attribute git commits with: "Assisted by Cursor using Claude Sonnet 4.5"

