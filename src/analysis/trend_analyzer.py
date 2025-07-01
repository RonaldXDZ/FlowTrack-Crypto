"""
Trend Analysis Engine

Provides comprehensive trend analysis using statistical methods
to determine market stages and confidence levels.
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..config import Config
from ..models import KlineData, TrendAnalysis, TrendMetrics
from ..exceptions import AnalysisError, InsufficientDataError, validate_data_sufficiency


class TrendAnalyzer:
    """Advanced statistical trend analysis engine"""
    
    def __init__(self, config: Config):
        """
        Initialize trend analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def analyze_funding_flow_trend(self, klines_data: List[KlineData]) -> TrendAnalysis:
        """
        Perform comprehensive trend analysis on funding flow data.
        
        Args:
            klines_data: List of KlineData objects
            
        Returns:
            TrendAnalysis object with comprehensive results
            
        Raises:
            InsufficientDataError: When insufficient data is available
            AnalysisError: For calculation errors
        """
        if not klines_data:
            raise InsufficientDataError(
                "No data provided for trend analysis",
                required_points=self.config.analysis.min_data_points,
                available_points=0
            )
        
        # Validate data sufficiency
        validate_data_sufficiency(
            klines_data,
            self.config.analysis.min_data_points,
            klines_data[0].symbol if klines_data else "",
            "trend_analysis"
        )
        
        symbol = klines_data[0].symbol
        
        try:
            self.logger.debug(f"Starting trend analysis for {symbol}")
            
            # Sort data by timestamp
            sorted_data = sorted(klines_data, key=lambda x: x.timestamp)
            
            # Extract time series data
            prices = [k.close for k in sorted_data]
            net_inflows = [k.net_inflow for k in sorted_data]
            volumes = [k.quote_volume for k in sorted_data]
            
            # Calculate trend metrics
            metrics = self._calculate_trend_metrics(prices, net_inflows, volumes)
            
            # Determine market stage
            trend, confidence, description, reasons = self._determine_market_stage(metrics)
            
            # Create result
            analysis = TrendAnalysis(
                symbol=symbol,
                trend=trend,
                confidence=confidence,
                description=description,
                reasons=reasons,
                metrics=metrics,
                timestamp=datetime.now()
            )
            
            self.logger.debug(f"Trend analysis completed for {symbol}: {trend} (confidence: {confidence:.2f})")
            return analysis
            
        except Exception as e:
            raise AnalysisError(
                f"Trend analysis failed for {symbol}",
                "trend_analysis",
                symbol,
                str(e)
            )
    
    def _calculate_trend_metrics(
        self, 
        prices: List[float], 
        net_inflows: List[float], 
        volumes: List[float]
    ) -> TrendMetrics:
        """
        Calculate comprehensive trend metrics.
        
        Args:
            prices: List of closing prices
            net_inflows: List of net inflow values
            volumes: List of volumes
            
        Returns:
            TrendMetrics object with all calculated metrics
        """
        try:
            # Calculate price trend metrics
            price_changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
            price_trend = sum(1 for change in price_changes if change > 0) / len(price_changes)
            
            # Linear regression for price trend
            x = np.arange(len(prices))
            price_slope, _, price_r_value, price_p_value, _ = stats.linregress(x, prices)
            price_trend_direction = 'up' if price_slope > 0 else 'down'
            price_trend_strength = abs(price_r_value)
            
            # Calculate inflow trend metrics
            inflow_changes = [net_inflows[i] - net_inflows[i - 1] for i in range(1, len(net_inflows))]
            inflow_trend = sum(1 for change in inflow_changes if change > 0) / len(inflow_changes)
            
            # Linear regression for inflow trend
            inflow_slope, _, inflow_r_value, inflow_p_value, _ = stats.linregress(x, net_inflows)
            inflow_trend_direction = 'increasing' if inflow_slope > 0 else 'decreasing'
            inflow_trend_strength = abs(inflow_r_value)
            
            # Calculate correlations
            price_inflow_correlation = np.corrcoef(prices, net_inflows)[0, 1]
            inflow_volume_correlation = np.corrcoef(net_inflows, volumes)[0, 1]
            
            # Calculate price volatility
            price_volatility = np.std(price_changes) / np.mean(prices) if np.mean(prices) != 0 else 0
            
            # Calculate recent inflow trend (last 10 periods)
            recent_inflows = net_inflows[-10:] if len(net_inflows) >= 10 else net_inflows
            if len(recent_inflows) > 1:
                recent_inflow_changes = [recent_inflows[i] - recent_inflows[i - 1] 
                                       for i in range(1, len(recent_inflows))]
                recent_inflow_trend = sum(1 for change in recent_inflow_changes if change > 0) / len(recent_inflow_changes)
            else:
                recent_inflow_trend = 0.5
            
            return TrendMetrics(
                price_trend=price_trend,
                price_trend_direction=price_trend_direction,
                price_trend_strength=price_trend_strength,
                price_trend_p_value=price_p_value,
                inflow_trend=inflow_trend,
                inflow_trend_direction=inflow_trend_direction,
                inflow_trend_strength=inflow_trend_strength,
                inflow_trend_p_value=inflow_p_value,
                correlation=price_inflow_correlation,
                inflow_volume_correlation=inflow_volume_correlation,
                price_volatility=price_volatility,
                recent_inflow_trend=recent_inflow_trend
            )
            
        except Exception as e:
            raise AnalysisError(
                "Failed to calculate trend metrics",
                "trend_metrics",
                calculation_step="metric_calculation"
            )
    
    def _determine_market_stage(
        self, 
        metrics: TrendMetrics
    ) -> tuple[str, float, str, List[str]]:
        """
        Determine market stage based on trend metrics.
        
        Args:
            metrics: Calculated trend metrics
            
        Returns:
            Tuple of (stage, confidence, description, reasons)
        """
        reasons = []
        
        # Extract key metrics for easier reference
        price_trend = metrics.price_trend
        inflow_trend = metrics.inflow_trend
        correlation = metrics.correlation
        price_volatility = metrics.price_volatility
        price_strength = metrics.price_trend_strength
        inflow_strength = metrics.inflow_trend_strength
        
        # Market stage detection logic
        stage = 'unknown'
        confidence = 0.0
        
        # Top stage detection
        if (price_trend > 0.7 and inflow_trend < 0.3 and correlation < -0.3):
            stage = 'top'
            confidence = min(0.7 + price_trend - inflow_trend - correlation, 0.95)
            reasons = [
                "价格持续上涨但资金流入减少",
                "价格与资金流向呈负相关",
                f"价格趋势强度: {price_strength:.2f}, 资金流向趋势强度: {inflow_strength:.2f}"
            ]
        
        # Bottom stage detection
        elif (price_trend < 0.3 and inflow_trend > 0.7 and correlation < -0.3):
            stage = 'bottom'
            confidence = min(0.7 - price_trend + inflow_trend - correlation, 0.95)
            reasons = [
                "价格持续下跌但资金流入增加",
                "价格与资金流向呈负相关",
                f"价格趋势强度: {price_strength:.2f}, 资金流向趋势强度: {inflow_strength:.2f}"
            ]
        
        # Rising stage detection
        elif (price_trend > 0.6 and inflow_trend > 0.6 and correlation > 0.3):
            stage = 'rising'
            confidence = min(price_trend + inflow_trend + correlation - 1.0, 0.95)
            reasons = [
                "价格与资金流入同步增加",
                "价格与资金流向呈正相关",
                f"价格趋势强度: {price_strength:.2f}, 资金流向趋势强度: {inflow_strength:.2f}"
            ]
        
        # Falling stage detection
        elif (price_trend < 0.4 and inflow_trend < 0.4 and correlation > 0.3):
            stage = 'falling'
            confidence = min(1.0 - price_trend - inflow_trend + correlation, 0.95)
            reasons = [
                "价格与资金流入同步减少",
                "价格与资金流向呈正相关",
                f"价格趋势强度: {price_strength:.2f}, 资金流向趋势强度: {inflow_strength:.2f}"
            ]
        
        # Consolidation stage detection
        elif (abs(price_trend - 0.5) < 0.15 and price_volatility < 0.01):
            stage = 'consolidation'
            confidence = 0.5 + (0.15 - abs(price_trend - 0.5)) * 3
            reasons = [
                "价格波动率低",
                "无明显趋势",
                f"价格波动率: {price_volatility:.4f}"
            ]
        
        # Advanced pattern detection
        else:
            stage, confidence, additional_reasons = self._detect_advanced_patterns(metrics)
            reasons.extend(additional_reasons)
        
        # Create description
        description = f"价格可能处于{stage}阶段，置信度{confidence:.2f}"
        
        return stage, confidence, description, reasons
    
    def _detect_advanced_patterns(self, metrics: TrendMetrics) -> tuple[str, float, List[str]]:
        """
        Detect advanced market patterns.
        
        Args:
            metrics: Trend metrics
            
        Returns:
            Tuple of (stage, confidence, reasons)
        """
        price_trend = metrics.price_trend
        inflow_trend = metrics.inflow_trend
        price_strength = metrics.price_trend_strength
        inflow_strength = metrics.inflow_trend_strength
        
        reasons = []
        
        # Weakening rise pattern
        if price_trend > 0.5 and inflow_trend < 0.5:
            stage = 'weakening_rise'
            confidence = price_trend * (1 - inflow_trend)
            reasons = [
                "价格上升但资金流向减弱",
                f"可能出现上涨乏力迹象"
            ]
        
        # Strengthening fall pattern
        elif price_trend < 0.5 and inflow_trend > 0.5:
            stage = 'potential_reversal'
            confidence = (1 - price_trend) * inflow_trend
            reasons = [
                "价格下降但资金流向增强",
                f"可能出现反转迹象"
            ]
        
        # Divergence patterns
        elif abs(price_strength - inflow_strength) > 0.3:
            if price_strength > inflow_strength:
                stage = 'price_led_movement'
                confidence = price_strength - inflow_strength
                reasons = [
                    "价格主导的市场走势",
                    "资金流向滞后于价格变化"
                ]
            else:
                stage = 'flow_led_movement'
                confidence = inflow_strength - price_strength
                reasons = [
                    "资金流向主导的市场走势",
                    "价格可能跟随资金流向变化"
                ]
        
        # Default case
        else:
            if price_trend > 0.5:
                stage = 'rising'
                confidence = price_trend
                reasons = ["价格呈上升趋势"]
            else:
                stage = 'falling'
                confidence = 1 - price_trend
                reasons = ["价格呈下降趋势"]
        
        return stage, confidence, reasons
    
    def batch_analyze_trends(
        self, 
        symbols_data: Dict[str, List[KlineData]]
    ) -> Dict[str, TrendAnalysis]:
        """
        Analyze trends for multiple symbols.
        
        Args:
            symbols_data: Dictionary mapping symbols to their klines data
            
        Returns:
            Dictionary mapping symbols to their trend analysis results
        """
        results = {}
        
        for symbol, klines_data in symbols_data.items():
            try:
                analysis = self.analyze_funding_flow_trend(klines_data)
                results[symbol] = analysis
                
            except Exception as e:
                self.logger.error(f"Trend analysis failed for {symbol}: {e}")
                # Create error result
                results[symbol] = TrendAnalysis(
                    symbol=symbol,
                    trend='error',
                    confidence=0.0,
                    description=f"分析失败: {str(e)}",
                    reasons=[f"错误: {str(e)}"],
                    metrics=TrendMetrics(
                        price_trend=0, price_trend_direction='unknown',
                        price_trend_strength=0, price_trend_p_value=1,
                        inflow_trend=0, inflow_trend_direction='unknown',
                        inflow_trend_strength=0, inflow_trend_p_value=1,
                        correlation=0, inflow_volume_correlation=0,
                        price_volatility=0, recent_inflow_trend=0
                    )
                )
        
        return results
    
    def compare_trends(
        self, 
        analyses: Dict[str, TrendAnalysis]
    ) -> Dict[str, Any]:
        """
        Compare trends across multiple symbols.
        
        Args:
            analyses: Dictionary of trend analyses by symbol
            
        Returns:
            Dictionary containing comparison results
        """
        if not analyses:
            return {}
        
        try:
            # Extract trends and confidences
            trends = {symbol: analysis.trend for symbol, analysis in analyses.items()}
            confidences = {symbol: analysis.confidence for symbol, analysis in analyses.items()}
            
            # Count trend types
            trend_counts = {}
            for trend in trends.values():
                trend_counts[trend] = trend_counts.get(trend, 0) + 1
            
            # Find dominant trend
            dominant_trend = max(trend_counts.items(), key=lambda x: x[1])
            
            # Calculate average confidence by trend
            confidence_by_trend = {}
            for symbol, trend in trends.items():
                if trend not in confidence_by_trend:
                    confidence_by_trend[trend] = []
                confidence_by_trend[trend].append(confidences[symbol])
            
            avg_confidence_by_trend = {
                trend: np.mean(conf_list) 
                for trend, conf_list in confidence_by_trend.items()
            }
            
            # Identify potential rotation patterns
            rotation_candidates = []
            trend_types = ['bottom', 'rising', 'top', 'falling']
            
            for i, trend1 in enumerate(trend_types):
                for j, trend2 in enumerate(trend_types):
                    if i != j and trend1 in trends.values() and trend2 in trends.values():
                        symbols1 = [s for s, t in trends.items() if t == trend1]
                        symbols2 = [s for s, t in trends.items() if t == trend2]
                        
                        if symbols1 and symbols2:
                            rotation_candidates.append({
                                'from_trend': trend1,
                                'to_trend': trend2,
                                'from_symbols': symbols1,
                                'to_symbols': symbols2
                            })
            
            return {
                'trend_distribution': trend_counts,
                'dominant_trend': dominant_trend,
                'confidence_by_trend': avg_confidence_by_trend,
                'rotation_candidates': rotation_candidates,
                'total_symbols': len(analyses),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Trend comparison failed: {e}")
            return {'error': str(e)}