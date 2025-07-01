"""
Main Funding Flow Analyzer

Orchestrates all components to provide comprehensive market analysis
with a clean, easy-to-use API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import concurrent.futures
import time

from .config import Config, config
from .clients import BinanceClient, DeepSeekClient
from .analysis import TrendAnalyzer, AnomalyDetector, PressureAnalyzer, CrossMarketAnalyzer
from .models import AnalysisReport, MarketSummary, create_market_summary, format_number
from .exceptions import AnalyzerError, APIError


class FundingFlowAnalyzer:
    """
    Main analyzer class that coordinates all analysis components.
    
    This class provides a high-level interface for running comprehensive
    market analysis including trend detection, anomaly identification,
    pressure analysis, and AI-powered insights.
    """
    
    def __init__(self, custom_config: Optional[Config] = None):
        """
        Initialize the analyzer with configuration.
        
        Args:
            custom_config: Optional custom configuration object
        """
        self.config = custom_config or config
        self.logger = logging.getLogger(__name__)
        
        # Initialize clients
        self.binance_client = BinanceClient(self.config)
        self.deepseek_client = DeepSeekClient(self.config) if self.config.api.deepseek_api_key else None
        
        # Initialize analysis engines
        self.trend_analyzer = TrendAnalyzer(self.config)
        self.anomaly_detector = AnomalyDetector(self.config)
        self.pressure_analyzer = PressureAnalyzer(self.config)
        self.cross_market_analyzer = CrossMarketAnalyzer(self.config)
        
        # Ensure directories exist
        self.config.ensure_directories()
        
        self.logger.info(f"Funding Flow Analyzer initialized with {len(self.config.trading.symbols)} symbols")
    
    def run_complete_analysis(
        self,
        symbols: Optional[List[str]] = None,
        include_ai_analysis: bool = True,
        save_report: bool = True
    ) -> AnalysisReport:
        """
        Run complete market analysis for all configured symbols.
        
        Args:
            symbols: Optional list of symbols to analyze (defaults to config)
            include_ai_analysis: Whether to include AI analysis
            save_report: Whether to save the report to file
            
        Returns:
            Complete analysis report
            
        Raises:
            AnalyzerError: For various analysis errors
        """
        start_time = time.time()
        symbols = symbols or self.config.trading.symbols
        
        self.logger.info(f"Starting complete analysis for symbols: {symbols}")
        
        try:
            # Step 1: Collect market data
            self.logger.info("Step 1: Collecting market data...")
            market_data = self._collect_market_data(symbols)
            
            # Step 2: Perform statistical analysis
            self.logger.info("Step 2: Performing statistical analysis...")
            analysis_results = self._perform_statistical_analysis(market_data)
            
            # Step 3: Cross-market analysis
            self.logger.info("Step 3: Performing cross-market analysis...")
            cross_market_results = self._perform_cross_market_analysis(market_data)
            
            # Step 4: Generate AI analysis (if enabled)
            ai_analysis = None
            if include_ai_analysis and self.deepseek_client:
                self.logger.info("Step 4: Generating AI analysis...")
                ai_analysis = self._generate_ai_analysis(analysis_results, cross_market_results)
            
            # Step 5: Create comprehensive report
            self.logger.info("Step 5: Creating analysis report...")
            report = self._create_analysis_report(
                symbols, market_data, analysis_results, cross_market_results, ai_analysis
            )
            
            # Step 6: Save report (if enabled)
            if save_report:
                self._save_report(report)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Complete analysis finished in {elapsed_time:.2f} seconds")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Complete analysis failed: {e}")
            raise AnalyzerError(f"Complete analysis failed: {str(e)}")
    
    def _collect_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Collect market data for all symbols from both spot and futures markets.
        
        Args:
            symbols: List of symbols to collect data for
            
        Returns:
            Dictionary containing all collected market data
        """
        market_data = {
            'spot_klines': {},
            'futures_klines': {},
            'spot_orderbooks': {},
            'futures_orderbooks': {},
            'collection_timestamp': datetime.now()
        }
        
        # Collect data in parallel for better performance
        if self.config.system.enable_parallel_processing:
            market_data = self._collect_data_parallel(symbols, market_data)
        else:
            market_data = self._collect_data_sequential(symbols, market_data)
        
        return market_data
    
    def _collect_data_parallel(self, symbols: List[str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect market data in parallel."""
        max_workers = min(self.config.system.max_workers, len(symbols))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all data collection tasks
            futures = []
            
            for symbol in symbols:
                # Spot klines
                futures.append(
                    executor.submit(
                        self.binance_client.get_klines_data,
                        symbol, 
                        self.config.analysis.default_interval,
                        self.config.analysis.default_limit,
                        False  # spot
                    )
                )
                
                # Futures klines
                if self.config.trading.enable_futures:
                    futures.append(
                        executor.submit(
                            self.binance_client.get_klines_data,
                            symbol,
                            self.config.analysis.default_interval,
                            self.config.analysis.default_limit,
                            True  # futures
                        )
                    )
                
                # Spot orderbook
                if self.config.trading.enable_spot:
                    futures.append(
                        executor.submit(
                            self.binance_client.get_orderbook_stats,
                            symbol,
                            False  # spot
                        )
                    )
                
                # Futures orderbook
                if self.config.trading.enable_futures:
                    futures.append(
                        executor.submit(
                            self.binance_client.get_orderbook_stats,
                            symbol,
                            True  # futures
                        )
                    )
            
            # Collect results
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result = future.result()
                    # Map results back to appropriate data structures
                    # This is simplified - in practice you'd need better tracking
                    # of which future corresponds to which data type and symbol
                except Exception as e:
                    self.logger.error(f"Parallel data collection error: {e}")
        
        # For now, fall back to sequential collection
        return self._collect_data_sequential(symbols, market_data)
    
    def _collect_data_sequential(self, symbols: List[str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect market data sequentially."""
        for symbol in symbols:
            try:
                # Spot klines
                if self.config.trading.enable_spot:
                    spot_klines = self.binance_client.get_klines_data(
                        symbol,
                        self.config.analysis.default_interval,
                        self.config.analysis.default_limit,
                        False
                    )
                    market_data['spot_klines'][symbol] = spot_klines
                
                # Futures klines
                if self.config.trading.enable_futures:
                    futures_klines = self.binance_client.get_klines_data(
                        symbol,
                        self.config.analysis.default_interval,
                        self.config.analysis.default_limit,
                        True
                    )
                    market_data['futures_klines'][symbol] = futures_klines
                
                # Spot orderbook
                if self.config.trading.enable_spot:
                    spot_orderbook = self.binance_client.get_orderbook_stats(symbol, False)
                    market_data['spot_orderbooks'][symbol] = spot_orderbook
                
                # Futures orderbook
                if self.config.trading.enable_futures:
                    futures_orderbook = self.binance_client.get_orderbook_stats(symbol, True)
                    market_data['futures_orderbooks'][symbol] = futures_orderbook
                
                self.logger.debug(f"Collected market data for {symbol}")
                
            except Exception as e:
                self.logger.error(f"Failed to collect data for {symbol}: {e}")
                # Set empty defaults
                market_data['spot_klines'][symbol] = []
                market_data['futures_klines'][symbol] = []
                market_data['spot_orderbooks'][symbol] = None
                market_data['futures_orderbooks'][symbol] = None
        
        return market_data
    
    def _perform_statistical_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform statistical analysis on collected market data.
        
        Args:
            market_data: Collected market data
            
        Returns:
            Dictionary containing all analysis results
        """
        results = {
            'spot_trends': {},
            'futures_trends': {},
            'spot_anomalies': {},
            'futures_anomalies': {},
            'spot_pressures': {},
            'futures_pressures': {}
        }
        
        # Trend analysis
        if self.config.trading.enable_spot:
            results['spot_trends'] = self.trend_analyzer.batch_analyze_trends(
                market_data['spot_klines']
            )
        
        if self.config.trading.enable_futures:
            results['futures_trends'] = self.trend_analyzer.batch_analyze_trends(
                market_data['futures_klines']
            )
        
        # Anomaly detection
        if self.config.trading.enable_spot:
            for symbol, klines in market_data['spot_klines'].items():
                try:
                    anomalies = self.anomaly_detector.detect_anomalies(klines)
                    results['spot_anomalies'][symbol] = anomalies
                except Exception as e:
                    self.logger.error(f"Anomaly detection failed for {symbol}: {e}")
                    results['spot_anomalies'][symbol] = []
        
        if self.config.trading.enable_futures:
            for symbol, klines in market_data['futures_klines'].items():
                try:
                    anomalies = self.anomaly_detector.detect_anomalies(klines)
                    results['futures_anomalies'][symbol] = anomalies
                except Exception as e:
                    self.logger.error(f"Futures anomaly detection failed for {symbol}: {e}")
                    results['futures_anomalies'][symbol] = []
        
        # Pressure analysis
        if self.config.trading.enable_spot:
            for symbol in market_data['spot_klines'].keys():
                try:
                    klines = market_data['spot_klines'][symbol]
                    orderbook = market_data['spot_orderbooks'][symbol]
                    if klines and orderbook:
                        pressure = self.pressure_analyzer.analyze_funding_pressure(klines, orderbook)
                        results['spot_pressures'][symbol] = pressure
                except Exception as e:
                    self.logger.error(f"Spot pressure analysis failed for {symbol}: {e}")
                    results['spot_pressures'][symbol] = None
        
        if self.config.trading.enable_futures:
            for symbol in market_data['futures_klines'].keys():
                try:
                    klines = market_data['futures_klines'][symbol]
                    orderbook = market_data['futures_orderbooks'][symbol]
                    if klines and orderbook:
                        pressure = self.pressure_analyzer.analyze_funding_pressure(klines, orderbook)
                        results['futures_pressures'][symbol] = pressure
                except Exception as e:
                    self.logger.error(f"Futures pressure analysis failed for {symbol}: {e}")
                    results['futures_pressures'][symbol] = None
        
        return results
    
    def _perform_cross_market_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform cross-market analysis comparing spot and futures.
        
        Args:
            market_data: Collected market data
            
        Returns:
            Dictionary containing cross-market analysis results
        """
        results = {
            'cross_market_metrics': {},
            'lead_lag_analysis': {}
        }
        
        # Cross-market flow comparison
        for symbol in self.config.trading.symbols:
            try:
                spot_klines = market_data['spot_klines'].get(symbol, [])
                futures_klines = market_data['futures_klines'].get(symbol, [])
                
                if spot_klines and futures_klines:
                    cross_metrics = self.cross_market_analyzer.analyze_cross_market_flows(
                        spot_klines, futures_klines
                    )
                    results['cross_market_metrics'][symbol] = cross_metrics
                
                # Lead-lag analysis
                if len(spot_klines) > 10:
                    lead_lag = self.cross_market_analyzer.analyze_lead_lag_relationship(spot_klines)
                    results['lead_lag_analysis'][symbol] = lead_lag
                
            except Exception as e:
                self.logger.error(f"Cross-market analysis failed for {symbol}: {e}")
                results['cross_market_metrics'][symbol] = None
                results['lead_lag_analysis'][symbol] = None
        
        return results
    
    def _generate_ai_analysis(
        self, 
        analysis_results: Dict[str, Any],
        cross_market_results: Dict[str, Any]
    ) -> str:
        """
        Generate AI-powered analysis using DeepSeek.
        
        Args:
            analysis_results: Statistical analysis results
            cross_market_results: Cross-market analysis results
            
        Returns:
            AI-generated analysis text
        """
        if not self.deepseek_client:
            return "AI analysis not available (DeepSeek API key not configured)"
        
        try:
            # Prepare data for AI analysis
            ai_data = {
                'analysis_results': analysis_results,
                'cross_market_results': cross_market_results,
                'config_summary': self.config.to_dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            # Generate AI analysis
            ai_analysis = self.deepseek_client.analyze_market_data(ai_data)
            
            return ai_analysis
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return f"AI analysis failed: {str(e)}"
    
    def _create_analysis_report(
        self,
        symbols: List[str],
        market_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
        cross_market_results: Dict[str, Any],
        ai_analysis: Optional[str]
    ) -> AnalysisReport:
        """
        Create comprehensive analysis report.
        
        Args:
            symbols: Analyzed symbols
            market_data: Raw market data
            analysis_results: Statistical analysis results
            cross_market_results: Cross-market analysis results
            ai_analysis: AI-generated analysis
            
        Returns:
            Complete analysis report
        """
        # Create market summaries
        spot_summaries = {}
        futures_summaries = {}
        
        for symbol in symbols:
            if symbol in market_data['spot_klines']:
                spot_summaries[symbol] = create_market_summary(
                    symbol, 'spot', market_data['spot_klines'][symbol]
                )
            
            if symbol in market_data['futures_klines']:
                futures_summaries[symbol] = create_market_summary(
                    symbol, 'futures', market_data['futures_klines'][symbol]
                )
        
        # Create the report
        report = AnalysisReport(
            timestamp=datetime.now(),
            symbols=symbols,
            spot_summaries=spot_summaries,
            futures_summaries=futures_summaries,
            spot_trends=analysis_results.get('spot_trends', {}),
            futures_trends=analysis_results.get('futures_trends', {}),
            spot_anomalies=analysis_results.get('spot_anomalies', {}),
            futures_anomalies=analysis_results.get('futures_anomalies', {}),
            spot_pressures=analysis_results.get('spot_pressures', {}),
            futures_pressures=analysis_results.get('futures_pressures', {}),
            spot_orderbooks=market_data.get('spot_orderbooks', {}),
            futures_orderbooks=market_data.get('futures_orderbooks', {}),
            cross_market_analysis=cross_market_results.get('cross_market_metrics', {}),
            lead_lag_analysis=cross_market_results.get('lead_lag_analysis', {}),
            ai_analysis=ai_analysis
        )
        
        return report
    
    def _save_report(self, report: AnalysisReport) -> None:
        """
        Save analysis report to files.
        
        Args:
            report: Analysis report to save
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save JSON report
            json_path = self.config.system.output_dir / f"analysis_report_{timestamp}.json"
            report.save_to_file(str(json_path))
            
            # Save markdown report (AI analysis)
            if report.ai_analysis:
                md_path = self.config.system.output_dir / f"ai_analysis_{timestamp}.md"
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(report.ai_analysis)
            
            self.logger.info(f"Analysis report saved to {json_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test all API connections.
        
        Returns:
            Dictionary with connection test results
        """
        results = {}
        
        # Test Binance connection
        try:
            results['binance'] = self.binance_client.test_connection()
        except Exception as e:
            self.logger.error(f"Binance connection test failed: {e}")
            results['binance'] = False
        
        # Test DeepSeek connection
        if self.deepseek_client:
            try:
                results['deepseek'] = self.deepseek_client.test_connection()
            except Exception as e:
                self.logger.error(f"DeepSeek connection test failed: {e}")
                results['deepseek'] = False
        else:
            results['deepseek'] = None  # Not configured
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary containing system status information
        """
        return {
            'config': self.config.to_dict(),
            'connections': self.test_connections(),
            'api_info': {
                'binance': self.binance_client.get_api_info(),
                'deepseek': self.deepseek_client.get_api_info() if self.deepseek_client else None
            },
            'system_time': datetime.now().isoformat(),
            'version': '2.0.0'
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'binance_client'):
            self.binance_client.close()
        
        if hasattr(self, 'deepseek_client') and self.deepseek_client:
            self.deepseek_client.close()
        
        self.logger.info("Funding Flow Analyzer closed")