"""
Binance API Client

Provides methods for interacting with Binance spot and futures APIs
with proper rate limiting, error handling, and data transformation.
"""

import hmac
import hashlib
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

from .base_client import BaseAPIClient, CachedMixin
from ..config import Config
from ..models import KlineData, OrderBookStats
from ..exceptions import BinanceAPIError, InsufficientDataError, validate_symbol_format, validate_data_sufficiency


class BinanceClient(CachedMixin, BaseAPIClient):
    """Enhanced Binance API client with caching and error handling"""
    
    def __init__(self, config: Config):
        """
        Initialize Binance client.
        
        Args:
            config: Configuration object containing API credentials
        """
        super().__init__(config, "Binance")
        
        # Initialize official Binance client
        self.client = Client(
            api_key=config.api.binance_api_key,
            api_secret=config.api.binance_api_secret,
            testnet=False  # Use mainnet
        )
        
        self.spot_url = config.api.binance_spot_url
        self.futures_url = config.api.binance_futures_url
    
    def test_connection(self) -> bool:
        """
        Test Binance API connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test spot API
            self.client.ping()
            
            # Test futures API  
            self.client.futures_ping()
            
            # Test authentication
            account_info = self.client.get_account()
            self.logger.info("Binance API connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Binance API connection test failed: {e}")
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get Binance API information and status.
        
        Returns:
            Dictionary containing API information
        """
        try:
            # Get exchange info
            spot_info = self.client.get_exchange_info()
            futures_info = self.client.futures_exchange_info()
            
            # Get server time
            server_time = self.client.get_server_time()
            
            return {
                "name": "Binance",
                "spot_symbols_count": len(spot_info['symbols']),
                "futures_symbols_count": len(futures_info['symbols']),
                "server_time": server_time['serverTime'],
                "rate_limits": {
                    "spot": spot_info.get('rateLimits', []),
                    "futures": futures_info.get('rateLimits', [])
                },
                "status": "operational"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get Binance API info: {e}")
            return {"name": "Binance", "status": "error", "error": str(e)}
    
    def get_klines_data(
        self, 
        symbol: str, 
        interval: str = None, 
        limit: int = None, 
        is_futures: bool = False,
        use_cache: bool = True
    ) -> List[KlineData]:
        """
        Get K-line data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (5m, 1h, etc.)
            limit: Number of klines to retrieve
            is_futures: Whether to use futures API
            use_cache: Whether to use cached data
            
        Returns:
            List of KlineData objects
            
        Raises:
            BinanceAPIError: For API-related errors
            InsufficientDataError: When insufficient data is available
            ValidationError: For invalid input parameters
        """
        # Validate inputs
        validate_symbol_format(symbol)
        
        interval = interval or self.config.analysis.default_interval
        limit = limit or self.config.analysis.default_limit
        
        # Check cache if enabled
        cache_key = self._get_cache_key("klines", symbol, interval, limit, is_futures)
        if use_cache and self.config.system.cache_enabled:
            if self._is_cache_valid(cache_key, self.config.system.cache_duration_minutes * 60):
                cached_data = self._get_cache(cache_key)
                if cached_data:
                    self.logger.debug(f"Using cached klines data for {symbol}")
                    return cached_data
        
        try:
            self.logger.debug(f"Fetching {symbol} {'futures' if is_futures else 'spot'} klines: {interval}, limit={limit}")
            
            if is_futures:
                raw_klines = self.client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit + 1  # Get one extra to remove incomplete candle
                )
            else:
                raw_klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit + 1  # Get one extra to remove incomplete candle
                )
            
            # Remove the last (incomplete) kline
            if raw_klines:
                raw_klines = raw_klines[:-1]
            
            # Validate data sufficiency
            validate_data_sufficiency(
                raw_klines, 
                self.config.analysis.min_data_points, 
                symbol, 
                "klines"
            )
            
            # Convert to KlineData objects
            klines_data = [
                KlineData.from_binance_data(symbol, kline) 
                for kline in raw_klines
            ]
            
            # Cache the data
            if use_cache and self.config.system.cache_enabled:
                self._set_cache(cache_key, klines_data)
            
            self.logger.debug(f"Retrieved {len(klines_data)} klines for {symbol}")
            return klines_data
            
        except BinanceAPIException as e:
            raise BinanceAPIError(
                f"Binance API error for {symbol} klines",
                endpoint="/klines",
                status_code=e.status_code,
                error_code=str(e.code),
                response_data={"message": e.message}
            )
            
        except Exception as e:
            raise BinanceAPIError(
                f"Unexpected error fetching {symbol} klines: {str(e)}",
                endpoint="/klines"
            )
    
    def get_orderbook_stats(
        self, 
        symbol: str, 
        is_futures: bool = False,
        use_cache: bool = True
    ) -> Optional[OrderBookStats]:
        """
        Get order book statistics for a symbol.
        
        Args:
            symbol: Trading pair symbol
            is_futures: Whether to use futures API
            use_cache: Whether to use cached data
            
        Returns:
            OrderBookStats object or None if failed
            
        Raises:
            BinanceAPIError: For API-related errors
            ValidationError: For invalid input parameters
        """
        # Validate inputs
        validate_symbol_format(symbol)
        
        # Check cache if enabled
        cache_key = self._get_cache_key("orderbook", symbol, is_futures)
        if use_cache and self.config.system.cache_enabled:
            # Use shorter cache time for orderbook data (1 minute)
            if self._is_cache_valid(cache_key, 60):
                cached_data = self._get_cache(cache_key)
                if cached_data:
                    self.logger.debug(f"Using cached orderbook data for {symbol}")
                    return cached_data
        
        limit = (
            self.config.trading.futures_orderbook_limit 
            if is_futures 
            else self.config.trading.spot_orderbook_limit
        )
        
        try:
            self.logger.debug(f"Fetching {symbol} {'futures' if is_futures else 'spot'} orderbook")
            
            # Get order book data
            if is_futures:
                orderbook = self.client.futures_order_book(symbol=symbol, limit=limit)
                ticker_data = self.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker_data['price'])
            else:
                orderbook = self.client.get_order_book(symbol=symbol, limit=limit)
                ticker_data = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker_data['price'])
            
            # Parse order book data
            bids = [(float(bid[0]), float(bid[1])) for bid in orderbook['bids']]
            asks = [(float(ask[0]), float(ask[1])) for ask in orderbook['asks']]
            
            # Calculate statistics
            bids_volume = sum(amount for _, amount in bids)
            asks_volume = sum(amount for _, amount in asks)
            bids_value = sum(price * amount for price, amount in bids)
            asks_value = sum(price * amount for price, amount in asks)
            
            # Calculate imbalances
            total_volume = bids_volume + asks_volume
            total_value = bids_value + asks_value
            
            volume_imbalance = (bids_volume - asks_volume) / total_volume if total_volume > 0 else 0
            value_imbalance = (bids_value - asks_value) / total_value if total_value > 0 else 0
            
            # Calculate near-price imbalance (within configured percentage)
            price_range_pct = self.config.analysis.price_range_pct
            lower_bound = current_price * (1 - price_range_pct)
            upper_bound = current_price * (1 + price_range_pct)
            
            near_bids_volume = sum(amount for price, amount in bids if price >= lower_bound)
            near_asks_volume = sum(amount for price, amount in asks if price <= upper_bound)
            near_total_volume = near_bids_volume + near_asks_volume
            
            near_volume_imbalance = (
                (near_bids_volume - near_asks_volume) / near_total_volume 
                if near_total_volume > 0 else 0
            )
            
            # Create OrderBookStats object
            stats = OrderBookStats(
                symbol=symbol,
                price=current_price,
                timestamp=datetime.now(),
                bids_count=len(bids),
                asks_count=len(asks),
                bids_volume=bids_volume,
                asks_volume=asks_volume,
                bids_value=bids_value,
                asks_value=asks_value,
                volume_imbalance=volume_imbalance,
                value_imbalance=value_imbalance,
                near_volume_imbalance=near_volume_imbalance
            )
            
            # Cache the data
            if use_cache and self.config.system.cache_enabled:
                self._set_cache(cache_key, stats)
            
            self.logger.debug(f"Retrieved orderbook stats for {symbol}")
            return stats
            
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error for {symbol} orderbook: {e}")
            raise BinanceAPIError(
                f"Binance API error for {symbol} orderbook",
                endpoint="/depth",
                status_code=e.status_code,
                error_code=str(e.code),
                response_data={"message": e.message}
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {symbol} orderbook: {e}")
            return None
    
    def get_symbol_info(self, symbol: str, is_futures: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get symbol information and trading rules.
        
        Args:
            symbol: Trading pair symbol
            is_futures: Whether to use futures API
            
        Returns:
            Dictionary containing symbol information
        """
        try:
            if is_futures:
                exchange_info = self.client.futures_exchange_info()
            else:
                exchange_info = self.client.get_exchange_info()
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return None
    
    def get_available_symbols(self, is_futures: bool = False) -> List[str]:
        """
        Get list of available trading symbols.
        
        Args:
            is_futures: Whether to get futures symbols
            
        Returns:
            List of available symbol names
        """
        try:
            if is_futures:
                exchange_info = self.client.futures_exchange_info()
            else:
                exchange_info = self.client.get_exchange_info()
            
            symbols = [
                symbol_info['symbol'] 
                for symbol_info in exchange_info['symbols']
                if symbol_info['status'] == 'TRADING'
            ]
            
            return symbols
            
        except Exception as e:
            self.logger.error(f"Failed to get available symbols: {e}")
            return []
    
    def get_24hr_ticker(self, symbol: str, is_futures: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get 24hr ticker price change statistics.
        
        Args:
            symbol: Trading pair symbol
            is_futures: Whether to use futures API
            
        Returns:
            Dictionary containing 24hr ticker data
        """
        try:
            if is_futures:
                ticker = self.client.futures_ticker(symbol=symbol)
            else:
                ticker = self.client.get_ticker(symbol=symbol)
            
            return ticker
            
        except Exception as e:
            self.logger.error(f"Failed to get 24hr ticker for {symbol}: {e}")
            return None
    
    def batch_get_klines(
        self, 
        symbols: List[str], 
        interval: str = None, 
        limit: int = None, 
        is_futures: bool = False
    ) -> Dict[str, List[KlineData]]:
        """
        Get K-line data for multiple symbols efficiently.
        
        Args:
            symbols: List of trading pair symbols
            interval: Time interval
            limit: Number of klines to retrieve
            is_futures: Whether to use futures API
            
        Returns:
            Dictionary mapping symbols to their KlineData lists
        """
        results = {}
        
        for symbol in symbols:
            try:
                klines = self.get_klines_data(
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                    is_futures=is_futures
                )
                results[symbol] = klines
                
            except Exception as e:
                self.logger.error(f"Failed to get klines for {symbol}: {e}")
                results[symbol] = []
        
        return results
    
    def batch_get_orderbooks(
        self, 
        symbols: List[str], 
        is_futures: bool = False
    ) -> Dict[str, Optional[OrderBookStats]]:
        """
        Get order book statistics for multiple symbols efficiently.
        
        Args:
            symbols: List of trading pair symbols
            is_futures: Whether to use futures API
            
        Returns:
            Dictionary mapping symbols to their OrderBookStats
        """
        results = {}
        
        for symbol in symbols:
            try:
                stats = self.get_orderbook_stats(
                    symbol=symbol,
                    is_futures=is_futures
                )
                results[symbol] = stats
                
            except Exception as e:
                self.logger.error(f"Failed to get orderbook for {symbol}: {e}")
                results[symbol] = None
        
        return results