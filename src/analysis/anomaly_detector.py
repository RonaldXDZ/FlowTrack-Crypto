"""
Anomaly Detection Engine

Identifies unusual market behavior using statistical outlier detection methods.
"""

import numpy as np
from typing import List, Dict, Any
import logging
from datetime import datetime

from ..config import Config
from ..models import KlineData, Anomaly
from ..exceptions import AnalysisError, InsufficientDataError


class AnomalyDetector:
    """Statistical anomaly detection for market data"""
    
    def __init__(self, config: Config):
        """
        Initialize anomaly detector.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def detect_anomalies(self, klines_data: List[KlineData]) -> List[Anomaly]:
        """
        Detect various types of market anomalies.
        
        Args:
            klines_data: List of KlineData objects
            
        Returns:
            List of detected anomalies
            
        Raises:
            InsufficientDataError: When insufficient data is available
            AnalysisError: For calculation errors
        """
        if not klines_data or len(klines_data) < 5:
            raise InsufficientDataError(
                "Insufficient data for anomaly detection",
                klines_data[0].symbol if klines_data else "",
                5,
                len(klines_data)
            )
        
        symbol = klines_data[0].symbol
        anomalies = []
        
        try:
            self.logger.debug(f"Starting anomaly detection for {symbol}")
            
            # Sort data by timestamp
            sorted_data = sorted(klines_data, key=lambda x: x.timestamp)
            
            # Extract time series data
            volumes = [k.quote_volume for k in sorted_data]
            net_inflows = [k.net_inflow for k in sorted_data]
            price_changes = [
                abs(k.close - k.open) / k.open 
                for k in sorted_data
            ]
            
            # Calculate statistical thresholds
            vol_mean = np.mean(volumes)
            vol_std = np.std(volumes)
            price_change_mean = np.mean(price_changes)
            price_change_std = np.std(price_changes)
            
            # Detect different types of anomalies
            for i, kline in enumerate(sorted_data):
                # High volume, low price change anomaly
                if (kline.quote_volume > vol_mean + self.config.analysis.anomaly_threshold * vol_std and
                    price_changes[i] < price_change_mean + 0.5 * price_change_std):
                    
                    anomalies.append(Anomaly(
                        timestamp=kline.open_time,
                        type='high_volume_low_price_change',
                        symbol=symbol,
                        volume=kline.quote_volume,
                        price_change=price_changes[i],
                        net_inflow=kline.net_inflow,
                        severity=self._calculate_severity(
                            kline.quote_volume, vol_mean, vol_std, 'volume'
                        ),
                        additional_data={
                            'volume_z_score': (kline.quote_volume - vol_mean) / vol_std,
                            'price_change_z_score': (price_changes[i] - price_change_mean) / price_change_std,
                            'description': '成交量异常高但价格变化较小，可能是大资金建仓或出货'
                        }
                    ))
                
                # High price change, low volume anomaly
                if (price_changes[i] > price_change_mean + self.config.analysis.anomaly_threshold * price_change_std and
                    kline.quote_volume < vol_mean + 0.5 * vol_std):
                    
                    anomalies.append(Anomaly(
                        timestamp=kline.open_time,
                        type='high_price_change_low_volume',
                        symbol=symbol,
                        volume=kline.quote_volume,
                        price_change=price_changes[i],
                        net_inflow=kline.net_inflow,
                        severity=self._calculate_severity(
                            price_changes[i], price_change_mean, price_change_std, 'price_change'
                        ),
                        additional_data={
                            'volume_z_score': (kline.quote_volume - vol_mean) / vol_std,
                            'price_change_z_score': (price_changes[i] - price_change_mean) / price_change_std,
                            'description': '价格异常波动但成交量不高，可能是薄盘或操纵行为'
                        }
                    ))
                
                # Extreme net inflow anomaly
                if (kline.net_inflow > 0 and 
                    kline.net_inflow > self.config.analysis.extreme_flow_threshold * kline.quote_volume):
                    
                    inflow_ratio = kline.net_inflow / kline.quote_volume if kline.quote_volume > 0 else 0
                    
                    anomalies.append(Anomaly(
                        timestamp=kline.open_time,
                        type='extreme_net_inflow',
                        symbol=symbol,
                        volume=kline.quote_volume,
                        price_change=price_changes[i],
                        net_inflow=kline.net_inflow,
                        severity=self._calculate_inflow_severity(inflow_ratio),
                        additional_data={
                            'inflow_ratio': inflow_ratio,
                            'description': f'极端资金净流入，买方资金占比{inflow_ratio:.1%}'
                        }
                    ))
                
                # Extreme net outflow anomaly
                if (kline.net_inflow < 0 and 
                    abs(kline.net_inflow) > self.config.analysis.extreme_flow_threshold * kline.quote_volume):
                    
                    outflow_ratio = abs(kline.net_inflow) / kline.quote_volume if kline.quote_volume > 0 else 0
                    
                    anomalies.append(Anomaly(
                        timestamp=kline.open_time,
                        type='extreme_net_outflow',
                        symbol=symbol,
                        volume=kline.quote_volume,
                        price_change=price_changes[i],
                        net_inflow=kline.net_inflow,
                        severity=self._calculate_inflow_severity(outflow_ratio),
                        additional_data={
                            'outflow_ratio': outflow_ratio,
                            'description': f'极端资金净流出，卖方资金占比{outflow_ratio:.1%}'
                        }
                    ))
            
            # Detect pattern-based anomalies
            pattern_anomalies = self._detect_pattern_anomalies(sorted_data)
            anomalies.extend(pattern_anomalies)
            
            self.logger.debug(f"Detected {len(anomalies)} anomalies for {symbol}")
            return anomalies
            
        except Exception as e:
            raise AnalysisError(
                f"Anomaly detection failed for {symbol}",
                "anomaly_detection",
                symbol,
                str(e)
            )
    
    def _calculate_severity(
        self, 
        value: float, 
        mean: float, 
        std: float, 
        metric_type: str
    ) -> str:
        """
        Calculate anomaly severity based on z-score.
        
        Args:
            value: Observed value
            mean: Mean of the distribution
            std: Standard deviation
            metric_type: Type of metric for context
            
        Returns:
            Severity level string
        """
        if std == 0:
            return 'medium'
        
        z_score = abs(value - mean) / std
        
        if z_score > 3:
            return 'critical'
        elif z_score > 2.5:
            return 'high'
        elif z_score > 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_inflow_severity(self, ratio: float) -> str:
        """Calculate severity based on inflow/outflow ratio."""
        if ratio > 0.9:
            return 'critical'
        elif ratio > 0.8:
            return 'high'
        elif ratio > 0.7:
            return 'medium'
        else:
            return 'low'
    
    def _detect_pattern_anomalies(self, sorted_data: List[KlineData]) -> List[Anomaly]:
        """
        Detect pattern-based anomalies.
        
        Args:
            sorted_data: Time-sorted klines data
            
        Returns:
            List of pattern-based anomalies
        """
        anomalies = []
        symbol = sorted_data[0].symbol
        
        try:
            # Detect sudden volume spikes
            volumes = [k.quote_volume for k in sorted_data]
            
            for i in range(1, len(volumes)):
                # Volume spike anomaly
                if i >= 3:  # Need at least 3 previous periods for comparison
                    recent_avg = np.mean(volumes[i-3:i])
                    current_volume = volumes[i]
                    
                    if current_volume > recent_avg * 5:  # 5x spike
                        anomalies.append(Anomaly(
                            timestamp=sorted_data[i].open_time,
                            type='volume_spike',
                            symbol=symbol,
                            volume=current_volume,
                            price_change=abs(sorted_data[i].close - sorted_data[i].open) / sorted_data[i].open,
                            net_inflow=sorted_data[i].net_inflow,
                            severity='high',
                            additional_data={
                                'spike_ratio': current_volume / recent_avg,
                                'recent_avg_volume': recent_avg,
                                'description': f'成交量突然激增{current_volume/recent_avg:.1f}倍'
                            }
                        ))
            
            # Detect price-volume divergence
            price_changes = [
                (k.close - k.open) / k.open 
                for k in sorted_data
            ]
            
            for i in range(5, len(sorted_data)):  # Need history for comparison
                recent_price_changes = price_changes[i-5:i]
                recent_volumes = volumes[i-5:i]
                
                current_price_change = price_changes[i]
                current_volume = volumes[i]
                
                # Strong price move with declining volume
                if (abs(current_price_change) > np.mean([abs(pc) for pc in recent_price_changes]) * 2 and
                    current_volume < np.mean(recent_volumes) * 0.7):
                    
                    anomalies.append(Anomaly(
                        timestamp=sorted_data[i].open_time,
                        type='price_volume_divergence',
                        symbol=symbol,
                        volume=current_volume,
                        price_change=abs(current_price_change),
                        net_inflow=sorted_data[i].net_inflow,
                        severity='medium',
                        additional_data={
                            'price_change': current_price_change,
                            'volume_ratio': current_volume / np.mean(recent_volumes),
                            'description': '价格大幅波动但成交量萎缩，可能是假突破'
                        }
                    ))
            
            # Detect unusual inflow patterns
            net_inflows = [k.net_inflow for k in sorted_data]
            
            for i in range(3, len(net_inflows)):
                # Consistent inflow direction change
                recent_inflows = net_inflows[i-3:i]
                current_inflow = net_inflows[i]
                
                # All recent were positive, current is strongly negative
                if (all(flow > 0 for flow in recent_inflows) and 
                    current_inflow < -np.mean(recent_inflows) * 2):
                    
                    anomalies.append(Anomaly(
                        timestamp=sorted_data[i].open_time,
                        type='inflow_direction_reversal',
                        symbol=symbol,
                        volume=sorted_data[i].quote_volume,
                        price_change=abs(sorted_data[i].close - sorted_data[i].open) / sorted_data[i].open,
                        net_inflow=current_inflow,
                        severity='medium',
                        additional_data={
                            'reversal_magnitude': abs(current_inflow) / np.mean(recent_inflows),
                            'description': '资金流向突然反转，可能是趋势转换信号'
                        }
                    ))
            
        except Exception as e:
            self.logger.error(f"Pattern anomaly detection failed: {e}")
        
        return anomalies
    
    def batch_detect_anomalies(
        self, 
        symbols_data: Dict[str, List[KlineData]]
    ) -> Dict[str, List[Anomaly]]:
        """
        Detect anomalies for multiple symbols.
        
        Args:
            symbols_data: Dictionary mapping symbols to their klines data
            
        Returns:
            Dictionary mapping symbols to their detected anomalies
        """
        results = {}
        
        for symbol, klines_data in symbols_data.items():
            try:
                anomalies = self.detect_anomalies(klines_data)
                results[symbol] = anomalies
                
            except Exception as e:
                self.logger.error(f"Anomaly detection failed for {symbol}: {e}")
                results[symbol] = []
        
        return results
    
    def filter_anomalies_by_severity(
        self, 
        anomalies: List[Anomaly], 
        min_severity: str = 'medium'
    ) -> List[Anomaly]:
        """
        Filter anomalies by minimum severity level.
        
        Args:
            anomalies: List of anomalies to filter
            min_severity: Minimum severity level ('low', 'medium', 'high', 'critical')
            
        Returns:
            Filtered list of anomalies
        """
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        min_level = severity_order.get(min_severity, 1)
        
        return [
            anomaly for anomaly in anomalies
            if severity_order.get(anomaly.severity, 0) >= min_level
        ]
    
    def get_anomaly_summary(self, anomalies: List[Anomaly]) -> Dict[str, Any]:
        """
        Generate summary statistics for detected anomalies.
        
        Args:
            anomalies: List of anomalies
            
        Returns:
            Dictionary containing summary statistics
        """
        if not anomalies:
            return {
                'total_count': 0,
                'by_type': {},
                'by_severity': {},
                'time_range': None
            }
        
        # Count by type
        type_counts = {}
        for anomaly in anomalies:
            type_counts[anomaly.type] = type_counts.get(anomaly.type, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for anomaly in anomalies:
            severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
        
        # Time range
        timestamps = [anomaly.timestamp for anomaly in anomalies]
        time_range = {
            'start': min(timestamps).isoformat(),
            'end': max(timestamps).isoformat()
        }
        
        return {
            'total_count': len(anomalies),
            'by_type': type_counts,
            'by_severity': severity_counts,
            'time_range': time_range,
            'most_common_type': max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        }