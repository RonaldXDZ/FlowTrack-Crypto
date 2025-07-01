"""
Binance Funding Flow Analyzer - Modular Architecture

A sophisticated cryptocurrency market analysis tool that examines capital flow patterns,
order book dynamics, and price relationships across Binance spot and futures markets.
"""

__version__ = "2.0.0"
__author__ = "Binance Funding Flow Analyzer Team"

from .analyzer import FundingFlowAnalyzer
from .config import Config
from .exceptions import AnalyzerError, APIError, DataError

__all__ = [
    "FundingFlowAnalyzer",
    "Config", 
    "AnalyzerError",
    "APIError",
    "DataError"
]