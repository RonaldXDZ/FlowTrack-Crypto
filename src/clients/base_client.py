"""
Base API Client

Provides common functionality for all API clients including rate limiting,
retry logic, error handling, and logging.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from functools import wraps
import requests
from ratelimit import limits, sleep_and_retry

from ..config import Config
from ..exceptions import APIError, RateLimitError, ConnectionError as AnalyzerConnectionError


class BaseAPIClient(ABC):
    """Abstract base class for all API clients"""
    
    def __init__(self, config: Config, name: str = "Unknown"):
        """
        Initialize base API client.
        
        Args:
            config: Configuration object
            name: Name of the API for logging and error handling
        """
        self.config = config
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.session = requests.Session()
        
        # Setup default headers
        self.session.headers.update({
            'User-Agent': f'Binance-Funding-Flow-Analyzer/2.0.0',
            'Content-Type': 'application/json'
        })
    
    def rate_limited_request(
        self, 
        calls: int = None, 
        period: int = None
    ) -> Callable:
        """
        Decorator for rate limiting API calls.
        
        Args:
            calls: Number of calls allowed per period
            period: Time period in seconds
            
        Returns:
            Decorated function with rate limiting
        """
        calls = calls or self.config.api.rate_limit_calls
        period = period or self.config.api.rate_limit_period
        
        def decorator(func):
            @sleep_and_retry
            @limits(calls=calls, period=period)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
        retries: int = None
    ) -> requests.Response:
        """
        Make HTTP request with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Additional headers
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            
        Returns:
            HTTP response object
            
        Raises:
            APIError: For various API-related errors
            RateLimitError: When rate limits are exceeded
            ConnectionError: For network connectivity issues
        """
        retries = retries or self.config.api.retry_attempts
        headers = headers or {}
        
        # Merge with session headers
        request_headers = {**self.session.headers, **headers}
        
        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                self.logger.debug(
                    f"Making {method} request to {url} (attempt {attempt + 1}/{retries + 1})"
                )
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data if method in ['POST', 'PUT', 'PATCH'] else None,
                    headers=request_headers,
                    timeout=timeout
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    retry_after = int(retry_after) if retry_after else self.config.api.retry_delay
                    
                    if attempt < retries:
                        self.logger.warning(
                            f"Rate limit hit for {self.name} API, retrying after {retry_after}s"
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        raise RateLimitError(
                            f"{self.name} API rate limit exceeded",
                            self.name,
                            retry_after
                        )
                
                # Handle other HTTP errors
                if response.status_code >= 400:
                    error_data = None
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"error": response.text}
                    
                    if attempt < retries and response.status_code >= 500:
                        # Retry on server errors
                        self.logger.warning(
                            f"Server error {response.status_code} for {self.name} API, retrying..."
                        )
                        time.sleep(self.config.api.retry_delay * (attempt + 1))
                        continue
                    
                    raise APIError(
                        f"{self.name} API error: {response.status_code}",
                        self.name,
                        response.status_code,
                        error_data
                    )
                
                # Success
                self.logger.debug(f"Request successful: {response.status_code}")
                return response
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < retries:
                    self.logger.warning(f"Request timeout, retrying... (attempt {attempt + 1})")
                    time.sleep(self.config.api.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < retries:
                    self.logger.warning(f"Connection error, retrying... (attempt {attempt + 1})")
                    time.sleep(self.config.api.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < retries:
                    self.logger.warning(f"Request error, retrying... (attempt {attempt + 1})")
                    time.sleep(self.config.api.retry_delay * (attempt + 1))
                    continue
        
        # If we get here, all retries failed
        if isinstance(last_exception, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
            raise AnalyzerConnectionError(
                f"Failed to connect to {self.name} API after {retries + 1} attempts",
                url,
                timeout
            )
        else:
            raise APIError(
                f"{self.name} API request failed after {retries + 1} attempts: {str(last_exception)}",
                self.name
            )
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make GET request"""
        return self.make_request('GET', url, params=params, **kwargs)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make POST request"""
        return self.make_request('POST', url, data=data, **kwargs)
    
    def put(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Make PUT request"""
        return self.make_request('PUT', url, data=data, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make DELETE request"""
        return self.make_request('DELETE', url, **kwargs)
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get API information and status.
        
        Returns:
            Dictionary containing API information
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def close(self):
        """Close the API client and cleanup resources"""
        self.session.close()
        self.logger.debug(f"Closed {self.name} API client")
    
    def __repr__(self) -> str:
        """String representation of the client"""
        return f"{self.__class__.__name__}(name='{self.name}')"


class RateLimitedMixin:
    """Mixin class to add rate limiting to specific methods"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_rate_limiting()
    
    def _setup_rate_limiting(self):
        """Setup rate limiting for specific methods"""
        # This can be overridden by subclasses to apply rate limiting
        # to specific methods
        pass


class CachedMixin:
    """Mixin class to add caching capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
        self._cache_ttl = {}
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key for method call"""
        key_parts = [method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)
    
    def _is_cache_valid(self, key: str, ttl_seconds: int = 300) -> bool:
        """Check if cached data is still valid"""
        if key not in self._cache:
            return False
        
        if key not in self._cache_ttl:
            return False
        
        return time.time() - self._cache_ttl[key] < ttl_seconds
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache value with timestamp"""
        self._cache[key] = value
        self._cache_ttl[key] = time.time()
    
    def _get_cache(self, key: str) -> Any:
        """Get cached value"""
        return self._cache.get(key)
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
        self._cache_ttl.clear()
        self.logger.debug("Cache cleared")