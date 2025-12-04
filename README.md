# Ross Cameron Day Trading Strategy

A complete algorithmic day trading system implementing Ross Cameron's momentum and pullback trading strategy with Interactive Brokers API integration.

## 📋 Overview

This repository contains a fully automated day trading system that implements Ross Cameron's proven pullback strategy. The system is designed for paper and live trading through Interactive Brokers TWS/Gateway with comprehensive backtesting capabilities.

### Strategy Summary

**Entry Conditions (ALL must be met):**
- **Pullback Pattern**: Surge → pullback → first candle making new high after dip
- **MACD Positive**: MACD line above signal line with positive histogram (12/26/9)
- **Volume Confirmation**: No volume topping, less than 4/5 red candles during pullback
- **VWAP Filter**: Price must be above session VWAP (calculated from 9:30 AM)
- **Minimum Requirements**: 2%+ surge, 0.3-5% pullback, 1.5x relative volume

**Exit Conditions:**
- **Dynamic Exit**: Candle Under Candle reversal (latest bar low < previous bar low)
- **Stop Loss**: Structural stop at pullback low OR recent high (if >10% breakout), 1% buffer
- **Profit Target**: +20% from entry price
- **End of Day**: Close all positions at 3:50 PM EST

## 🗂️ Core Files

### 1. `RossCameron-Strategy.py`
**Shared strategy logic module** - Contains all entry/exit conditions, indicators, and position sizing logic.

- ✅ **Used by both live trading and backtesting**
- ✅ **Single source of truth** - modify once, applies everywhere
- ✅ **Configurable parameters** via `StrategyConfig` class
- ✅ **Indicators**: MACD, VWAP, volume analysis
- ✅ **Pattern detection**: Pullback and breakout identification

### 2. `RossCameron-Algo.py`
**Live trading engine** - Automated trading bot for paper/live trading.

**Features:**
- Real-time multi-symbol scanning (up to 3 stocks simultaneously)
- 10-second bars for fast pattern/MACD/volume analysis
- 1-minute bars for VWAP calculation
- Pre-market trading support (limit orders only)
- Regular hours bracket orders (entry + stop loss + profit target)
- Real-time monitoring dashboard with clean table visualization
- Paper trading via Interactive Brokers API (port 7497)

**Configuration:**
```python
port = 7497  # Paper trading
clientId = 3
symbols = ["AAPL", "TSLA", "NVDA"]  # Modify as needed
```

### 3. `RossCameron-Backtest.py`
**Backtesting engine** - Historical performance testing with comprehensive metrics.

**Features:**
- Fetches historical data from Interactive Brokers
- Simulates realistic trading with commissions and slippage
- Supports 10-second and 1-minute bar analysis
- Detailed performance metrics:
  - Win rate, profit factor, Sharpe ratio
  - Max drawdown, average win/loss
  - Commission tracking
  - Trade-by-trade breakdown

**Usage:**
```python
# Configure test parameters
symbol = "AAPL"
start_date = "2024-11-25"
end_date = "2024-11-25"
```

## 🚀 Quick Start

### Prerequisites

1. **Interactive Brokers Account**
   - Paper trading account recommended for testing
   - TWS or IB Gateway installed and running

2. **Python Environment**
   ```bash
   pip install numpy pandas pytz ibapi
   ```

3. **TWS/Gateway Configuration**
   - Enable API connections in settings
   - Configure port 7497 (paper) or 7496 (live)
   - Enable socket port connections

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ross-cameron-trading-strategy.git
   cd ross-cameron-trading-strategy
   ```

2. Ensure TWS/Gateway is running and API is enabled

3. Configure your symbols in the algo file (optional)

### Running Live Trading

```bash
python RossCameron-Algo.py
```

**What happens:**
- Connects to TWS/Gateway on port 7497
- Scans specified symbols for entry conditions
- Places trades when all conditions met
- Monitors positions with dynamic exits
- Displays real-time dashboard

### Running Backtests

```bash
python RossCameron-Backtest.py
```

**Customize test:**
- Edit symbol, start_date, end_date in script
- Run on single trading day for 10-second bars
- Review performance metrics and trade log

## ⚙️ Strategy Configuration

All strategy parameters are in `RossCameron-Strategy.py` → `StrategyConfig` class:

```python
class StrategyConfig:
    # MACD Parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Pattern Detection
    MIN_SURGE_PCT = 2.0              # Minimum surge to qualify
    MIN_PULLBACK_PCT = 0.3           # Minimum pullback required
    MAX_PULLBACK_PCT = 5.0           # Maximum pullback allowed
    
    # Volume Requirements
    MIN_RELATIVE_VOLUME = 1.5        # 1.5x average volume required
    MAX_RED_CANDLES_IN_PULLBACK = 4  # Max red candles in pullback
    
    # Position Sizing
    SIMULATED_ACCOUNT_SIZE = 500.0   # Simulate small account
    TRADE_SIZE_DOLLARS = 100.0       # $100 per trade
    
    # Profit/Loss
    PROFIT_TARGET_PCT = 0.2          # 20% profit target
    
    # Trading Hours (EST)
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 30
    END_OF_DAY_HOUR = 15
    END_OF_DAY_MINUTE = 50
```

**To modify strategy behavior:**
1. Edit parameters in `StrategyConfig` class
2. Changes automatically apply to both live trading and backtesting
3. No need to modify algo or backtest files

## 📊 Performance Metrics

The backtest engine provides comprehensive performance analysis:

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Win/Loss**: Mean profit and loss per trade
- **Commission Impact**: Total fees and their effect on P&L
- **Trade Log**: Detailed entry/exit prices, dates, and outcomes

## 🎯 Risk Management

**Position Sizing:**
- Fixed $100 per trade (configurable)
- Simulates $500 account (5 trades max per day)
- Can adjust to use actual account balance

**Stop Loss:**
- Structural stops at pullback low
- Tighter stops for strong breakouts (>10% above recent high)
- Minimum 2% distance from entry
- 1% buffer below support level

**Profit Target:**
- 20% from entry (3:1 reward/risk typical)
- Automatically cancelled if dynamic exit triggers

**Daily Limits:**
- All positions closed at 3:50 PM EST
- Maximum 3 concurrent positions (configurable)

## 🛠️ Troubleshooting

### Connection Issues
- Verify TWS/Gateway is running
- Check API is enabled in TWS settings
- Confirm correct port (7497 paper, 7496 live)
- Ensure unique `clientId` per script

### Data Issues
- 10-second bars: Maximum 1 trading day per request
- 1-minute bars: Can fetch multiple days
- Use liquid stocks (AAPL, TSLA, NVDA) for testing
- Verify date is a weekday when market was open

### Strategy Issues
- Check all entry conditions in console output
- Review pattern detection messages
- Verify VWAP calculation has enough bars
- Confirm volume data is available

## 📈 Example Performance

**Sample backtest results (AAPL, single day):**
```
Total Trades: 3
Win Rate: 66.7%
Profit Factor: 2.1
Average Win: $18.50
Average Loss: -$8.20
Total P&L: $28.60
Max Drawdown: -$8.20
```

*Note: Past performance does not guarantee future results. Always paper trade thoroughly before risking real capital.*

## 🔒 Safety Features

- **Paper Trading Default**: Port 7497 configured by default
- **Position Limits**: Maximum 3 concurrent positions
- **End-of-Day Exit**: Automatic close at 3:50 PM
- **Error Handling**: Comprehensive error checking and logging
- **Order Validation**: Stop loss validation, minimum distance checks

## 📝 License

This project is for educational purposes. Use at your own risk. No guarantees or warranties provided.

## ⚠️ Disclaimer

**IMPORTANT:** This software is provided for educational and research purposes only. 

- Trading involves substantial risk of loss
- Past performance is not indicative of future results
- Always test thoroughly in paper trading before live trading
- Never trade with money you cannot afford to lose
- The author is not responsible for any trading losses
- Consult with a licensed financial advisor before trading

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📧 Support

For questions or issues:
1. Check the troubleshooting section
2. Review code comments and docstrings
3. Open an issue on GitHub

## 🎓 Learn More

**Ross Cameron Resources:**
- [Warrior Trading](https://www.warriortrading.com/)
- Ross Cameron's YouTube channel
- Day Trading courses and community

**Technical Analysis:**
- MACD indicator (12/26/9 settings)
- VWAP calculation and usage
- Volume analysis techniques
- Candlestick pattern recognition

---

**Happy Trading! 📈**

*Remember: The best trader is the one who survives to trade another day. Always use proper risk management.*
