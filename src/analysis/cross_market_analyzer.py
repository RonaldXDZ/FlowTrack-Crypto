"""
Cross-Market Analysis Engine

Analyzes relationships between spot and futures markets to identify
arbitrage opportunities, lead-lag relationships, and market efficiency.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from ..config import Config
from ..models import KlineData, CrossMarketMetrics, LeadLagAnalysis
from ..exceptions import AnalysisError, InsufficientDataError


class CrossMarketAnalyzer:
    """Advanced cross-market analysis engine"""
    
    def __init__(self, config: Config):
        """
        Initialize cross-market analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def analyze_cross_market_flows(
        self, 
        spot_klines: List[KlineData], 
        futures_klines: List[KlineData]
    ) -> CrossMarketMetrics:
        """
        Analyze capital flow differences between spot and futures markets.
        
        Args:
            spot_klines: Spot market K-line data
            futures_klines: Futures market K-line data
            
        Returns:
            CrossMarketMetrics object with comparison results
            
        Raises:
            InsufficientDataError: When insufficient data is available
            AnalysisError: For calculation errors
        """
        if not spot_klines or not futures_klines:
            raise InsufficientDataError(
                "Insufficient data for cross-market analysis",
                spot_klines[0].symbol if spot_klines else futures_klines[0].symbol if futures_klines else "",
                required_points=1,
                available_points=min(len(spot_klines), len(futures_klines))
            )
        
        symbol = spot_klines[0].symbol
        
        try:
            self.logger.debug(f"Starting cross-market analysis for {symbol}")
            
            # Get recent data (last 10 periods)
            recent_spot = spot_klines[-10:] if len(spot_klines) >= 10 else spot_klines
            recent_futures = futures_klines[-10:] if len(futures_klines) >= 10 else futures_klines
            
            # Calculate total inflows
            spot_total_inflow = sum(k.net_inflow for k in recent_spot)
            futures_total_inflow = sum(k.net_inflow for k in recent_futures)
            
            # Calculate flow difference
            flow_difference = spot_total_inflow - futures_total_inflow
            
            # Calculate correlation if we have matching data
            correlation = None
            if len(recent_spot) == len(recent_futures) and len(recent_spot) > 1:
                spot_inflows = [k.net_inflow for k in recent_spot]
                futures_inflows = [k.net_inflow for k in recent_futures]
                correlation = np.corrcoef(spot_inflows, futures_inflows)[0, 1]
            
            # Determine dominant market
            dominant_market = "spot" if spot_total_inflow > futures_total_inflow else "futures"
            
            # Calculate flow ratio
            flow_ratio = (
                abs(spot_total_inflow / futures_total_inflow) 
                if futures_total_inflow != 0 
                else float('inf')
            )
            
            metrics = CrossMarketMetrics(
                spot_total_inflow=spot_total_inflow,
                futures_total_inflow=futures_total_inflow,
                flow_difference=flow_difference,
                correlation=correlation,
                dominant_market=dominant_market,
                flow_ratio=flow_ratio
            )
            
            self.logger.debug(f"Cross-market analysis completed for {symbol}")
            return metrics
            
        except Exception as e:
            raise AnalysisError(
                f"Cross-market analysis failed for {symbol}",
                "cross_market_analysis",
                symbol,
                str(e)
            )
    
    def analyze_lead_lag_relationship(
        self, 
        klines_data: List[KlineData]
    ) -> LeadLagAnalysis:
        """
        Analyze lead-lag relationship between price and capital flow.
        
        Args:
            klines_data: K-line data for analysis
            
        Returns:
            LeadLagAnalysis object with relationship results
            
        Raises:
            InsufficientDataError: When insufficient data is available
            AnalysisError: For calculation errors
        """
        if not klines_data or len(klines_data) < 10:
            raise InsufficientDataError(
                "Insufficient data for lead-lag analysis",
                klines_data[0].symbol if klines_data else "",
                required_points=10,
                available_points=len(klines_data)
            )
        
        symbol = klines_data[0].symbol
        
        try:
            self.logger.debug(f"Starting lead-lag analysis for {symbol}")
            
            # Sort data by timestamp
            sorted_data = sorted(klines_data, key=lambda x: x.timestamp)
            
            # Extract price and inflow data
            prices = [k.close for k in sorted_data]
            inflows = [k.net_inflow for k in sorted_data]
            
            # Calculate correlations for different lag periods
            correlations = []
            for lag in range(-5, 6):  # From -5 to 5 lag periods
                if lag < 0:
                    # Capital flow leads price (negative lag)
                    corr = np.corrcoef(inflows[:lag], prices[-lag:])[0, 1]
                elif lag > 0:
                    # Price leads capital flow (positive lag)
                    corr = np.corrcoef(inflows[lag:], prices[:-lag])[0, 1]
                else:
                    # Synchronous relationship (zero lag)
                    corr = np.corrcoef(inflows, prices)[0, 1]
                
                correlations.append((lag, corr))
            
            # Find optimal lag (maximum absolute correlation)
            max_corr_lag = max(correlations, key=lambda x: abs(x[1]))
            optimal_lag = max_corr_lag[0]
            max_correlation = max_corr_lag[1]
            
            # Determine relationship type
            if optimal_lag < 0:
                relationship = "资金流向领先于价格"
            elif optimal_lag > 0:
                relationship = "价格领先于资金流向"
            else:
                relationship = "同步变化"
            
            analysis = LeadLagAnalysis(
                symbol=symbol,
                max_correlation=max_correlation,
                optimal_lag=optimal_lag,
                relationship=relationship,
                all_correlations=correlations,
                timestamp=datetime.now()
            )
            
            self.logger.debug(f"Lead-lag analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            raise AnalysisError(
                f"Lead-lag analysis failed for {symbol}",
                "lead_lag_analysis",
                symbol,
                str(e)
            )
    
    def detect_arbitrage_opportunities(
        self, 
        spot_klines: List[KlineData], 
        futures_klines: List[KlineData],
        threshold: float = 0.02
    ) -> Dict[str, Any]:
        """
        Detect potential arbitrage opportunities between spot and futures.
        
        Args:
            spot_klines: Spot market data
            futures_klines: Futures market data
            threshold: Price difference threshold for arbitrage detection
            
        Returns:
            Dictionary containing arbitrage analysis
        """
        if not spot_klines or not futures_klines:
            return {'error': 'Insufficient data for arbitrage analysis'}
        
        symbol = spot_klines[0].symbol
        
        try:
            # Get latest prices
            latest_spot_price = spot_klines[-1].close
            latest_futures_price = futures_klines[-1].close
            
            # Calculate price difference
            price_diff = futures_klines[-1].close - spot_klines[-1].close
            price_diff_pct = price_diff / spot_klines[-1].close
            
            # Detect arbitrage opportunities
            arbitrage_detected = abs(price_diff_pct) > threshold
            
            if arbitrage_detected:
                if price_diff_pct > 0:
                    opportunity_type = 'futures_premium'
                    action = 'sell_futures_buy_spot'
                else:
                    opportunity_type = 'spot_premium'
                    action = 'buy_futures_sell_spot'
            else:
                opportunity_type = 'none'
                action = 'no_action'
            
            # Calculate historical price correlation
            if len(spot_klines) == len(futures_klines) and len(spot_klines) > 1:
                spot_prices = [k.close for k in spot_klines[-20:]]  # Last 20 periods
                futures_prices = [k.close for k in futures_klines[-20:]]
                
                if len(spot_prices) == len(futures_prices):
                    price_correlation = np.corrcoef(spot_prices, futures_prices)[0, 1]
                else:
                    price_correlation = None
            else:
                price_correlation = None
            
            # Calculate average spread over recent periods
            recent_spreads = []
            min_length = min(len(spot_klines), len(futures_klines), 10)
            
            for i in range(-min_length, 0):
                spread = futures_klines[i].close - spot_klines[i].close
                spread_pct = spread / spot_klines[i].close
                recent_spreads.append(spread_pct)
            
            avg_spread = np.mean(recent_spreads) if recent_spreads else 0
            spread_volatility = np.std(recent_spreads) if len(recent_spreads) > 1 else 0
            
            return {
                'symbol': symbol,
                'arbitrage_detected': arbitrage_detected,
                'opportunity_type': opportunity_type,
                'suggested_action': action,
                'current_spread': price_diff,
                'current_spread_pct': price_diff_pct,
                'threshold': threshold,
                'spot_price': latest_spot_price,
                'futures_price': latest_futures_price,
                'price_correlation': price_correlation,
                'average_spread_pct': avg_spread,
                'spread_volatility': spread_volatility,
                'profit_potential': abs(price_diff_pct) - threshold if arbitrage_detected else 0,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Arbitrage analysis failed for {symbol}: {e}")
            return {'error': str(e)}
    
    def analyze_market_efficiency(
        self, 
        spot_klines: List[KlineData], 
        futures_klines: List[KlineData]
    ) -> Dict[str, Any]:
        """
        Analyze market efficiency between spot and futures markets.
        
        Args:
            spot_klines: Spot market data
            futures_klines: Futures market data
            
        Returns:
            Dictionary containing market efficiency analysis
        """
        if not spot_klines or not futures_klines:
            return {'error': 'Insufficient data for efficiency analysis'}
        
        symbol = spot_klines[0].symbol
        
        try:
            # Align data by finding common time periods
            spot_dict = {k.timestamp: k for k in spot_klines}
            futures_dict = {k.timestamp: k for k in futures_klines}
            
            common_timestamps = set(spot_dict.keys()) & set(futures_dict.keys())
            
            if len(common_timestamps) < 5:
                return {'error': 'Insufficient overlapping data'}
            
            # Sort common timestamps
            sorted_timestamps = sorted(common_timestamps)
            
            # Extract aligned price data
            spot_prices = [spot_dict[ts].close for ts in sorted_timestamps]
            futures_prices = [futures_dict[ts].close for ts in sorted_timestamps]
            
            # Calculate price correlations
            price_correlation = np.corrcoef(spot_prices, futures_prices)[0, 1]
            
            # Calculate return correlations
            spot_returns = [
                (spot_prices[i] - spot_prices[i-1]) / spot_prices[i-1] 
                for i in range(1, len(spot_prices))
            ]
            futures_returns = [
                (futures_prices[i] - futures_prices[i-1]) / futures_prices[i-1] 
                for i in range(1, len(futures_prices))
            ]
            
            return_correlation = np.corrcoef(spot_returns, futures_returns)[0, 1] if len(spot_returns) > 1 else 0
            
            # Calculate basis (futures - spot) statistics
            basis_values = [futures_prices[i] - spot_prices[i] for i in range(len(spot_prices))]
            basis_pct = [basis_values[i] / spot_prices[i] for i in range(len(spot_prices))]
            
            avg_basis = np.mean(basis_values)
            avg_basis_pct = np.mean(basis_pct)
            basis_volatility = np.std(basis_pct)
            
            # Calculate mean reversion characteristics
            basis_changes = [basis_pct[i] - basis_pct[i-1] for i in range(1, len(basis_pct))]
            mean_reversion_tendency = -np.corrcoef(basis_pct[:-1], basis_changes)[0, 1] if len(basis_changes) > 1 else 0
            
            # Market efficiency score (higher = more efficient)
            efficiency_score = (
                abs(price_correlation) * 0.4 +
                abs(return_correlation) * 0.3 +
                (1 - min(basis_volatility, 1.0)) * 0.2 +
                abs(mean_reversion_tendency) * 0.1
            )
            
            # Determine efficiency level
            if efficiency_score > 0.8:
                efficiency_level = 'high'
            elif efficiency_score > 0.6:
                efficiency_level = 'medium'
            else:
                efficiency_level = 'low'
            
            return {
                'symbol': symbol,
                'efficiency_score': efficiency_score,
                'efficiency_level': efficiency_level,
                'price_correlation': price_correlation,
                'return_correlation': return_correlation,
                'average_basis': avg_basis,
                'average_basis_pct': avg_basis_pct,
                'basis_volatility': basis_volatility,
                'mean_reversion_tendency': mean_reversion_tendency,
                'data_points_analyzed': len(sorted_timestamps),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Market efficiency analysis failed for {symbol}: {e}")
            return {'error': str(e)}
    
    def detect_funding_rate_impact(
        self, 
        futures_klines: List[KlineData],
        funding_times: List[datetime]
    ) -> Dict[str, Any]:
        """
        Analyze the impact of funding rate settlements on market behavior.
        
        Args:
            futures_klines: Futures market data
            funding_times: List of funding rate settlement times
            
        Returns:
            Dictionary containing funding rate impact analysis
        """
        if not futures_klines or not funding_times:
            return {'error': 'Insufficient data for funding rate analysis'}
        
        symbol = futures_klines[0].symbol
        
        try:
            # Analyze price and volume behavior around funding times
            impact_analysis = []
            
            for funding_time in funding_times:
                # Find klines around funding time (±30 minutes)
                relevant_klines = [
                    k for k in futures_klines
                    if abs((k.open_time - funding_time).total_seconds()) <= 1800  # 30 minutes
                ]
                
                if len(relevant_klines) < 3:
                    continue
                
                # Sort by time relative to funding
                relevant_klines.sort(key=lambda x: x.open_time)
                
                # Analyze before/after funding
                before_funding = [k for k in relevant_klines if k.open_time < funding_time]
                after_funding = [k for k in relevant_klines if k.open_time >= funding_time]
                
                if before_funding and after_funding:
                    # Calculate price impact
                    price_before = np.mean([k.close for k in before_funding])
                    price_after = np.mean([k.close for k in after_funding])
                    price_impact = (price_after - price_before) / price_before
                    
                    # Calculate volume impact
                    volume_before = np.mean([k.quote_volume for k in before_funding])
                    volume_after = np.mean([k.quote_volume for k in after_funding])
                    volume_impact = (volume_after - volume_before) / volume_before if volume_before > 0 else 0
                    
                    impact_analysis.append({
                        'funding_time': funding_time.isoformat(),
                        'price_impact': price_impact,
                        'volume_impact': volume_impact,
                        'periods_before': len(before_funding),
                        'periods_after': len(after_funding)
                    })
            
            if not impact_analysis:
                return {'error': 'No funding events found in data range'}
            
            # Calculate aggregate statistics
            price_impacts = [a['price_impact'] for a in impact_analysis]
            volume_impacts = [a['volume_impact'] for a in impact_analysis]
            
            avg_price_impact = np.mean(price_impacts)
            avg_volume_impact = np.mean(volume_impacts)
            price_impact_volatility = np.std(price_impacts)
            
            return {
                'symbol': symbol,
                'funding_events_analyzed': len(impact_analysis),
                'average_price_impact': avg_price_impact,
                'average_volume_impact': avg_volume_impact,
                'price_impact_volatility': price_impact_volatility,
                'individual_impacts': impact_analysis,
                'significant_impact_detected': abs(avg_price_impact) > 0.001,  # 0.1% threshold
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Funding rate impact analysis failed for {symbol}: {e}")
            return {'error': str(e)}