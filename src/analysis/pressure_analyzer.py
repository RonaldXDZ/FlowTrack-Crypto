"""
Funding Pressure Analysis Engine

Combines historical capital flow data with current order book depth
to assess market pressure and directional bias.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..config import Config
from ..models import KlineData, OrderBookStats, FundingPressure, PressureMetrics
from ..exceptions import AnalysisError, InsufficientDataError


class PressureAnalyzer:
    """Advanced funding pressure analysis engine"""
    
    def __init__(self, config: Config):
        """
        Initialize pressure analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def analyze_funding_pressure(
        self, 
        klines_data: List[KlineData], 
        orderbook: OrderBookStats
    ) -> FundingPressure:
        """
        Analyze funding pressure combining historical data and current order book.
        
        Args:
            klines_data: Historical K-line data
            orderbook: Current order book statistics
            
        Returns:
            FundingPressure analysis result
            
        Raises:
            InsufficientDataError: When insufficient data is available
            AnalysisError: For calculation errors
        """
        if not klines_data or not orderbook:
            raise InsufficientDataError(
                "Insufficient data for pressure analysis",
                klines_data[0].symbol if klines_data else "",
                required_points=1,
                available_points=len(klines_data) if klines_data else 0
            )
        
        symbol = klines_data[0].symbol
        
        try:
            self.logger.debug(f"Starting pressure analysis for {symbol}")
            
            # Calculate pressure metrics
            metrics = self._calculate_pressure_metrics(klines_data, orderbook)
            
            # Determine pressure characteristics
            pressure, direction, strength = self._determine_pressure_characteristics(metrics)
            
            # Create result
            result = FundingPressure(
                symbol=symbol,
                pressure=pressure,
                direction=direction,
                strength=strength,
                metrics=metrics,
                timestamp=datetime.now()
            )
            
            self.logger.debug(
                f"Pressure analysis completed for {symbol}: {pressure} "
                f"({direction}, strength: {strength:.2f})"
            )
            
            return result
            
        except Exception as e:
            raise AnalysisError(
                f"Pressure analysis failed for {symbol}",
                "pressure_analysis",
                symbol,
                str(e)
            )
    
    def _calculate_pressure_metrics(
        self, 
        klines_data: List[KlineData], 
        orderbook: OrderBookStats
    ) -> PressureMetrics:
        """
        Calculate comprehensive pressure metrics.
        
        Args:
            klines_data: Historical K-line data
            orderbook: Order book statistics
            
        Returns:
            PressureMetrics object with all calculated metrics
        """
        # Sort data by timestamp
        sorted_data = sorted(klines_data, key=lambda x: x.timestamp)
        
        # Extract recent capital flow data (last 10 periods)
        recent_data = sorted_data[-10:] if len(sorted_data) >= 10 else sorted_data
        
        # Calculate average inflow ratio
        inflow_ratios = []
        for kline in recent_data:
            if kline.quote_volume > 0:
                ratio = kline.net_inflow / kline.quote_volume
                inflow_ratios.append(ratio)
        
        avg_inflow_ratio = np.mean(inflow_ratios) if inflow_ratios else 0.0
        
        # Get order book metrics
        volume_imbalance = orderbook.volume_imbalance
        value_imbalance = orderbook.value_imbalance
        near_volume_imbalance = orderbook.near_volume_imbalance
        
        # Calculate composite pressure score using configured weights
        pressure_score = (
            avg_inflow_ratio * self.config.analysis.inflow_weight +
            volume_imbalance * self.config.analysis.volume_imbalance_weight +
            value_imbalance * self.config.analysis.value_imbalance_weight +
            near_volume_imbalance * self.config.analysis.near_imbalance_weight
        )
        
        return PressureMetrics(
            avg_inflow_ratio=avg_inflow_ratio,
            volume_imbalance=volume_imbalance,
            value_imbalance=value_imbalance,
            near_volume_imbalance=near_volume_imbalance,
            pressure_score=pressure_score
        )
    
    def _determine_pressure_characteristics(
        self, 
        metrics: PressureMetrics
    ) -> tuple[str, str, float]:
        """
        Determine pressure type, direction, and strength.
        
        Args:
            metrics: Calculated pressure metrics
            
        Returns:
            Tuple of (pressure_type, direction, strength)
        """
        pressure_score = metrics.pressure_score
        
        # Determine pressure type and direction
        if pressure_score > 0.1:
            pressure = 'buying'
            direction = 'bullish'
            strength = min(pressure_score * 5, 1.0)
        elif pressure_score < -0.1:
            pressure = 'selling'
            direction = 'bearish' 
            strength = min(abs(pressure_score) * 5, 1.0)
        else:
            pressure = 'balanced'
            direction = 'neutral'
            strength = abs(pressure_score) * 5
        
        return pressure, direction, strength
    
    def analyze_pressure_evolution(
        self, 
        historical_pressures: List[FundingPressure]
    ) -> Dict[str, Any]:
        """
        Analyze how funding pressure has evolved over time.
        
        Args:
            historical_pressures: List of historical pressure analyses
            
        Returns:
            Dictionary containing pressure evolution analysis
        """
        if not historical_pressures:
            return {'error': 'No historical pressure data provided'}
        
        try:
            # Sort by timestamp
            sorted_pressures = sorted(historical_pressures, key=lambda x: x.timestamp)
            
            # Extract time series data
            timestamps = [p.timestamp for p in sorted_pressures]
            pressure_scores = [p.metrics.pressure_score for p in sorted_pressures]
            strengths = [p.strength for p in sorted_pressures]
            
            # Calculate trend
            if len(pressure_scores) > 1:
                x = np.arange(len(pressure_scores))
                slope = np.polyfit(x, pressure_scores, 1)[0]
                
                if slope > 0.01:
                    trend = 'increasing_pressure'
                elif slope < -0.01:
                    trend = 'decreasing_pressure'
                else:
                    trend = 'stable_pressure'
            else:
                trend = 'insufficient_data'
                slope = 0
            
            # Calculate volatility
            score_volatility = np.std(pressure_scores) if len(pressure_scores) > 1 else 0
            
            # Identify pressure regime changes
            regime_changes = []
            for i in range(1, len(sorted_pressures)):
                prev_pressure = sorted_pressures[i-1]
                curr_pressure = sorted_pressures[i]
                
                if prev_pressure.pressure != curr_pressure.pressure:
                    regime_changes.append({
                        'timestamp': curr_pressure.timestamp.isoformat(),
                        'from': prev_pressure.pressure,
                        'to': curr_pressure.pressure,
                        'strength_change': curr_pressure.strength - prev_pressure.strength
                    })
            
            # Calculate persistence metrics
            pressure_types = [p.pressure for p in sorted_pressures]
            buying_periods = sum(1 for p in pressure_types if p == 'buying')
            selling_periods = sum(1 for p in pressure_types if p == 'selling')
            balanced_periods = sum(1 for p in pressure_types if p == 'balanced')
            
            total_periods = len(pressure_types)
            persistence = {
                'buying_ratio': buying_periods / total_periods,
                'selling_ratio': selling_periods / total_periods,
                'balanced_ratio': balanced_periods / total_periods,
                'dominant_pressure': max(
                    [('buying', buying_periods), ('selling', selling_periods), ('balanced', balanced_periods)],
                    key=lambda x: x[1]
                )[0]
            }
            
            return {
                'trend': trend,
                'slope': slope,
                'volatility': score_volatility,
                'regime_changes': regime_changes,
                'persistence': persistence,
                'latest_pressure': sorted_pressures[-1].pressure,
                'latest_strength': sorted_pressures[-1].strength,
                'analysis_period': {
                    'start': timestamps[0].isoformat(),
                    'end': timestamps[-1].isoformat(),
                    'total_periods': total_periods
                }
            }
            
        except Exception as e:
            self.logger.error(f"Pressure evolution analysis failed: {e}")
            return {'error': str(e)}
    
    def compare_pressure_across_symbols(
        self, 
        symbol_pressures: Dict[str, FundingPressure]
    ) -> Dict[str, Any]:
        """
        Compare funding pressure across multiple symbols.
        
        Args:
            symbol_pressures: Dictionary mapping symbols to their pressure analysis
            
        Returns:
            Dictionary containing cross-symbol pressure comparison
        """
        if not symbol_pressures:
            return {'error': 'No pressure data provided'}
        
        try:
            # Extract pressure data
            symbols = list(symbol_pressures.keys())
            pressures = [p.pressure for p in symbol_pressures.values()]
            strengths = [p.strength for p in symbol_pressures.values()]
            scores = [p.metrics.pressure_score for p in symbol_pressures.values()]
            
            # Count pressure types
            pressure_counts = {}
            for pressure in pressures:
                pressure_counts[pressure] = pressure_counts.get(pressure, 0) + 1
            
            # Find strongest and weakest pressure
            strength_data = [(symbol, symbol_pressures[symbol].strength) for symbol in symbols]
            strongest = max(strength_data, key=lambda x: x[1])
            weakest = min(strength_data, key=lambda x: x[1])
            
            # Identify symbols by pressure type
            by_pressure_type = {}
            for symbol, pressure_obj in symbol_pressures.items():
                pressure_type = pressure_obj.pressure
                if pressure_type not in by_pressure_type:
                    by_pressure_type[pressure_type] = []
                by_pressure_type[pressure_type].append({
                    'symbol': symbol,
                    'strength': pressure_obj.strength,
                    'score': pressure_obj.metrics.pressure_score
                })
            
            # Sort each pressure type by strength
            for pressure_type in by_pressure_type:
                by_pressure_type[pressure_type].sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate correlation between symbols (if multiple symbols)
            correlation_matrix = {}
            if len(symbols) > 1:
                for i, symbol1 in enumerate(symbols):
                    correlation_matrix[symbol1] = {}
                    for j, symbol2 in enumerate(symbols):
                        if i != j:
                            # Simple correlation based on pressure scores
                            score1 = symbol_pressures[symbol1].metrics.pressure_score
                            score2 = symbol_pressures[symbol2].metrics.pressure_score
                            
                            # Simplified correlation (would need historical data for proper correlation)
                            correlation_matrix[symbol1][symbol2] = np.sign(score1) == np.sign(score2)
            
            # Market sentiment summary
            total_symbols = len(symbols)
            bullish_count = sum(1 for p in symbol_pressures.values() if p.direction == 'bullish')
            bearish_count = sum(1 for p in symbol_pressures.values() if p.direction == 'bearish')
            neutral_count = sum(1 for p in symbol_pressures.values() if p.direction == 'neutral')
            
            if bullish_count > bearish_count and bullish_count > neutral_count:
                market_sentiment = 'bullish'
            elif bearish_count > bullish_count and bearish_count > neutral_count:
                market_sentiment = 'bearish'
            else:
                market_sentiment = 'mixed'
            
            return {
                'pressure_distribution': pressure_counts,
                'market_sentiment': market_sentiment,
                'sentiment_breakdown': {
                    'bullish': bullish_count / total_symbols,
                    'bearish': bearish_count / total_symbols,
                    'neutral': neutral_count / total_symbols
                },
                'strongest_pressure': {
                    'symbol': strongest[0],
                    'strength': strongest[1],
                    'pressure': symbol_pressures[strongest[0]].pressure
                },
                'weakest_pressure': {
                    'symbol': weakest[0],
                    'strength': weakest[1],
                    'pressure': symbol_pressures[weakest[0]].pressure
                },
                'by_pressure_type': by_pressure_type,
                'correlation_hints': correlation_matrix,
                'average_strength': np.mean(strengths),
                'pressure_variance': np.var(scores),
                'total_symbols': total_symbols
            }
            
        except Exception as e:
            self.logger.error(f"Cross-symbol pressure comparison failed: {e}")
            return {'error': str(e)}
    
    def detect_pressure_divergence(
        self, 
        price_data: List[float], 
        pressure_data: List[float]
    ) -> Dict[str, Any]:
        """
        Detect divergence between price movement and funding pressure.
        
        Args:
            price_data: List of price values
            pressure_data: List of pressure scores
            
        Returns:
            Dictionary containing divergence analysis
        """
        if len(price_data) != len(pressure_data) or len(price_data) < 3:
            return {'error': 'Insufficient or mismatched data for divergence analysis'}
        
        try:
            # Calculate price and pressure trends
            x = np.arange(len(price_data))
            price_slope = np.polyfit(x, price_data, 1)[0]
            pressure_slope = np.polyfit(x, pressure_data, 1)[0]
            
            # Normalize slopes for comparison
            price_direction = np.sign(price_slope)
            pressure_direction = np.sign(pressure_slope)
            
            # Detect divergence
            divergence_detected = False
            divergence_type = None
            
            if price_direction != pressure_direction and abs(price_slope) > 0.01 and abs(pressure_slope) > 0.01:
                divergence_detected = True
                
                if price_direction > 0 and pressure_direction < 0:
                    divergence_type = 'bearish_divergence'  # Price up, pressure down
                elif price_direction < 0 and pressure_direction > 0:
                    divergence_type = 'bullish_divergence'  # Price down, pressure up
            
            # Calculate correlation
            correlation = np.corrcoef(price_data, pressure_data)[0, 1] if len(price_data) > 1 else 0
            
            return {
                'divergence_detected': divergence_detected,
                'divergence_type': divergence_type,
                'price_trend': 'up' if price_slope > 0 else 'down' if price_slope < 0 else 'flat',
                'pressure_trend': 'up' if pressure_slope > 0 else 'down' if pressure_slope < 0 else 'flat',
                'correlation': correlation,
                'price_slope': price_slope,
                'pressure_slope': pressure_slope,
                'strength': abs(price_slope - pressure_slope) if divergence_detected else 0
            }
            
        except Exception as e:
            self.logger.error(f"Divergence analysis failed: {e}")
            return {'error': str(e)}