# Caching Guide

This guide explains the caching implementation in Zaxby, including configuration, performance tuning, and best practices.

## Overview

Zaxby implements a multi-backend caching system to reduce expensive OpenSearch queries and improve dashboard responsiveness. The cache layer sits between the UI callbacks and the query service, transparently caching query results with configurable TTLs.

### Architecture

```
UI Callbacks
    ↓
Query Service (with cache integration)
    ↓
Cache Service (simple/Redis backends)
    ↓
OpenSearch Client
```

## Cache Backends

### Simple (In-Memory)

The default backend for development and small deployments.

**Pros:**
- No external dependencies
- Fast (sub-millisecond reads)
- Easy to configure

**Cons:**
- Memory limited (default: 1000 entries)
- Not shared across workers/processes
- Lost on restart

**Configuration:**
```bash
CACHE_TYPE=simple
CACHE_DEFAULT_TTL=300  # 5 minutes
```

### Redis

Production-ready distributed cache.

**Pros:**
- Shared across workers
- Survives restarts
- Configurable memory limits
- Production-grade

**Cons:**
- Requires Redis server
- Network latency (though minimal)
- Additional infrastructure

**Configuration:**
```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=300
```

### Null (Disabled)

For testing or explicitly disabling cache.

**Configuration:**
```bash
CACHE_TYPE=null
```

## TTL Configuration

Different query types have different TTL defaults based on their update frequency:

| Query Type | Default TTL | Rationale |
|-----------|-------------|-----------|
| `pulse_kpis` | 300s (5 min) | Real-time KPIs update frequently |
| `track_exceptions` | 900s (15 min) | Historical exception data changes slowly |
| `category_rollup` | 300s (5 min) | Moderate update frequency |
| `activity_timeline` | 300s (5 min) | Monthly aggregations are stable |
| `scope_footnote` | 300s (5 min) | Index metadata changes moderately |

### Override TTLs

Set environment variables to override defaults:

```bash
# Set Pulse KPI TTL to 10 minutes
CACHE_TTL_PULSE_KPIS=600

# Set Track exceptions TTL to 30 minutes
CACHE_TTL_TRACK_EXCEPTIONS=1800

# Set category rollup TTL to 2 minutes
CACHE_TTL_CATEGORY_ROLLUP=120
```

## Cache Keys

Cache keys are generated deterministically from query parameters:

```python
cache_key = f"cache:{query_type}:{hash(params)}"
```

**Key components:**
- `query_type`: Type of query (e.g., 'pulse_kpis', 'track_exceptions')
- `hash(params)`: SHA256 hash of sorted query parameters

**Example:**
```
cache:pulse_kpis:a1b2c3d4e5f6...
cache:category_rollup:f6e5d4c3b2a1...
```

This ensures:
- Identical queries hit the same cache entry
- Different filters generate different keys
- Keys are deterministic across restarts

## Cache Invalidation

### Automatic Invalidation

The system automatically invalidates cache in these scenarios:

1. **Filter Changes** - When user changes any filter (date range, cloud provider, etc.)
   - Invalidates: ALL cache entries
   - Rationale: Filters affect all query results

2. **Mode Switch** - When switching between Pulse/Track/Investigate
   - Invalidates: Mode-specific cache entries
   - Rationale: Different modes have different data requirements

3. **TTL Expiration** - When cached entry exceeds its TTL
   - Invalidates: Individual expired entries
   - Rationale: Prevents stale data

### Manual Invalidation

The cache service provides methods for manual invalidation:

```python
from src.cache_service import get_cache_service

cache = get_cache_service()

# Invalidate specific query
cache.invalidate(query_params)

# Invalidate by query type
cache.invalidate_by_query_type('pulse_kpis')

# Invalidate by mode
cache.invalidate_by_mode('pulse')  # Clears pulse_kpis, category_rollup, etc.

# Clear entire cache
cache.clear()
```

## Performance Tuning

### Measuring Performance

Use the performance test suite:

```bash
pytest tests/performance/test_cache_performance.py -v -s
```

This measures:
- Cache write/read latency (p50, p95, p99)
- Cache hit rate
- Cache eviction performance
- Speedup vs uncached queries

### Tuning TTLs

**Short TTLs (< 5 minutes):**
- Pro: Fresh data, less stale risk
- Con: More cache misses, higher OpenSearch load
- Use for: Real-time dashboards, frequently changing data

**Long TTLs (> 15 minutes):**
- Pro: Higher hit rate, lower OpenSearch load
- Con: Staler data, slower to reflect changes
- Use for: Historical data, stable aggregations

**Recommended approach:**
1. Start with defaults (5-15 minutes)
2. Monitor cache hit rate (target: >= 60%)
3. If hit rate is low, increase TTLs
4. If data staleness is an issue, decrease TTLs

### Cache Size Limits

**Simple backend:**
- Default max size: 1000 entries
- LRU eviction when full
- Adjust: Modify `SIMPLE_CACHE_MAX_SIZE` in `cache_service.py`

**Redis backend:**
- Configure Redis `maxmemory` and `maxmemory-policy`
- Recommended policy: `allkeys-lru`
- Example Redis config:
  ```
  maxmemory 256mb
  maxmemory-policy allkeys-lru
  ```

### Memory Estimation

Estimate cache memory usage:

```python
# Average entry size
entry_size = 10_000 bytes  # Typical query result

# For 1000 entries
total_memory = 1000 * 10_000 = 10 MB

# Add overhead
overhead = total_memory * 0.2  # 20% overhead
total = total_memory + overhead = 12 MB
```

## Monitoring

### Cache Metrics

Access cache metrics programmatically:

```python
from src.cache_service import get_cache_service

cache = get_cache_service()
metrics = cache.get_metrics()

print(f"Hits: {metrics.hits}")
print(f"Misses: {metrics.misses}")
print(f"Errors: {metrics.errors}")
print(f"Hit rate: {metrics.hit_rate:.1f}%")
```

### Log Messages

Cache operations are logged:

```
INFO - Cache HIT for results_overview_aggregates | cache_age_seconds=123.4 | hit_rate=65.2%
INFO - Cache MISS for results_overview_aggregates | hit_rate=58.1%
INFO - Cache cleared due to filter change
INFO - Switched to Track mode, invalidated 15 Pulse cache entries
```

### UI Indicators

Cache status is shown in the UI:

```
Data: mode=opensearch · results index: benchmark-results · cached 2m ago
```

This helps users understand data freshness.

## Best Practices

### 1. Use Appropriate TTLs

Match TTL to data update frequency:
- Real-time metrics: 1-5 minutes
- Hourly updates: 15-30 minutes
- Daily updates: 1-6 hours
- Static data: 24+ hours

### 2. Monitor Hit Rate

Target: >= 60% cache hit rate under normal usage

If hit rate is low:
- Increase TTLs
- Check if filters are changing frequently
- Verify cache size is sufficient

### 3. Handle Cache Failures Gracefully

Always handle cache failures:

```python
try:
    result = cache.get(params)
    if result:
        return result
except Exception as e:
    logger.error(f"Cache error: {e}")
    # Fall through to query

# Execute query if cache miss or error
return execute_query()
```

### 4. Use Mode-Specific Invalidation

When switching modes, invalidate only that mode's cache:

```python
# Good - targeted invalidation
cache.invalidate_by_mode('pulse')

# Bad - clears everything including other modes
cache.clear()
```

### 5. Test Cache Behavior

Include cache tests in your test suite:

```python
def test_query_uses_cache(cache_service):
    cache_service.reset_metrics()
    
    # First call - miss
    result1 = fetch_kpis()
    assert cache_service.metrics.misses == 1
    
    # Second call - hit
    result2 = fetch_kpis()
    assert cache_service.metrics.hits == 1
    assert result1 == result2
```

## Troubleshooting

### Issue: Low Hit Rate

**Symptoms:** Cache hit rate < 40%

**Causes:**
- Filters changing frequently
- TTLs too short
- Cache too small (evicting before reuse)

**Solutions:**
1. Increase TTLs
2. Increase cache size
3. Review filter change patterns

### Issue: Stale Data

**Symptoms:** UI shows old data after changes

**Causes:**
- TTLs too long
- Invalidation not triggered
- Cache not cleared on filter change

**Solutions:**
1. Decrease TTLs
2. Add invalidation triggers
3. Verify invalidation logic

### Issue: High Memory Usage

**Symptoms:** Process memory grows unbounded

**Causes:**
- Cache size limit not enforced
- Large query results
- Memory leaks

**Solutions:**
1. Set cache size limits
2. Monitor entry sizes
3. Use Redis with maxmemory limit

### Issue: Cache Not Working

**Symptoms:** All queries are cache misses

**Causes:**
- Cache type set to 'null'
- Redis connection failed (fallback to simple)
- Cache key generation inconsistent

**Solutions:**
1. Check `CACHE_TYPE` environment variable
2. Verify Redis connection
3. Review cache key generation logic

## Performance Benchmarks

Based on performance tests (`test_cache_performance.py`):

### Simple Backend

- Write latency: < 5ms avg
- Read latency (hit): < 1ms avg
- Read latency (miss): < 1ms avg
- LRU eviction: < 10ms avg
- Speedup: > 10x for expensive queries
- Latency reduction: > 80%

### Redis Backend

- Write latency: < 10ms avg (includes network)
- Read latency (hit): < 2ms avg
- Read latency (miss): < 2ms avg
- Speedup: > 10x for expensive queries
- Latency reduction: > 75%

### Target Metrics

- Cache hit rate: >= 60%
- Latency reduction: >= 80%
- OpenSearch query reduction: >= 50%
- End-to-end page load improvement: >= 40%

## Migration Guide

### From No Cache to Simple Cache

1. No code changes needed - cache is integrated in query_service
2. Set environment variable:
   ```bash
   CACHE_TYPE=simple
   ```
3. Monitor metrics and tune TTLs

### From Simple to Redis

1. Deploy Redis server
2. Update environment:
   ```bash
   CACHE_TYPE=redis
   CACHE_REDIS_URL=redis://your-redis-host:6379/0
   ```
3. Configure Redis maxmemory and eviction policy
4. Monitor cache hit rate and latency

## References

- Implementation: `src/cache_service.py`
- Integration: `src/query_service.py`
- Tests: `tests/performance/test_cache_performance.py`
- Jira: RPOPC-1116, RPOPC-1170, RPOPC-1171, RPOPC-1172
