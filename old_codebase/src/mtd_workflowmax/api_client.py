"""Enhanced API client for WorkflowMax API."""

import time
import asyncio
from typing import Dict, Optional, List, Any, AsyncGenerator
from contextlib import contextmanager
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.poolmanager import PoolManager
import urllib3

from .config import Config
from .exceptions import (
    AuthenticationError,
    RateLimitError,
    WorkflowMaxAPIError,
    handle_api_errors,
    validate_response
)
from .logging_config import get_logger
from . import metrics

logger = get_logger('workflowmax.api_client')

class RateLimiter:
    """Token bucket rate limiter with enhanced features."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize rate limiter with configuration.
        
        Args:
            config: Optional Config instance. If not provided, will create new one.
        """
        self.config = config or Config()
        rate_limit_config = self.config.get_rate_limit_config()
        
        self.concurrent_limit = rate_limit_config.concurrent_limit
        self.minute_limit = rate_limit_config.minute_limit
        self.daily_limit = rate_limit_config.daily_limit
        
        self.active_calls = 0
        self.minute_calls = 0
        self.daily_calls = 0
        
        self.minute_reset = time.time() + 60
        self.daily_reset = time.time() + 86400
        
        # Track rate limit metrics
        metrics.RATE_LIMIT_REMAINING.set(self.minute_limit)
    
    @contextmanager
    def acquire(self):
        """Context manager for rate limiting.
        
        Yields:
            None
            
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        self._wait_for_capacity()
        
        try:
            self.active_calls += 1
            self.minute_calls += 1
            self.daily_calls += 1
            
            # Update metrics
            metrics.RATE_LIMIT_REMAINING.set(self.minute_limit - self.minute_calls)
            
            yield
        finally:
            self.active_calls -= 1
    
    def _wait_for_capacity(self):
        """Wait until capacity is available."""
        start_time = time.time()
        max_wait = 60  # Maximum wait time in seconds
        
        while True:
            now = time.time()
            
            # Check if we've waited too long
            if now - start_time > max_wait:
                raise RateLimitError(
                    "Rate limit wait timeout exceeded",
                    reset_time=int(min(self.minute_reset, self.daily_reset) - now)
                )
            
            # Reset counters if time windows have elapsed
            if now > self.minute_reset:
                self.minute_calls = 0
                self.minute_reset = now + 60
                
            if now > self.daily_reset:
                self.daily_calls = 0
                self.daily_reset = now + 86400
            
            # Check if we have capacity
            if (self.active_calls < self.concurrent_limit and
                self.minute_calls < self.minute_limit and
                self.daily_calls < self.daily_limit):
                break
            
            # Wait before checking again
            time.sleep(0.1)

class CustomPoolManager(PoolManager):
    """Enhanced connection pool manager."""
    
    def __init__(self, **kwargs):
        """Initialize with improved settings."""
        # Set default timeouts
        kwargs.setdefault('timeout', 30.0)
        
        # Enable connection pooling
        kwargs.setdefault('maxsize', 200)
        kwargs.setdefault('retries', False)
        
        # Enable keep-alive
        kwargs.setdefault('keepalive', True)
        
        super().__init__(**kwargs)
        logger.debug("Initialized CustomPoolManager with settings: %s", kwargs)

class APIClient:
    """Enhanced WorkflowMax API client."""
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.config = Config()
        api_config = self.config.get_api_config()
        
        self.base_url = api_config.base_url
        self.tokens = None
        self.org_id = None
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=api_config.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'])
        )
        
        # Create session with enhanced settings
        self.session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=api_config.pool_connections,
            pool_maxsize=api_config.pool_maxsize,
            pool_block=False
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(self.config)
        
        # Update connection pool metrics
        metrics.CONNECTION_POOL_SIZE.set(api_config.pool_maxsize)
        logger.debug("API client initialized with pool size %d", api_config.pool_maxsize)
    
    def set_auth(self, tokens: Dict, org_id: str):
        """Set authentication tokens and organization ID.
        
        Args:
            tokens: Dictionary containing access and refresh tokens
            org_id: Organization ID
        """
        self.tokens = tokens
        self.org_id = org_id
        logger.info("Authentication set for organization %s", org_id)
    
    @contextmanager
    def _track_connection(self):
        """Track active connections for metrics."""
        metrics.CONNECTION_POOL_USED.inc()
        try:
            yield
        finally:
            metrics.CONNECTION_POOL_USED.dec()
    
    def _update_rate_limit_metrics(self, response: requests.Response):
        """Update rate limit metrics from response headers.
        
        Args:
            response: Response object containing rate limit headers
        """
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        
        if remaining is not None:
            metrics.RATE_LIMIT_REMAINING.set(float(remaining))
            logger.debug("Rate limit remaining: %s", remaining)
        if reset is not None:
            metrics.RATE_LIMIT_RESET.set(float(reset))
            logger.debug("Rate limit reset in %s seconds", reset)
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests.
        
        Returns:
            Dict[str, str]: Headers dictionary
            
        Raises:
            AuthenticationError: If not authenticated
        """
        if not self.tokens or not self.org_id:
            logger.error("Attempted to get headers without authentication")
            raise AuthenticationError("Not authenticated")
            
        return {
            'Authorization': f"Bearer {self.tokens['access_token']}",
            'account_id': self.org_id,
            'Accept': 'application/xml',
            'Content-Type': 'application/xml'
        }
    
    @handle_api_errors()
    @validate_response
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request with enhanced error handling and metrics.
        
        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            **kwargs: Additional arguments for requests
            
        Returns:
            requests.Response: Response from the API
            
        Raises:
            Various exceptions defined in exceptions.py
        """
        with self.rate_limiter.acquire(), self._track_connection():
            # Merge default headers with any custom headers
            headers = self._get_default_headers()
            if 'headers' in kwargs:
                headers.update(kwargs['headers'])
            kwargs['headers'] = headers
            
            url = urljoin(self.base_url, endpoint)
            logger.debug("Making %s request to %s", method, url)
            
            with metrics.API_REQUEST_DURATION.labels(
                endpoint=endpoint,
                method=method
            ).time():
                response = self.session.request(
                    method,
                    url,
                    timeout=self.config.api.timeout,
                    **kwargs
                )
            
            # Update metrics
            metrics.API_REQUESTS.labels(
                endpoint=endpoint,
                method=method,
                status=response.status_code
            ).inc()
            
            self._update_rate_limit_metrics(response)
            
            logger.debug("Request successful: %s %s", 
                       response.status_code, response.reason)
            return response

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """Make a GET request."""
        return self.request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: str) -> requests.Response:
        """Make a POST request."""
        return self.request('POST', endpoint, data=data)

    def put(self, endpoint: str, data: str) -> requests.Response:
        """Make a PUT request."""
        return self.request('PUT', endpoint, data=data)

    def delete(self, endpoint: str) -> requests.Response:
        """Make a DELETE request."""
        return self.request('DELETE', endpoint)
    
    async def batch_get(self, endpoints: List[str], 
                       params: Optional[List[Dict]] = None) -> AsyncGenerator[requests.Response, None]:
        """Process multiple GET requests in batches.
        
        Args:
            endpoints: List of API endpoints to call
            params: Optional list of parameters for each endpoint
            
        Yields:
            requests.Response: Response from each API call
        """
        if params is None:
            params = [None] * len(endpoints)
        
        logger.info("Starting batch request for %d endpoints", len(endpoints))
        
        # Process in batches
        batch_size = self.config.api.batch_size
        for i in range(0, len(endpoints), batch_size):
            batch_endpoints = endpoints[i:i + batch_size]
            batch_params = params[i:i + batch_size]
            
            logger.debug("Processing batch %d-%d", i, i + len(batch_endpoints))
            
            with metrics.BATCH_PROCESSING_DURATION.time():
                metrics.BATCH_PROCESSING_SIZE.observe(len(batch_endpoints))
                
                # Create tasks for batch
                tasks = []
                for endpoint, param in zip(batch_endpoints, batch_params):
                    tasks.append(
                        asyncio.to_thread(self.get, endpoint, param)
                    )
                
                # Process batch with concurrency limit
                for response in asyncio.as_completed(tasks):
                    yield await response
        
        logger.info("Completed batch processing of %d endpoints", len(endpoints))
