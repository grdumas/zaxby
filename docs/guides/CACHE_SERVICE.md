# Cache Service Guide

## Overview

The cache service provides a configurable caching layer for query results with support for multiple backends and graceful degradation.

**Implementation:** RPOPC-1168

## Features

- **Multiple backends**: In-memory (dev), Redis (production), and null (disabled)
- **Deterministic cache keys**: Generated from query parameters via SHA-256 hashing
- **Configurable TTLs**: Per-query-type TTL configuration
- **Cache metrics**: Hit/miss/error tracking for monitoring
- **Graceful fallback**: Cache failures don't break queries

## Configuration

All configuration is done via environment variables in `.env`:

```bash
# Cache backend type: 'simple' (in-memory), 'redis', or 'null' (disabled)
CACHE_TYPE=simple

# Redis URL (required when CACHE_TYPE=redis)
CACHE_REDIS_URL=redis://localhost:6379/0

# Default TTL in seconds (default: 300 = 5 minutes)
CACHE_DEFAULT_TTL=300

# Query-type-specific TTLs (optional overrides)
CACHE_TTL_PULSE_KPIS=300          # 5 minutes
CACHE_TTL_TRACK_EXCEPTIONS=900    # 15 minutes
CACHE_TTL_CATEGORY_ROLLUP=300     # 5 minutes
CACHE_TTL_ACTIVITY_TIMELINE=300   # 5 minutes
CACHE_TTL_SCOPE_FOOTNOTE=300      # 5 minutes
```

## Cache Backends

### Simple (In-Memory)

Default backend, good for development and testing:
- No external dependencies
- Data lost on restart
- Memory-bound by available RAM

```bash
CACHE_TYPE=simple
```

### Redis

Production-grade distributed cache:
- Persistent across restarts
- Shared across multiple instances
- Requires Redis server

```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```

### Null (Disabled)

Disables caching for testing:
- Always returns cache misses
- Useful for benchmarking or debugging

```bash
CACHE_TYPE=null
```

## Usage

### Basic Usage

```python
from src.cache_service import get_cache_service

# Get the cache service
cache = get_cache_service()

# Define query parameters
query_params = {
    'query_type': 'pulse_kpis',
    'filters': {'os': 'rhel', 'version': '9.4'},
    'date_range': '2024-01-01:2024-12-31'
}

# Try to get from cache
result = cache.get(query_params)
if result is None:
    # Cache miss - fetch from OpenSearch
    result = fetch_from_opensearch(query_params)
    
    # Store in cache
    cache.set(query_params, result)
else:
    # Cache hit
    print("Loaded from cache")

# Process result
process_data(result)
```

### With Custom TTL

```python
# Set with custom TTL (60 seconds)
cache.set(query_params, result, ttl=60)
```

### Invalidation

```python
# Invalidate specific cache entry
cache.invalidate(query_params)

# Clear all cache entries
cache.clear()
```

### Monitoring

```python
# Get cache metrics
metrics = cache.get_metrics()
print(f"Hit rate: {metrics.hit_rate:.1f}%")
print(f"Hits: {metrics.hits}, Misses: {metrics.misses}")
print(f"Errors: {metrics.errors}")

# Reset metrics
cache.reset_metrics()
```

## Integration Example

Example integration with query service:

```python
from src.cache_service import get_cache_service
from src.query_service import fetch_results_category_kpis

def get_category_kpis_cached(client):
    """Fetch category KPIs with caching."""
    cache = get_cache_service()
    
    # Define cache key parameters
    params = {
        'query_type': 'category_rollup',
        'template_id': 'TPL_CATEGORY_ROLLUP'
    }
    
    # Try cache first
    result = cache.get(params)
    if result is not None:
        return result
    
    # Cache miss - fetch from OpenSearch
    snapshot = fetch_results_category_kpis(client)
    
    # Only cache successful results
    if snapshot.error is None:
        cache.set(params, snapshot)
    
    return snapshot
```

## Cache Key Generation

Cache keys are deterministically generated from query parameters:

1. Parameters are serialized to JSON with sorted keys
2. SHA-256 hash is computed
3. Key format: `cache:{query_type}:{hash_prefix}`

Example:
```python
params = {'query_type': 'pulse_kpis', 'os': 'rhel'}
# Generates: cache:pulse_kpis:a3f2c1d4e5b6...
```

The same parameters always generate the same key, regardless of dict key order.

## Error Handling

The cache service handles all errors gracefully:

- **Redis connection failures**: Falls back to simple in-memory cache
- **Get/Set errors**: Return None/False and increment error metrics
- **Invalid TTL values**: Fall back to defaults

This ensures that cache failures never break application functionality.

## Best Practices

1. **Use query_type**: Always include `query_type` in cache params for readable keys and automatic TTL selection
2. **Cache only successful results**: Don't cache errors or null results
3. **Monitor hit rates**: Use metrics to tune TTL values
4. **Clear on data changes**: Invalidate cache when underlying data changes
5. **Production Redis**: Use Redis in production for multi-instance deployments

## Limitations

- **Simple cache**: Not suitable for multi-instance deployments (each instance has its own cache)
- **Memory-bound**: Simple cache limited by available RAM
- **No query result streaming**: Cache stores complete results in memory

## Testing

Comprehensive test suite in `tests/test_cache_service.py`:

```bash
pytest tests/test_cache_service.py -v
```

Test coverage includes:
- Cache key generation and determinism
- All three backend types
- TTL and expiry
- Error handling and fallback
- Metrics tracking
