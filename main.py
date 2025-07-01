#!/usr/bin/env python3
"""
Binance Funding Flow Analyzer - Main Entry Point

A sophisticated cryptocurrency market analysis tool that examines capital flow patterns,
order book dynamics, and price relationships across Binance spot and futures markets.

Usage:
    python main.py --help
    python main.py run
    python main.py test-connections
    python main.py status
"""

import argparse
import sys
import os
from pathlib import Path
import json
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import FundingFlowAnalyzer, Config
from src.exceptions import AnalyzerError


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Binance Funding Flow Analyzer - Professional Market Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                           # Run complete analysis
  %(prog)s run --symbols BTCUSDT ETHUSDT # Analyze specific symbols
  %(prog)s run --no-ai                   # Skip AI analysis
  %(prog)s test-connections               # Test API connections
  %(prog)s status                         # Show system status
  %(prog)s run --config custom.env       # Use custom config file

Environment Variables:
  BINANCE_API_KEY        - Binance API key
  BINANCE_API_SECRET     - Binance API secret
  DEEPSEEK_API_KEY       - DeepSeek AI API key
  TRADING_SYMBOLS        - Comma-separated symbols (default: BTCUSDT,ETHUSDT)
  LOG_LEVEL              - Logging level (default: INFO)
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run analysis command
    run_parser = subparsers.add_parser(
        'run', 
        help='Run complete market analysis'
    )
    run_parser.add_argument(
        '--symbols', 
        nargs='+', 
        help='Trading symbols to analyze (e.g., BTCUSDT ETHUSDT)'
    )
    run_parser.add_argument(
        '--no-ai', 
        action='store_true',
        help='Skip AI analysis to save API costs'
    )
    run_parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save report to file'
    )
    run_parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for reports'
    )
    
    # Test connections command
    test_parser = subparsers.add_parser(
        'test-connections',
        help='Test all API connections'
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show system status and configuration'
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Show current configuration'
    )
    config_parser.add_argument(
        '--format',
        choices=['json', 'yaml', 'table'],
        default='table',
        help='Output format for configuration'
    )
    
    # Global options
    parser.add_argument(
        '--config-file',
        type=str,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Binance Funding Flow Analyzer 2.0.0'
    )
    
    return parser


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from file or environment."""
    try:
        if config_file and Path(config_file).exists():
            # Load from custom config file
            # This would need implementation for file-based config
            print(f"Loading configuration from {config_file}")
        
        config = Config(config_file)
        return config
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def validate_environment() -> bool:
    """Validate that required environment variables are set."""
    required_vars = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the analyzer.")
        print("See SETUP_GUIDE.md for detailed instructions.")
        return False
    
    return True


def run_analysis(args, config: Config) -> int:
    """Run the complete market analysis."""
    try:
        # Override config with command line arguments
        if args.symbols:
            config.trading.symbols = args.symbols
        
        if args.output_dir:
            config.system.output_dir = Path(args.output_dir)
        
        print("🚀 Starting Binance Funding Flow Analysis...")
        print(f"📊 Analyzing symbols: {', '.join(config.trading.symbols)}")
        
        with FundingFlowAnalyzer(config) as analyzer:
            # Run the analysis
            report = analyzer.run_complete_analysis(
                symbols=config.trading.symbols,
                include_ai_analysis=not args.no_ai,
                save_report=not args.no_save
            )
            
            # Print summary
            print("\n✅ Analysis completed successfully!")
            print(f"📈 Analyzed {len(report.symbols)} symbols")
            
            # Print brief summary of findings
            print("\n📋 Summary:")
            for symbol in report.symbols:
                spot_trend = report.spot_trends.get(symbol)
                if spot_trend:
                    print(f"   {symbol}: {spot_trend.trend} (confidence: {spot_trend.confidence:.2f})")
                
                anomalies = report.spot_anomalies.get(symbol, [])
                if anomalies:
                    print(f"      🚨 {len(anomalies)} anomalies detected")
            
            if report.ai_analysis and not args.no_ai:
                print(f"\n🤖 AI Analysis: {len(report.ai_analysis)} characters generated")
            
            if not args.no_save:
                print(f"💾 Reports saved to: {config.system.output_dir}")
        
        return 0
        
    except AnalyzerError as e:
        print(f"❌ Analysis failed: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


def test_connections(config: Config) -> int:
    """Test all API connections."""
    try:
        print("🔌 Testing API connections...")
        
        with FundingFlowAnalyzer(config) as analyzer:
            results = analyzer.test_connections()
            
            print("\n📊 Connection Test Results:")
            for api, status in results.items():
                if status is True:
                    print(f"   ✅ {api.title()}: Connected")
                elif status is False:
                    print(f"   ❌ {api.title()}: Failed")
                elif status is None:
                    print(f"   ⚪ {api.title()}: Not configured")
            
            # Overall status
            if all(status for status in results.values() if status is not None):
                print("\n🎉 All configured APIs are working!")
                return 0
            else:
                print("\n⚠️  Some APIs are not working. Check your configuration.")
                return 1
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return 1


def show_status(config: Config) -> int:
    """Show system status and configuration."""
    try:
        print("📊 System Status")
        print("=" * 50)
        
        with FundingFlowAnalyzer(config) as analyzer:
            status = analyzer.get_system_status()
            
            # Connection status
            print("\n🔌 API Connections:")
            connections = status['connections']
            for api, connected in connections.items():
                if connected is True:
                    print(f"   ✅ {api.title()}: Connected")
                elif connected is False:
                    print(f"   ❌ {api.title()}: Failed")
                else:
                    print(f"   ⚪ {api.title()}: Not configured")
            
            # Configuration summary
            print("\n⚙️  Configuration:")
            print(f"   Symbols: {', '.join(config.trading.symbols)}")
            print(f"   Interval: {config.analysis.default_interval}")
            print(f"   Data points: {config.analysis.default_limit}")
            print(f"   Spot enabled: {config.trading.enable_spot}")
            print(f"   Futures enabled: {config.trading.enable_futures}")
            print(f"   AI analysis: {'Yes' if config.api.deepseek_api_key else 'No'}")
            
            # System info
            print(f"\n🖥️  System:")
            print(f"   Version: {status['version']}")
            print(f"   Log level: {config.system.log_level}")
            print(f"   Output dir: {config.system.output_dir}")
            print(f"   Cache enabled: {config.system.cache_enabled}")
            
        return 0
        
    except Exception as e:
        print(f"❌ Failed to get system status: {e}")
        return 1


def show_config(args, config: Config) -> int:
    """Show current configuration."""
    try:
        config_dict = config.to_dict()
        
        if args.format == 'json':
            print(json.dumps(config_dict, indent=2, ensure_ascii=False))
        elif args.format == 'yaml':
            try:
                import yaml
                print(yaml.dump(config_dict, default_flow_style=False, allow_unicode=True))
            except ImportError:
                print("❌ PyYAML not installed. Use 'pip install pyyaml' or choose json format.")
                return 1
        else:  # table format
            print("⚙️  Current Configuration")
            print("=" * 50)
            
            def print_section(name: str, data: dict, indent: int = 0):
                prefix = "  " * indent
                print(f"{prefix}📁 {name}:")
                for key, value in data.items():
                    if isinstance(value, dict):
                        print_section(key, value, indent + 1)
                    else:
                        print(f"{prefix}   {key}: {value}")
                print()
            
            for section, data in config_dict.items():
                print_section(section.title(), data)
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to show configuration: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 0
    
    # Set log level from args
    if args.log_level:
        os.environ['LOG_LEVEL'] = args.log_level
    
    # Load configuration
    config = load_config(args.config_file)
    
    # Validate environment for commands that need API access
    if args.command in ['run', 'test-connections', 'status']:
        if not validate_environment():
            return 1
    
    # Route to appropriate command handler
    try:
        if args.command == 'run':
            return run_analysis(args, config)
        elif args.command == 'test-connections':
            return test_connections(config)
        elif args.command == 'status':
            return show_status(config)
        elif args.command == 'config':
            return show_config(args, config)
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())