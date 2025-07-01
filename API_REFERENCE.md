# API Reference - Binance Funding Flow Analyzer

## Table of Contents
- [Utility Functions](#utility-functions)
- [Data Collection Functions](#data-collection-functions)
- [Analysis Functions](#analysis-functions)
- [AI Integration Functions](#ai-integration-functions)
- [Caching Functions](#caching-functions)
- [Constants and Configuration](#constants-and-configuration)

---

## Utility Functions

### `format_number(value)`

Formats numerical values for human-readable display using K/M notation.

**Parameters:**
- `value` (float): Numerical value to format

**Returns:**
- `str`: Formatted string with K/M suffix

**Examples:**
```python
format_number(1500)      # Returns: "1.50K"
format_number(2500000)   # Returns: "2.50M"
format_number(50.25)     # Returns: "50.25"
```

---

## Data Collection Functions

### `get_klines_data(symbol, interval='5m', limit=50, is_futures=False)`

Retrieves candlestick (K-line) data from Binance API with comprehensive market metrics.

**Parameters:**
- `symbol` (str): Trading pair symbol (e.g., 'BTCUSDT')
- `interval` (str, optional): Time interval for candlesticks. Default: '5m'
  - Valid values: '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
- `limit` (int, optional): Number of candlesticks to retrieve. Default: 50
  - Maximum: 1000
- `is_futures` (bool, optional): Whether to fetch from futures market. Default: False

**Returns:**
- `List[Dict]`: List of candlestick dictionaries, each containing:
  ```python
  {
      'symbol': str,                    # Trading pair symbol
      'open_time': str,                 # Opening time (YYYY-MM-DD HH:MM:SS)
      'close_time': str,                # Closing time (YYYY-MM-DD HH:MM:SS)
      'open': float,                    # Opening price
      'high': float,                    # Highest price
      'low': float,                     # Lowest price
      'close': float,                   # Closing price
      'volume': float,                  # Base asset volume
      'quote_volume': float,            # Quote asset volume
      'trades': int,                    # Number of trades
      'taker_buy_base_volume': float,   # Taker buy base asset volume
      'taker_buy_quote_volume': float,  # Taker buy quote asset volume
      'net_inflow': float,              # Calculated net capital inflow
      'timestamp': int                  # Unix timestamp in milliseconds
  }
  ```

**Rate Limiting:**
- Decorated with `@sleep_and_retry` and `@limits(calls=20, period=1)`
- Automatically handles rate limiting with exponential backoff

**Error Handling:**
- Returns empty list on API errors
- Logs warnings for insufficient data
- Automatically excludes incomplete (latest) candlestick

**Examples:**
```python
# Get 50 5-minute candles for BTC spot market
btc_spot = get_klines_data('BTCUSDT', '5m', 50, False)

# Get 100 1-hour candles for ETH futures market
eth_futures = get_klines_data('ETHUSDT', '1h', 100, True)
```

### `get_orderbook_stats(symbol, is_futures=False, retries=3)`

Analyzes order book depth and calculates comprehensive market pressure metrics.

**Parameters:**
- `symbol` (str): Trading pair symbol
- `is_futures` (bool, optional): Whether to query futures market. Default: False
- `retries` (int, optional): Number of retry attempts on failure. Default: 3

**Returns:**
- `Dict` or `None`: Order book statistics dictionary:
  ```python
  {
      'symbol': str,                      # Trading pair symbol
      'price': float,                     # Current market price
      'bids_count': int,                  # Number of bid levels
      'asks_count': int,                  # Number of ask levels
      'bids_volume': float,               # Total bid volume
      'asks_volume': float,               # Total ask volume
      'bids_value': float,                # Total bid value (price × volume)
      'asks_value': float,                # Total ask value (price × volume)
      'volume_imbalance': float,          # Volume-based buy/sell imbalance (-1 to 1)
      'value_imbalance': float,           # Value-based buy/sell imbalance (-1 to 1)
      'near_volume_imbalance': float      # Imbalance within 0.5% of current price
  }
  ```

**Depth Levels:**
- **Spot Market**: 5000 levels
- **Futures Market**: 1000 levels

**Imbalance Calculations:**
```python
volume_imbalance = (bids_volume - asks_volume) / (bids_volume + asks_volume)
value_imbalance = (bids_value - asks_value) / (bids_value + asks_value)
```

**Rate Limiting:**
- Same rate limiting as `get_klines_data`

**Examples:**
```python
# Get spot order book statistics
btc_spot_book = get_orderbook_stats('BTCUSDT', False)

# Get futures order book with custom retry count
eth_futures_book = get_orderbook_stats('ETHUSDT', True, retries=5)
```

---

## Analysis Functions

### `analyze_funding_flow_trend(klines_data)`

Performs comprehensive trend analysis using statistical methods to determine market stage and confidence levels.

**Parameters:**
- `klines_data` (List[Dict]): List of candlestick data from `get_klines_data()`

**Returns:**
- `Dict`: Comprehensive trend analysis results:
  ```python
  {
      'trend': str,              # Market stage: 'top', 'bottom', 'rising', 'falling', 'consolidation', etc.
      'confidence': float,       # Confidence level (0.0 to 1.0)
      'description': str,        # Human-readable description
      'reasons': List[str],      # List of analytical reasoning
      'metrics': {
          'price_trend': float,              # Price trend ratio (0 to 1)
          'price_trend_direction': str,      # 'up' or 'down'
          'price_trend_strength': float,     # R-squared from linear regression
          'price_trend_p_value': float,      # Statistical significance
          'inflow_trend': float,             # Capital inflow trend ratio
          'inflow_trend_direction': str,     # 'increasing' or 'decreasing'
          'inflow_trend_strength': float,    # R-squared from linear regression
          'inflow_trend_p_value': float,     # Statistical significance
          'correlation': float,              # Price vs. inflow correlation (-1 to 1)
          'inflow_volume_correlation': float,# Inflow vs. volume correlation
          'price_volatility': float,         # Normalized price volatility
          'recent_inflow_trend': float       # Recent 10-period inflow trend
      }
  }
  ```

**Statistical Methods:**
1. **Linear Regression**: Analyzes price and inflow trends over time
2. **Correlation Analysis**: Measures relationships between variables
3. **Volatility Analysis**: Calculates normalized price volatility
4. **Trend Classification**: Categorizes market stages based on multiple criteria

**Market Stage Classifications:**
- **top**: High price trend + Low inflow trend + Negative correlation
- **bottom**: Low price trend + High inflow trend + Negative correlation
- **rising**: High price trend + High inflow trend + Positive correlation
- **falling**: Low price trend + Low inflow trend + Positive correlation
- **consolidation**: Balanced trends + Low volatility

**Minimum Data Requirements:**
- At least 10 candlesticks for analysis
- Returns 'unknown' trend with 0 confidence if insufficient data

**Examples:**
```python
# Analyze trend for BTC data
btc_data = get_klines_data('BTCUSDT')
trend_analysis = analyze_funding_flow_trend(btc_data)

print(f"Market Stage: {trend_analysis['trend']}")
print(f"Confidence: {trend_analysis['confidence']:.2f}")
```

### `detect_anomalies(klines_data)`

Identifies unusual market behavior using statistical outlier detection methods.

**Parameters:**
- `klines_data` (List[Dict]): List of candlestick data

**Returns:**
- `List[Dict]`: List of detected anomalies:
  ```python
  [
      {
          'timestamp': str,           # Time of anomaly
          'type': str,               # Anomaly type
          'symbol': str,             # Trading pair
          'volume': float,           # Trade volume during anomaly
          'price_change': float,     # Price change percentage
          'net_inflow': float,       # Net capital flow
          # Additional fields depending on anomaly type
      }
  ]
  ```

**Anomaly Types:**
1. **high_volume_low_price_change**: 
   - High volume (>2σ above mean) + Low price change (<0.5σ above mean)
   - Suggests accumulation/distribution

2. **high_price_change_low_volume**:
   - High price change (>2σ above mean) + Low volume (<0.5σ above mean)
   - Suggests potential manipulation or thin market

3. **extreme_net_inflow**:
   - Net inflow >70% of total volume
   - Additional field: `inflow_ratio`

4. **extreme_net_outflow**:
   - Net outflow >70% of total volume
   - Additional field: `outflow_ratio`

**Statistical Method:**
- Z-score analysis using 2 standard deviation thresholds
- Requires minimum 5 candlesticks for meaningful analysis

**Examples:**
```python
# Detect anomalies in trading data
anomalies = detect_anomalies(btc_data)

for anomaly in anomalies:
    print(f"Anomaly: {anomaly['type']} at {anomaly['timestamp']}")
```

### `analyze_funding_pressure(klines_data, orderbook)`

Combines historical capital flow data with current order book depth to assess market pressure.

**Parameters:**
- `klines_data` (List[Dict]): Historical candlestick data
- `orderbook` (Dict): Order book statistics from `get_orderbook_stats()`

**Returns:**
- `Dict`: Funding pressure analysis:
  ```python
  {
      'pressure': str,           # 'buying', 'selling', or 'balanced'
      'direction': str,          # 'bullish', 'bearish', or 'neutral'
      'strength': float,         # Pressure strength (0.0 to 1.0)
      'metrics': {
          'avg_inflow_ratio': float,        # Average inflow/volume ratio
          'volume_imbalance': float,        # Order book volume imbalance
          'value_imbalance': float,         # Order book value imbalance
          'near_volume_imbalance': float,   # Near-price volume imbalance
          'pressure_score': float           # Composite pressure score
      }
  }
  ```

**Pressure Score Calculation:**
```python
pressure_score = (
    avg_inflow_ratio * 0.4 +          # 40% weight on historical flow
    volume_imbalance * 0.2 +          # 20% weight on volume imbalance
    value_imbalance * 0.2 +           # 20% weight on value imbalance
    near_volume_imbalance * 0.2       # 20% weight on near-price imbalance
)
```

**Classification Thresholds:**
- **Buying Pressure**: score > 0.1 (Bullish)
- **Selling Pressure**: score < -0.1 (Bearish)
- **Balanced**: -0.1 ≤ score ≤ 0.1 (Neutral)

**Examples:**
```python
# Analyze funding pressure
orderbook = get_orderbook_stats('BTCUSDT')
pressure = analyze_funding_pressure(btc_data, orderbook)

print(f"Pressure: {pressure['pressure']} ({pressure['strength']:.2f})")
```

---

## AI Integration Functions

### `send_to_deepseek(data)`

Sends comprehensive market data to DeepSeek AI API for professional trading analysis.

**Parameters:**
- `data` (Dict): Structured market analysis data containing:
  - K-line summaries for spot and futures
  - Trend analysis results
  - Anomaly detection results
  - Funding pressure analysis
  - Order book statistics
  - Cross-market comparisons
  - Lead-lag relationship analysis

**Returns:**
- `str`: AI-generated professional market analysis in markdown format

**API Configuration:**
- **Model**: `deepseek-chat`
- **Max Tokens**: 2000
- **Temperature**: 0.7 (balanced creativity/consistency)

**Analysis Prompt Structure:**
The function sends a comprehensive prompt requesting:
1. **主力资金行为解读** (Main Capital Behavior Analysis)
2. **价格阶段判断** (Price Stage Assessment)
3. **短期趋势预判** (Short-term Trend Prediction)
4. **交易策略建议** (Trading Strategy Recommendations)

**Error Handling:**
- Returns error message on API failures
- Logs detailed error information

**Examples:**
```python
# Prepare data for AI analysis
analysis_data = {
    'spot_trend_analysis': trend_results,
    'futures_trend_analysis': futures_results,
    # ... other analysis results
}

# Get AI analysis
ai_analysis = send_to_deepseek(analysis_data)
```

---

## Caching Functions

### `cache_data(data, filename)`

Saves analysis data to disk using pickle serialization.

**Parameters:**
- `data` (Any): Data object to cache
- `filename` (str): Output filename

**Examples:**
```python
cache_data(analysis_results, 'latest_analysis.pkl')
```

### `load_cached_data(filename)`

Loads previously cached analysis data.

**Parameters:**
- `filename` (str): Cache filename

**Returns:**
- Cached data object or `None` if file not found

**Examples:**
```python
cached_results = load_cached_data('latest_analysis.pkl')
if cached_results:
    print("Using cached data")
```

---

## Constants and Configuration

### Global Constants

```python
# API Endpoints
SPOT_BASE_URL = "https://api.binance.com/api/v3"
FUTURES_BASE_URL = "https://fapi.binance.com/fapi/v1"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Rate Limiting
RATE_LIMIT_CALLS = 20  # Calls per second
RATE_LIMIT_PERIOD = 1  # Second

# Analysis Parameters
DEFAULT_INTERVAL = '5m'
DEFAULT_LIMIT = 50
PRICE_RANGE_PCT = 0.005  # 0.5% for near-price analysis
ANOMALY_THRESHOLD = 2.0  # Standard deviations
EXTREME_FLOW_THRESHOLD = 0.7  # 70% of volume
```

### Configuration Variables

```python
# Trading Pairs (configurable)
SYMBOLS = ['BTCUSDT', 'ETHUSDT']

# API Keys (set via environment variables)
BINANCE_API_KEY = ""     # Set your Binance API key
BINANCE_API_SECRET = ""  # Set your Binance API secret
DEEPSEEK_API_KEY = ""    # Set your DeepSeek API key
```

### Logging Configuration

```python
# Logging setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

---

## Usage Examples

### Complete Analysis Workflow

```python
# Run full analysis
def run_analysis():
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    for symbol in symbols:
        # Collect data
        spot_data = get_klines_data(symbol, '5m', 50, False)
        futures_data = get_klines_data(symbol, '5m', 50, True)
        orderbook = get_orderbook_stats(symbol, False)
        
        # Analyze
        trend = analyze_funding_flow_trend(spot_data)
        anomalies = detect_anomalies(spot_data)
        pressure = analyze_funding_pressure(spot_data, orderbook)
        
        # Output results
        print(f"{symbol} Analysis:")
        print(f"Trend: {trend['trend']} (confidence: {trend['confidence']:.2f})")
        print(f"Anomalies: {len(anomalies)} detected")
        print(f"Pressure: {pressure['pressure']} ({pressure['strength']:.2f})")
```

---

*This API reference provides detailed information about all functions and their usage. For implementation examples, see the main application file.*