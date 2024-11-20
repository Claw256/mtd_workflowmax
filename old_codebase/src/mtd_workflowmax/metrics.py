"""Metrics collection for MTD's WorkflowMax 2 API client."""

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
API_REQUESTS = Counter(
    'workflowmax_api_requests_total',
    'Total number of API requests made',
    ['endpoint', 'method', 'status']
)

API_REQUEST_DURATION = Histogram(
    'workflowmax_api_request_duration_seconds',
    'API request duration in seconds',
    ['endpoint', 'method'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Rate limiting metrics
RATE_LIMIT_REMAINING = Gauge(
    'workflowmax_rate_limit_remaining',
    'Number of API requests remaining in the current time window'
)

RATE_LIMIT_RESET = Gauge(
    'workflowmax_rate_limit_reset_seconds',
    'Time until the rate limit resets in seconds'
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'workflowmax_circuit_breaker_state',
    'Current state of the circuit breaker (0=open, 1=half-open, 2=closed)'
)

# Cache metrics
CACHE_HITS = Counter(
    'workflowmax_cache_hits_total',
    'Total number of cache hits',
    ['cache_name']
)

CACHE_MISSES = Counter(
    'workflowmax_cache_misses_total',
    'Total number of cache misses',
    ['cache_name']
)

# Connection pool metrics
CONNECTION_POOL_SIZE = Gauge(
    'workflowmax_connection_pool_size',
    'Current size of the connection pool'
)

CONNECTION_POOL_USED = Gauge(
    'workflowmax_connection_pool_used',
    'Number of connections currently in use'
)

# Batch processing metrics
BATCH_PROCESSING_SIZE = Histogram(
    'workflowmax_batch_size',
    'Size of processed batches',
    buckets=(1, 5, 10, 25, 50, 100)
)

BATCH_PROCESSING_DURATION = Histogram(
    'workflowmax_batch_duration_seconds',
    'Duration of batch processing in seconds',
    buckets=(1, 5, 10, 30, 60, 120)
)
