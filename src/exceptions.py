"""
Custom Exception Classes

Defines specific exceptions for different types of errors in the
Binance Funding Flow Analyzer system.
"""

from typing import Optional, Dict, Any


class AnalyzerError(Exception):
    """Base exception class for all analyzer-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class APIError(AnalyzerError):
    """Exception raised for API-related errors"""
    
    def __init__(
        self, 
        message: str, 
        api_name: str = "", 
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        details = {
            "api_name": api_name,
            "status_code": status_code,
            "response_data": response_data
        }
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code
        self.response_data = response_data


class BinanceAPIError(APIError):
    """Specific exception for Binance API errors"""
    
    def __init__(
        self, 
        message: str, 
        endpoint: str = "",
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "Binance", status_code, response_data)
        self.endpoint = endpoint
        self.error_code = error_code
        if error_code:
            self.details["error_code"] = error_code
        if endpoint:
            self.details["endpoint"] = endpoint


class DeepSeekAPIError(APIError):
    """Specific exception for DeepSeek API errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "DeepSeek", status_code, response_data)
        self.error_type = error_type
        if error_type:
            self.details["error_type"] = error_type


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded"""
    
    def __init__(
        self, 
        message: str = "API rate limit exceeded",
        api_name: str = "",
        retry_after: Optional[int] = None
    ):
        super().__init__(message, api_name)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class DataError(AnalyzerError):
    """Exception raised for data-related errors"""
    
    def __init__(
        self, 
        message: str, 
        data_type: str = "",
        symbol: str = "",
        expected_format: Optional[str] = None
    ):
        details = {
            "data_type": data_type,
            "symbol": symbol,
            "expected_format": expected_format
        }
        super().__init__(message, details)
        self.data_type = data_type
        self.symbol = symbol
        self.expected_format = expected_format


class InsufficientDataError(DataError):
    """Exception raised when insufficient data is available for analysis"""
    
    def __init__(
        self, 
        message: str,
        symbol: str = "",
        required_points: int = 0,
        available_points: int = 0
    ):
        super().__init__(message, "insufficient_data", symbol)
        self.required_points = required_points
        self.available_points = available_points
        self.details.update({
            "required_points": required_points,
            "available_points": available_points
        })


class ValidationError(AnalyzerError):
    """Exception raised for configuration or input validation errors"""
    
    def __init__(
        self, 
        message: str,
        field_name: str = "",
        field_value: Any = None,
        validation_rule: str = ""
    ):
        details = {
            "field_name": field_name,
            "field_value": str(field_value),
            "validation_rule": validation_rule
        }
        super().__init__(message, details)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule


class AnalysisError(AnalyzerError):
    """Exception raised during statistical analysis operations"""
    
    def __init__(
        self, 
        message: str,
        analysis_type: str = "",
        symbol: str = "",
        calculation_step: str = ""
    ):
        details = {
            "analysis_type": analysis_type,
            "symbol": symbol,
            "calculation_step": calculation_step
        }
        super().__init__(message, details)
        self.analysis_type = analysis_type
        self.symbol = symbol
        self.calculation_step = calculation_step


class CacheError(AnalyzerError):
    """Exception raised for cache-related operations"""
    
    def __init__(
        self, 
        message: str,
        cache_key: str = "",
        operation: str = ""
    ):
        details = {
            "cache_key": cache_key,
            "operation": operation
        }
        super().__init__(message, details)
        self.cache_key = cache_key
        self.operation = operation


class ConnectionError(AnalyzerError):
    """Exception raised for network connectivity issues"""
    
    def __init__(
        self, 
        message: str,
        host: str = "",
        timeout: Optional[float] = None
    ):
        details = {
            "host": host,
            "timeout": timeout
        }
        super().__init__(message, details)
        self.host = host
        self.timeout = timeout


class AuthenticationError(APIError):
    """Exception raised for authentication failures"""
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        api_name: str = "",
        auth_type: str = ""
    ):
        super().__init__(message, api_name)
        self.auth_type = auth_type
        if auth_type:
            self.details["auth_type"] = auth_type


# Convenience functions for error handling
def handle_api_response(response, api_name: str = "Unknown") -> None:
    """
    Check API response and raise appropriate exceptions.
    
    Args:
        response: HTTP response object
        api_name: Name of the API for error context
        
    Raises:
        APIError: For various API-related errors
    """
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        raise RateLimitError(
            "API rate limit exceeded",
            api_name,
            int(retry_after) if retry_after else None
        )
    
    if response.status_code == 401:
        raise AuthenticationError(
            "API authentication failed",
            api_name,
            "api_key"
        )
    
    if response.status_code >= 400:
        try:
            error_data = response.json()
        except:
            error_data = {"error": response.text}
        
        raise APIError(
            f"{api_name} API error: {response.status_code}",
            api_name,
            response.status_code,
            error_data
        )


def validate_symbol_format(symbol: str) -> None:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading pair symbol to validate
        
    Raises:
        ValidationError: If symbol format is invalid
    """
    if not symbol:
        raise ValidationError(
            "Symbol cannot be empty",
            "symbol",
            symbol,
            "non_empty_string"
        )
    
    if not symbol.isupper():
        raise ValidationError(
            "Symbol must be uppercase",
            "symbol", 
            symbol,
            "uppercase_string"
        )
    
    if len(symbol) < 6:
        raise ValidationError(
            "Symbol must be at least 6 characters",
            "symbol",
            symbol,
            "min_length_6"
        )


def validate_data_sufficiency(
    data: list, 
    min_required: int, 
    symbol: str = "",
    data_type: str = "klines"
) -> None:
    """
    Validate that sufficient data is available for analysis.
    
    Args:
        data: Data list to validate
        min_required: Minimum required data points
        symbol: Trading symbol for context
        data_type: Type of data being validated
        
    Raises:
        InsufficientDataError: If insufficient data is available
    """
    if len(data) < min_required:
        raise InsufficientDataError(
            f"Insufficient {data_type} data for analysis",
            symbol,
            min_required,
            len(data)
        )