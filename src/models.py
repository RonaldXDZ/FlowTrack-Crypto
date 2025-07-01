"""
Data Models Module

Defines dataclasses for all the data structures used in the analyzer
to provide type safety, validation, and easy serialization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import json


@dataclass
class KlineData:
    """Represents a single candlestick/K-line data point"""
    symbol: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    taker_buy_base_volume: float
    taker_buy_quote_volume: float
    net_inflow: float
    timestamp: int
    
    @classmethod
    def from_binance_data(cls, symbol: str, kline_data: List) -> 'KlineData':
        """Create KlineData from Binance API response"""
        return cls(
            symbol=symbol,
            open_time=datetime.fromtimestamp(kline_data[0] / 1000),
            close_time=datetime.fromtimestamp(kline_data[6] / 1000),
            open=float(kline_data[1]),
            high=float(kline_data[2]),
            low=float(kline_data[3]),
            close=float(kline_data[4]),
            volume=float(kline_data[5]),
            quote_volume=float(kline_data[7]),
            trades=int(kline_data[8]),
            taker_buy_base_volume=float(kline_data[9]),
            taker_buy_quote_volume=float(kline_data[10]),
            net_inflow=float(kline_data[10]) - (float(kline_data[7]) - float(kline_data[10])),
            timestamp=kline_data[0]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'quote_volume': self.quote_volume,
            'trades': self.trades,
            'taker_buy_base_volume': self.taker_buy_base_volume,
            'taker_buy_quote_volume': self.taker_buy_quote_volume,
            'net_inflow': self.net_inflow,
            'timestamp': self.timestamp
        }


@dataclass
class OrderBookStats:
    """Represents order book statistics and imbalances"""
    symbol: str
    price: float
    timestamp: datetime
    bids_count: int
    asks_count: int
    bids_volume: float
    asks_volume: float
    bids_value: float
    asks_value: float
    volume_imbalance: float
    value_imbalance: float
    near_volume_imbalance: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'bids_count': self.bids_count,
            'asks_count': self.asks_count,
            'bids_volume': self.bids_volume,
            'asks_volume': self.asks_volume,
            'bids_value': self.bids_value,
            'asks_value': self.asks_value,
            'volume_imbalance': self.volume_imbalance,
            'value_imbalance': self.value_imbalance,
            'near_volume_imbalance': self.near_volume_imbalance
        }


@dataclass
class TrendMetrics:
    """Represents statistical metrics for trend analysis"""
    price_trend: float
    price_trend_direction: str
    price_trend_strength: float
    price_trend_p_value: float
    inflow_trend: float
    inflow_trend_direction: str
    inflow_trend_strength: float
    inflow_trend_p_value: float
    correlation: float
    inflow_volume_correlation: float
    price_volatility: float
    recent_inflow_trend: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'price_trend': self.price_trend,
            'price_trend_direction': self.price_trend_direction,
            'price_trend_strength': self.price_trend_strength,
            'price_trend_p_value': self.price_trend_p_value,
            'inflow_trend': self.inflow_trend,
            'inflow_trend_direction': self.inflow_trend_direction,
            'inflow_trend_strength': self.inflow_trend_strength,
            'inflow_trend_p_value': self.inflow_trend_p_value,
            'correlation': self.correlation,
            'inflow_volume_correlation': self.inflow_volume_correlation,
            'price_volatility': self.price_volatility,
            'recent_inflow_trend': self.recent_inflow_trend
        }


@dataclass
class TrendAnalysis:
    """Represents the result of funding flow trend analysis"""
    symbol: str
    trend: str
    confidence: float
    description: str
    reasons: List[str]
    metrics: TrendMetrics
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'trend': self.trend,
            'confidence': self.confidence,
            'description': self.description,
            'reasons': self.reasons,
            'metrics': self.metrics.to_dict(),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Anomaly:
    """Represents a detected market anomaly"""
    timestamp: datetime
    type: str
    symbol: str
    volume: float
    price_change: float
    net_inflow: float
    severity: str = "medium"
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'type': self.type,
            'symbol': self.symbol,
            'volume': self.volume,
            'price_change': self.price_change,
            'net_inflow': self.net_inflow,
            'severity': self.severity,
            'additional_data': self.additional_data
        }


@dataclass
class PressureMetrics:
    """Represents funding pressure calculation metrics"""
    avg_inflow_ratio: float
    volume_imbalance: float
    value_imbalance: float
    near_volume_imbalance: float
    pressure_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'avg_inflow_ratio': self.avg_inflow_ratio,
            'volume_imbalance': self.volume_imbalance,
            'value_imbalance': self.value_imbalance,
            'near_volume_imbalance': self.near_volume_imbalance,
            'pressure_score': self.pressure_score
        }


@dataclass
class FundingPressure:
    """Represents funding pressure analysis results"""
    symbol: str
    pressure: str  # 'buying', 'selling', 'balanced'
    direction: str  # 'bullish', 'bearish', 'neutral'
    strength: float
    metrics: PressureMetrics
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'pressure': self.pressure,
            'direction': self.direction,
            'strength': self.strength,
            'metrics': self.metrics.to_dict(),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class CrossMarketMetrics:
    """Represents cross-market analysis metrics"""
    spot_total_inflow: float
    futures_total_inflow: float
    flow_difference: float
    correlation: Optional[float]
    dominant_market: str
    flow_ratio: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'spot_total_inflow': self.spot_total_inflow,
            'futures_total_inflow': self.futures_total_inflow,
            'flow_difference': self.flow_difference,
            'correlation': self.correlation,
            'dominant_market': self.dominant_market,
            'flow_ratio': self.flow_ratio
        }


@dataclass
class LeadLagAnalysis:
    """Represents lead-lag relationship analysis"""
    symbol: str
    max_correlation: float
    optimal_lag: int
    relationship: str
    all_correlations: List[tuple]  # (lag, correlation) pairs
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'max_correlation': self.max_correlation,
            'optimal_lag': self.optimal_lag,
            'relationship': self.relationship,
            'all_correlations': self.all_correlations,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MarketSummary:
    """Represents summary of market data for a symbol"""
    symbol: str
    market_type: str  # 'spot' or 'futures'
    count: int
    time_range: str
    latest_price: Optional[float]
    price_change_pct: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'market_type': self.market_type,
            'count': self.count,
            'time_range': self.time_range,
            'latest_price': self.latest_price,
            'price_change_pct': self.price_change_pct
        }


@dataclass
class AnalysisReport:
    """Comprehensive analysis report for all symbols"""
    timestamp: datetime
    symbols: List[str]
    spot_summaries: Dict[str, MarketSummary]
    futures_summaries: Dict[str, MarketSummary]
    spot_trends: Dict[str, TrendAnalysis]
    futures_trends: Dict[str, TrendAnalysis]
    spot_anomalies: Dict[str, List[Anomaly]]
    futures_anomalies: Dict[str, List[Anomaly]]
    spot_pressures: Dict[str, FundingPressure]
    futures_pressures: Dict[str, FundingPressure]
    spot_orderbooks: Dict[str, OrderBookStats]
    futures_orderbooks: Dict[str, OrderBookStats]
    cross_market_analysis: Dict[str, CrossMarketMetrics]
    lead_lag_analysis: Dict[str, LeadLagAnalysis]
    ai_analysis: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbols': self.symbols,
            'spot_summaries': {k: v.to_dict() for k, v in self.spot_summaries.items()},
            'futures_summaries': {k: v.to_dict() for k, v in self.futures_summaries.items()},
            'spot_trends': {k: v.to_dict() for k, v in self.spot_trends.items()},
            'futures_trends': {k: v.to_dict() for k, v in self.futures_trends.items()},
            'spot_anomalies': {k: [a.to_dict() for a in v] for k, v in self.spot_anomalies.items()},
            'futures_anomalies': {k: [a.to_dict() for a in v] for k, v in self.futures_anomalies.items()},
            'spot_pressures': {k: v.to_dict() for k, v in self.spot_pressures.items()},
            'futures_pressures': {k: v.to_dict() for k, v in self.futures_pressures.items()},
            'spot_orderbooks': {k: v.to_dict() for k, v in self.spot_orderbooks.items()},
            'futures_orderbooks': {k: v.to_dict() for k, v in self.futures_orderbooks.items()},
            'cross_market_analysis': {k: v.to_dict() for k, v in self.cross_market_analysis.items()},
            'lead_lag_analysis': {k: v.to_dict() for k, v in self.lead_lag_analysis.items()},
            'ai_analysis': self.ai_analysis
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_to_file(self, filepath: str) -> None:
        """Save report to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


# Utility functions for data conversion
def format_number(value: float) -> str:
    """Format numbers with K/M suffixes for readability"""
    if abs(value) >= 1000000:
        return f"{value / 1000000:.2f}M"
    elif abs(value) >= 1000:
        return f"{value / 1000:.2f}K"
    else:
        return f"{value:.2f}"


def create_market_summary(
    symbol: str, 
    market_type: str, 
    klines_data: List[KlineData]
) -> MarketSummary:
    """Create MarketSummary from klines data"""
    if not klines_data:
        return MarketSummary(
            symbol=symbol,
            market_type=market_type,
            count=0,
            time_range="No data",
            latest_price=None,
            price_change_pct=None
        )
    
    time_range = f"{klines_data[0].open_time.strftime('%Y-%m-%d %H:%M:%S')} to {klines_data[-1].close_time.strftime('%Y-%m-%d %H:%M:%S')}"
    latest_price = klines_data[-1].close
    price_change_pct = ((klines_data[-1].close - klines_data[0].open) / klines_data[0].open * 100) if klines_data else None
    
    return MarketSummary(
        symbol=symbol,
        market_type=market_type,
        count=len(klines_data),
        time_range=time_range,
        latest_price=latest_price,
        price_change_pct=price_change_pct
    )


# Type aliases for better code readability
KlinesData = List[KlineData]
AnomaliesList = List[Anomaly]
SymbolDataDict = Dict[str, Any]