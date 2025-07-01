# Setup Guide - Binance Funding Flow Analyzer

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Setup](#api-setup)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)
- [Development Setup](#development-setup)

---

## System Requirements

### Minimum Requirements
- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.7 or higher
- **Memory**: 2GB RAM (4GB recommended)
- **Storage**: 100MB free space
- **Internet**: Stable internet connection for API calls

### Recommended Specifications
- **Python**: 3.9+ for optimal performance
- **Memory**: 4GB+ RAM for handling large datasets
- **CPU**: Multi-core processor for concurrent API processing

---

## Installation

### Option 1: Quick Setup (Recommended)

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd binance-funding-flow-analyzer
   ```

2. **Create Virtual Environment**
   ```bash
   # Using venv (recommended)
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Using conda (alternative)
   conda create -n binance-analyzer python=3.9
   conda activate binance-analyzer
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Option 2: Manual Installation

If `requirements.txt` is not available, install dependencies manually:

```bash
pip install requests pandas numpy scipy python-binance python-telegram-bot ratelimit
```

#### Core Dependencies
```
requests>=2.25.1          # HTTP requests for API calls
pandas>=1.3.0             # Data manipulation and analysis
numpy>=1.21.0             # Numerical computing
scipy>=1.7.0              # Statistical analysis
python-binance>=1.0.15    # Official Binance API client
python-telegram-bot>=13.7 # Telegram integration (optional)
ratelimit>=2.2.1          # API rate limiting
```

#### Optional Dependencies
```
matplotlib>=3.3.4         # For future plotting features
jupyter>=1.0.0            # For interactive analysis
plotly>=5.0.0             # Advanced visualizations
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env
```

Add the following content to `.env`:

```env
# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_secret_key_here

# DeepSeek AI Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional: Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Application Settings
LOG_LEVEL=INFO
OUTPUT_DIR=./output
CACHE_DIR=./cache
```

### Loading Environment Variables

If using a `.env` file, install and configure python-dotenv:

```bash
pip install python-dotenv
```

Add to the beginning of your script:

```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Update configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
```

---

## API Setup

### 1. Binance API Setup

#### Creating API Keys
1. **Log in to Binance**
   - Visit [binance.com](https://www.binance.com) and log in

2. **Navigate to API Management**
   - Go to Account → API Management
   - Click "Create API"

3. **Configure API Key**
   - **Label**: Give your API key a descriptive name (e.g., "Funding Flow Analyzer")
   - **API Key**: Copy the generated API key
   - **Secret Key**: Copy the secret key (shown only once)

4. **Set Permissions**
   - ✅ **Enable Reading** (Required)
   - ❌ **Enable Spot & Margin Trading** (Not needed)
   - ❌ **Enable Futures** (Optional, only if analyzing futures)
   - ❌ **Enable Withdrawals** (Never enable for analysis tools)

5. **IP Restrictions (Recommended)**
   - Add your server's IP address for security
   - Use "Unrestricted" only for development

#### Testing API Connection
```python
from binance.client import Client

# Test connection
try:
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    account_info = client.get_account()
    print("✅ Binance API connection successful")
except Exception as e:
    print(f"❌ Binance API connection failed: {e}")
```

### 2. DeepSeek AI API Setup

#### Getting API Access
1. **Visit DeepSeek Platform**
   - Go to [platform.deepseek.com](https://platform.deepseek.com)
   - Create an account or log in

2. **Generate API Key**
   - Navigate to API Keys section
   - Click "Create new secret key"
   - Copy the generated key (store securely)

3. **Check Usage Limits**
   - Review your token limits and pricing
   - Each analysis uses approximately 1000-2000 tokens

#### Testing DeepSeek Connection
```python
import requests

def test_deepseek_connection():
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        print("✅ DeepSeek API connection successful")
    except Exception as e:
        print(f"❌ DeepSeek API connection failed: {e}")
```

---

## First Run

### Basic Execution

1. **Verify Configuration**
   ```bash
   # Check environment variables
   python -c "import os; print('Binance API Key:', bool(os.getenv('BINANCE_API_KEY')))"
   ```

2. **Run the Analyzer**
   ```bash
   python binance_funding_flow_analyzer.py
   ```

3. **Expected Output**
   ```
   2024-01-15 10:30:00 - INFO - 开始运行，当前时间: 2024-01-15 10:30:00
   2024-01-15 10:30:00 - INFO - 目标交易对: ['BTCUSDT', 'ETHUSDT']
   2024-01-15 10:30:01 - INFO - 获取 BTCUSDT 现货5分钟K线数据...
   2024-01-15 10:30:02 - INFO - 获取 BTCUSDT 期货5分钟K线数据...
   ...
   2024-01-15 10:30:15 - INFO - 分析结果已保存到 binance_analysis.md
   ```

### Customizing Analysis

#### Modify Trading Pairs
```python
# Edit the SYMBOLS list in the script
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
```

#### Adjust Analysis Parameters
```python
# Change timeframe and data points
klines_data = get_klines_data(symbol, interval='15m', limit=100)
```

#### Enable/Disable Features
```python
# Skip AI analysis to save costs
# Comment out the DeepSeek API call
# analysis = send_to_deepseek(deepseek_data)
analysis = "AI analysis disabled"
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Error**: `ModuleNotFoundError: No module named 'binance'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or conda activate binance-analyzer

# Reinstall dependencies
pip install python-binance
```

#### 2. API Connection Failures
**Error**: `Binance API connection failed: Invalid API-key`

**Solutions**:
- Verify API keys are correctly set in environment variables
- Check for extra spaces or hidden characters
- Ensure API key has "Enable Reading" permission
- Verify IP restrictions if configured

#### 3. Rate Limiting Issues
**Error**: `HTTP 429: Too Many Requests`

**Solutions**:
- Increase delay between requests
- Reduce the number of symbols analyzed
- Check if multiple instances are running

```python
# Adjust rate limiting
@limits(calls=10, period=1)  # Reduce from 20 to 10 calls per second
```

#### 4. Memory Issues
**Error**: `MemoryError` or system freezing

**Solutions**:
- Reduce data retrieval limits
- Process symbols one at a time
- Close other applications

```python
# Reduce data points
klines_data = get_klines_data(symbol, limit=20)  # Reduce from 50 to 20
```

#### 5. DeepSeek API Issues
**Error**: `DeepSeek API error: Insufficient credits`

**Solutions**:
- Check your DeepSeek account balance
- Reduce analysis frequency
- Implement caching to avoid repeated API calls

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging

# Set debug level logging
logging.basicConfig(level=logging.DEBUG)

# Add more detailed error handling
try:
    result = get_klines_data(symbol)
    print(f"✅ Successfully retrieved {len(result)} data points")
except Exception as e:
    print(f"❌ Error details: {str(e)}")
    import traceback
    traceback.print_exc()
```

### Performance Optimization

#### 1. Reduce API Calls
```python
# Cache results to avoid repeated API calls
import pickle
from datetime import datetime, timedelta

def get_cached_data(symbol, cache_duration_minutes=5):
    cache_file = f"cache_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
    
    # Check if cache exists and is recent
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    # Fetch new data and cache it
    data = get_klines_data(symbol)
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)
    
    return data
```

#### 2. Parallel Processing
```python
import concurrent.futures

def analyze_symbol(symbol):
    """Analyze a single symbol"""
    spot_data = get_klines_data(symbol, is_futures=False)
    futures_data = get_klines_data(symbol, is_futures=True)
    return symbol, spot_data, futures_data

# Process multiple symbols in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(analyze_symbol, symbol) for symbol in SYMBOLS]
    results = [future.result() for future in concurrent.futures.as_completed(futures)]
```

---

## Development Setup

### Code Style and Formatting

1. **Install Development Dependencies**
   ```bash
   pip install black flake8 mypy pytest
   ```

2. **Format Code**
   ```bash
   black binance_funding_flow_analyzer.py
   ```

3. **Lint Code**
   ```bash
   flake8 binance_funding_flow_analyzer.py
   ```

4. **Type Checking**
   ```bash
   mypy binance_funding_flow_analyzer.py
   ```

### Testing

1. **Create Test File** (`test_analyzer.py`)
   ```python
   import unittest
   from binance_funding_flow_analyzer import format_number, analyze_funding_flow_trend

   class TestAnalyzer(unittest.TestCase):
       def test_format_number(self):
           self.assertEqual(format_number(1500), "1.50K")
           self.assertEqual(format_number(2500000), "2.50M")
       
       def test_analyze_empty_data(self):
           result = analyze_funding_flow_trend([])
           self.assertEqual(result['trend'], 'unknown')
   
   if __name__ == '__main__':
       unittest.main()
   ```

2. **Run Tests**
   ```bash
   python -m pytest test_analyzer.py
   ```

### Contributing

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-analysis-method
   ```
3. **Make Changes and Test**
4. **Submit Pull Request**

---

## Security Best Practices

1. **Never Commit API Keys**
   ```bash
   # Add to .gitignore
   echo "*.env" >> .gitignore
   echo "config.py" >> .gitignore
   ```

2. **Use Environment Variables**
   - Never hardcode sensitive information
   - Use different keys for development and production

3. **Regular Key Rotation**
   - Rotate API keys periodically
   - Monitor API usage for unusual activity

4. **Minimal Permissions**
   - Only enable necessary API permissions
   - Use IP restrictions when possible

---

This setup guide should help you get the Binance Funding Flow Analyzer running smoothly. For technical details about the code structure and functions, refer to the [Technical Documentation](DOCUMENTATION.md) and [API Reference](API_REFERENCE.md).