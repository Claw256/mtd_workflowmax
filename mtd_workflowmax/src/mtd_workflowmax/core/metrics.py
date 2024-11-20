"""Prometheus metrics for WorkflowMax API."""

from prometheus_client import Counter, Gauge, Histogram

# API request metrics
API_REQUESTS = Counter(
    'workflowmax_api_requests_total',
    'Total number of API requests',
    ['endpoint', 'method', 'status']
)

API_REQUEST_DURATION = Histogram(
    'workflowmax_api_request_duration_seconds',
    'API request duration in seconds',
    ['endpoint', 'method'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Rate limit metrics
RATE_LIMIT_REMAINING = Gauge(
    'workflowmax_rate_limit_remaining',
    'Number of API requests remaining in current window'
)

RATE_LIMIT_RESET = Gauge(
    'workflowmax_rate_limit_reset_seconds',
    'Time until rate limit reset in seconds'
)

# Connection pool metrics
CONNECTION_POOL_SIZE = Gauge(
    'workflowmax_connection_pool_size',
    'Maximum size of the connection pool'
)

CONNECTION_POOL_USED = Gauge(
    'workflowmax_connection_pool_used',
    'Number of connections currently in use'
)

# Batch processing metrics
BATCH_PROCESSING_DURATION = Histogram(
    'workflowmax_batch_processing_duration_seconds',
    'Duration of batch processing operations',
    buckets=(1, 5, 10, 30, 60, 120)
)

BATCH_PROCESSING_SIZE = Histogram(
    'workflowmax_batch_processing_size',
    'Size of processed batches',
    buckets=(1, 5, 10, 25, 50, 100)
)

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'workflowmax_circuit_breaker_state',
    'Current state of the circuit breaker (0=open, 1=half-open, 2=closed)',
    ['endpoint']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'workflowmax_circuit_breaker_failures_total',
    'Total number of circuit breaker failures',
    ['endpoint']
)

CIRCUIT_BREAKER_TRIPS = Counter(
    'workflowmax_circuit_breaker_trips_total',
    'Total number of times circuit breaker has tripped',
    ['endpoint']
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

CACHE_SIZE = Gauge(
    'workflowmax_cache_size',
    'Current number of items in cache',
    ['cache_name']
)

CACHE_EVICTIONS = Counter(
    'workflowmax_cache_evictions_total',
    'Total number of cache evictions',
    ['cache_name']
)

# Authentication metrics
AUTH_ATTEMPTS = Counter(
    'workflowmax_auth_attempts_total',
    'Total number of authentication attempts',
    ['status']  # success, failure
)

AUTH_TOKEN_REFRESHES = Counter(
    'workflowmax_auth_token_refreshes_total',
    'Total number of token refresh attempts',
    ['status']  # success, failure
)

# Service operation metrics
SERVICE_OPERATION_DURATION = Histogram(
    'workflowmax_service_operation_duration_seconds',
    'Duration of service operations',
    ['service', 'operation'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

SERVICE_OPERATION_FAILURES = Counter(
    'workflowmax_service_operation_failures_total',
    'Total number of service operation failures',
    ['service', 'operation', 'error_type']
)

# Repository metrics
REPOSITORY_OPERATION_DURATION = Histogram(
    'workflowmax_repository_operation_duration_seconds',
    'Duration of repository operations',
    ['repository', 'operation'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

REPOSITORY_OPERATION_FAILURES = Counter(
    'workflowmax_repository_operation_failures_total',
    'Total number of repository operation failures',
    ['repository', 'operation', 'error_type']
)
