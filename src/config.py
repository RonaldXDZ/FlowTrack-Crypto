"""
Configuration Management Module

Centralized configuration system with environment variable support,
validation, and type safety.
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging


@dataclass
class APIConfig:
    """API configuration settings"""
    binance_api_key: str = ""
    binance_api_secret: str = ""
    deepseek_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # API endpoints
    binance_spot_url: str = "https://api.binance.com/api/v3"
    binance_futures_url: str = "https://fapi.binance.com/fapi/v1"
    deepseek_url: str = "https://api.deepseek.com/v1/chat/completions"
    
    # Rate limiting
    rate_limit_calls: int = 20
    rate_limit_period: int = 1
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass 
class AnalysisConfig:
    """Analysis parameters configuration"""
    default_interval: str = "5m"
    default_limit: int = 50
    min_data_points: int = 10
    
    # Analysis thresholds
    price_range_pct: float = 0.005  # 0.5% for near-price analysis
    anomaly_threshold: float = 2.0  # Standard deviations
    extreme_flow_threshold: float = 0.7  # 70% of volume
    
    # Pressure analysis weights
    inflow_weight: float = 0.4
    volume_imbalance_weight: float = 0.2
    value_imbalance_weight: float = 0.2
    near_imbalance_weight: float = 0.2
    
    # AI analysis settings
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.7


@dataclass
class SystemConfig:
    """System and logging configuration"""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File paths
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    cache_dir: Path = field(default_factory=lambda: Path("./cache"))
    logs_dir: Path = field(default_factory=lambda: Path("./logs"))
    
    # Cache settings
    cache_enabled: bool = True
    cache_duration_minutes: int = 5
    
    # Concurrency
    max_workers: int = 3
    enable_parallel_processing: bool = True


@dataclass
class TradingConfig:
    """Trading pairs and market configuration"""
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    enable_spot: bool = True
    enable_futures: bool = True
    
    # Order book settings
    spot_orderbook_limit: int = 5000
    futures_orderbook_limit: int = 1000


class Config:
    """Main configuration class that aggregates all config sections"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration from environment variables and config file.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.api = APIConfig()
        self.analysis = AnalysisConfig()
        self.system = SystemConfig()
        self.trading = TradingConfig()
        
        # Load from environment variables
        self._load_from_env()
        
        # Load from config file if provided
        if config_file:
            self._load_from_file(config_file)
            
        # Validate configuration
        self._validate()
        
        # Setup logging
        self._setup_logging()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        # API configuration
        self.api.binance_api_key = os.getenv("BINANCE_API_KEY", "")
        self.api.binance_api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.api.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.api.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.api.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # System configuration
        self.system.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.system.output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
        self.system.cache_dir = Path(os.getenv("CACHE_DIR", "./cache"))
        self.system.logs_dir = Path(os.getenv("LOGS_DIR", "./logs"))
        
        # Trading configuration
        symbols_env = os.getenv("TRADING_SYMBOLS")
        if symbols_env:
            self.trading.symbols = [s.strip() for s in symbols_env.split(",")]
        
        # Analysis configuration
        interval = os.getenv("DEFAULT_INTERVAL")
        if interval:
            self.analysis.default_interval = interval
            
        limit = os.getenv("DEFAULT_LIMIT")
        if limit and limit.isdigit():
            self.analysis.default_limit = int(limit)
    
    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file (JSON/YAML)"""
        # Implementation for file-based configuration
        # This can be extended to support JSON, YAML, etc.
        pass
    
    def _validate(self) -> None:
        """Validate configuration settings"""
        errors = []
        
        # Validate required API keys
        if not self.api.binance_api_key and not self._is_test_mode():
            errors.append("BINANCE_API_KEY is required")
        
        if not self.api.binance_api_secret and not self._is_test_mode():
            errors.append("BINANCE_API_SECRET is required")
        
        # Validate trading symbols
        if not self.trading.symbols:
            errors.append("At least one trading symbol must be configured")
        
        # Validate analysis parameters
        if self.analysis.default_limit < self.analysis.min_data_points:
            errors.append(f"Default limit ({self.analysis.default_limit}) must be >= min_data_points ({self.analysis.min_data_points})")
        
        # Validate weights sum to 1.0
        total_weight = (
            self.analysis.inflow_weight + 
            self.analysis.volume_imbalance_weight + 
            self.analysis.value_imbalance_weight + 
            self.analysis.near_imbalance_weight
        )
        if abs(total_weight - 1.0) > 0.001:
            errors.append(f"Analysis weights must sum to 1.0, got {total_weight}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        # Ensure logs directory exists
        self.system.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_level = getattr(logging, self.system.log_level.upper())
        logging.basicConfig(
            level=log_level,
            format=self.system.log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    self.system.logs_dir / "analyzer.log",
                    mode='a'
                )
            ]
        )
    
    def _is_test_mode(self) -> bool:
        """Check if running in test mode"""
        return os.getenv("ANALYZER_TEST_MODE", "").lower() == "true"
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        for directory in [self.system.output_dir, self.system.cache_dir, self.system.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for serialization)"""
        return {
            "api": {
                "binance_spot_url": self.api.binance_spot_url,
                "binance_futures_url": self.api.binance_futures_url,
                "deepseek_url": self.api.deepseek_url,
                "rate_limit_calls": self.api.rate_limit_calls,
                "rate_limit_period": self.api.rate_limit_period,
                "retry_attempts": self.api.retry_attempts,
                "retry_delay": self.api.retry_delay,
            },
            "analysis": {
                "default_interval": self.analysis.default_interval,
                "default_limit": self.analysis.default_limit,
                "min_data_points": self.analysis.min_data_points,
                "price_range_pct": self.analysis.price_range_pct,
                "anomaly_threshold": self.analysis.anomaly_threshold,
                "extreme_flow_threshold": self.analysis.extreme_flow_threshold,
            },
            "trading": {
                "symbols": self.trading.symbols,
                "enable_spot": self.trading.enable_spot,
                "enable_futures": self.trading.enable_futures,
                "spot_orderbook_limit": self.trading.spot_orderbook_limit,
                "futures_orderbook_limit": self.trading.futures_orderbook_limit,
            },
            "system": {
                "log_level": self.system.log_level,
                "cache_enabled": self.system.cache_enabled,
                "cache_duration_minutes": self.system.cache_duration_minutes,
                "max_workers": self.system.max_workers,
                "enable_parallel_processing": self.system.enable_parallel_processing,
            }
        }
    
    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"Config(symbols={self.trading.symbols}, interval={self.analysis.default_interval})"


# Global configuration instance
config = Config()