"""
Breakout Trading Strategy - SHARED LOGIC
=========================================

This module contains the core strategy logic used by BOTH:
- Breakout-Algo.py (live trading)
- Breakout-Backtest.py (backtesting)

ANY changes to entry/exit conditions made here will automatically
apply to both live trading and backtesting.

Strategy Rules:
===============

ENTRY CONDITIONS (ALL must be met):
- Breakout Pattern: Price breaking above consolidation/resistance level with strong momentum
- MACD Positive: MACD line above signal line with increasing histogram (12/26/9)
- Volume Confirmation: Volume spike on breakout (2x+ average), high relative volume
- VWAP Filter: Price must be above session VWAP (from 9:30 AM)
- Range Breakout: Must break above recent consolidation range with momentum

EXIT CONDITIONS:
- Dynamic Exit: First red candle after entry (early exit on momentum loss)
- Stop Loss: Below consolidation range or recent support, 2% buffer, minimum 2% distance
- Profit Target: +25% from entry price (higher target for breakout momentum)
- End of Day: Close all positions at 3:50 PM EST

CONFIGURATION:
==============
Modify these parameters to change strategy behavior:
"""

import numpy as np

# ==================== STRATEGY CONFIGURATION ====================

class StrategyConfig:
    """Centralized strategy parameters - modify here to change strategy"""
    
    # MACD Parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Pattern Detection - Breakout Focus
    PATTERN_LOOKBACK_BARS = 30   # 30 minutes of 1-min bars for pattern detection
    MIN_BARS_FOR_PATTERN = 10    # Minimum bars needed for pattern analysis
    
    # Breakout Detection (different from pullback strategy)
    CONSOLIDATION_LOOKBACK = 15      # Check for consolidation in last 15 bars
    MIN_CONSOLIDATION_BARS = 5       # Minimum bars in consolidation before breakout
    MAX_CONSOLIDATION_RANGE_PCT = 3.0  # Consolidation range should be tight (max 3%)
    MIN_BREAKOUT_PCT = 1.5           # Minimum 1.5% breakout above consolidation high
    BREAKOUT_MOMENTUM_BARS = 3       # Must break out within last 3 bars
    
    # Volume Analysis - Breakout Style
    MIN_RELATIVE_VOLUME = 2.0        # Higher requirement: 2x average volume for breakout
    BREAKOUT_VOLUME_SPIKE = 2.5      # Volume spike on breakout bar (2.5x average)
    VOLUME_LOOKBACK_BARS = 10        # Bars to analyze for volume
    
    # Position Sizing
    SIMULATED_ACCOUNT_SIZE = 500.0   # Simulate $500 account
    TRADE_SIZE_DOLLARS = 100.0       # $100 per trade (allows 5 trades per day)
    
    # Commission Fees (IBKR Fixed Pricing)
    COMMISSION_PER_SHARE = 0.005     # $0.005 per share
    COMMISSION_MINIMUM = 1.00        # $1 minimum per order
    SEC_FEE_PER_DOLLAR = 0.0000278   # SEC fee on sells (~$0.0278 per $1000)
    
    # Profit/Loss Targets
    PROFIT_TARGET_PCT = 0.25         # 25% profit target (higher for breakouts)
    ENTRY_SPREAD_PCT = 0.002         # 0.2% spread simulation for entry
    
    # Trading Hours (EST)
    PREMARKET_START_HOUR = 5         # 5:00 AM
    PREMARKET_START_MINUTE = 0
    MARKET_OPEN_HOUR = 9             # 9:30 AM
    MARKET_OPEN_MINUTE = 30
    MARKET_CLOSE_HOUR = 15           # 3:50 PM
    MARKET_CLOSE_MINUTE = 50
    
    # Exit Timing (same as market close)
    END_OF_DAY_HOUR = 15             # 3 PM
    END_OF_DAY_MINUTE = 50           # 3:50 PM
    
    # VWAP Lookback
    VWAP_LOOKBACK_BARS = 390         # Session VWAP (from 9:30 AM market open)
    
    # Live Trading Data Fetching
    DATA_DURATION_10SEC = "3600 S"   # 1 hour of 10-second bars for exit monitoring
    DATA_DURATION_1MIN = "1 D"       # 1 day of 1-minute bars for pattern/VWAP
    BAR_SIZE_10SEC = "10 secs"
    BAR_SIZE_1MIN = "1 min"
    
    # Live Trading Account (uses real IBKR account balance, these are defaults)
    DEFAULT_ACCOUNT_BALANCE = 10000.0  # Default if API doesn't return balance
    MAX_CONCURRENT_POSITIONS = 3       # Maximum number of symbols to trade simultaneously


# ==================== INDICATOR CALCULATIONS ====================

def calculate_macd(closes, fast=None, slow=None, signal=None):
    """
    Calculate MACD indicator
    
    Parameters:
    - closes: List of closing prices
    - fast: Fast EMA period (default from config)
    - slow: Slow EMA period (default from config)
    - signal: Signal line period (default from config)
    
    Returns: (macd_line, signal_line, histogram) or (None, None, None)
    """
    if fast is None:
        fast = StrategyConfig.MACD_FAST
    if slow is None:
        slow = StrategyConfig.MACD_SLOW
    if signal is None:
        signal = StrategyConfig.MACD_SIGNAL
    
    if len(closes) < slow:
        return None, None, None
    
    closes_arr = np.array(closes)
    
    # Calculate EMAs
    ema_fast = np.zeros(len(closes))
    ema_slow = np.zeros(len(closes))
    
    ema_fast[0] = closes_arr[0]
    ema_slow[0] = closes_arr[0]
    
    alpha_fast = 2 / (fast + 1)
    alpha_slow = 2 / (slow + 1)
    
    for i in range(1, len(closes)):
        ema_fast[i] = closes_arr[i] * alpha_fast + ema_fast[i-1] * (1 - alpha_fast)
        ema_slow[i] = closes_arr[i] * alpha_slow + ema_slow[i-1] * (1 - alpha_slow)
    
    macd_line = ema_fast - ema_slow
    
    # Calculate signal line
    signal_line = np.zeros(len(macd_line))
    signal_line[0] = macd_line[0]
    alpha_signal = 2 / (signal + 1)
    
    for i in range(1, len(macd_line)):
        signal_line[i] = macd_line[i] * alpha_signal + signal_line[i-1] * (1 - alpha_signal)
    
    histogram = macd_line - signal_line
    
    return macd_line[-1], signal_line[-1], histogram[-1]


def calculate_vwap(bars):
    """
    Calculate VWAP (Volume Weighted Average Price)
    VWAP = Sum(Price * Volume) / Sum(Volume)
    Using typical price: (High + Low + Close) / 3
    
    Parameters:
    - bars: List of bar dictionaries with 'high', 'low', 'close', 'volume'
    
    Returns: VWAP value or None
    """
    if len(bars) < 2:
        return None
    
    total_pv = 0.0
    total_volume = 0.0
    
    for bar in bars:
        typical_price = (bar['high'] + bar['low'] + bar['close']) / 3
        pv = typical_price * bar['volume']
        total_pv += pv
        total_volume += bar['volume']
    
    if total_volume == 0:
        return None
    
    return total_pv / total_volume


# ==================== ENTRY CONDITIONS ====================

def check_macd_positive(bars):
    """
    Check if MACD is positive and increasing (strong momentum for breakout)
    
    Parameters:
    - bars: List of bar dictionaries with 'close' key
    
    Returns: (bool, str) - (condition_met, message)
    """
    if len(bars) < StrategyConfig.MIN_BARS_FOR_PATTERN + 2:
        return False, "Not enough data"
    
    closes = [bar['close'] for bar in bars]
    
    # Calculate current MACD
    macd, signal, histogram = calculate_macd(closes)
    
    if macd is None:
        return False, "MACD calculation failed"
    
    # MACD must be above signal line
    if macd <= signal:
        return False, f"MACD negative: {macd:.4f} <= {signal:.4f}"
    
    # Check histogram is positive and increasing (momentum building)
    closes_prev = closes[:-1]
    macd_prev, signal_prev, histogram_prev = calculate_macd(closes_prev)
    
    if histogram_prev is None or histogram <= histogram_prev:
        return False, f"MACD not accelerating: current={histogram:.4f}, prev={histogram_prev:.4f if histogram_prev else 'N/A'}"
    
    return True, f"MACD positive & accelerating: {macd:.4f} > {signal:.4f}, histogram {histogram_prev:.4f}→{histogram:.4f}"


def detect_breakout_pattern(bars):
    """
    Detect breakout pattern:
    1. Find consolidation range (tight price action for 5+ bars)
    2. Verify consolidation range is small (< 3%)
    3. Detect breakout: price breaking above consolidation high
    4. Breakout must be recent (within last 3 bars)
    5. Breakout bar should be strong (green candle, good volume)
    
    Parameters:
    - bars: List of bar dictionaries with 'high', 'low', 'close', 'open', 'volume'
    
    Returns: (bool, str, float, float) - (pattern_found, message, consolidation_low, consolidation_high)
    """
    if len(bars) < StrategyConfig.MIN_BARS_FOR_PATTERN:
        return False, "Not enough bars", None, None
    
    # Look at recent bars
    recent = bars[-StrategyConfig.PATTERN_LOOKBACK_BARS:] if len(bars) >= StrategyConfig.PATTERN_LOOKBACK_BARS else bars
    
    if len(recent) < 8:
        return False, "Insufficient data", None, None
    
    # STEP 1: Find consolidation range (looking back, excluding last 3 bars for breakout check)
    consolidation_end_idx = len(recent) - StrategyConfig.BREAKOUT_MOMENTUM_BARS
    consolidation_start_idx = max(0, consolidation_end_idx - StrategyConfig.CONSOLIDATION_LOOKBACK)
    
    if consolidation_end_idx - consolidation_start_idx < StrategyConfig.MIN_CONSOLIDATION_BARS:
        return False, "Not enough bars for consolidation", None, None
    
    consolidation_bars = recent[consolidation_start_idx:consolidation_end_idx]
    
    if len(consolidation_bars) < StrategyConfig.MIN_CONSOLIDATION_BARS:
        return False, "Insufficient consolidation period", None, None
    
    # Find consolidation range
    consolidation_high = max([bar['high'] for bar in consolidation_bars])
    consolidation_low = min([bar['low'] for bar in consolidation_bars])
    consolidation_range_pct = ((consolidation_high - consolidation_low) / consolidation_low) * 100
    
    # STEP 2: Verify consolidation is tight (< 3% range)
    if consolidation_range_pct > StrategyConfig.MAX_CONSOLIDATION_RANGE_PCT:
        return False, f"Consolidation too wide: {consolidation_range_pct:.2f}% (need < {StrategyConfig.MAX_CONSOLIDATION_RANGE_PCT}%)", None, None
    
    # STEP 3: Check for breakout in last 3 bars
    breakout_bars = recent[-StrategyConfig.BREAKOUT_MOMENTUM_BARS:]
    breakout_high = max([bar['high'] for bar in breakout_bars])
    
    # Must break above consolidation high
    if breakout_high <= consolidation_high:
        return False, f"No breakout: high ${breakout_high:.2f} <= consolidation ${consolidation_high:.2f}", None, None
    
    # Calculate breakout percentage
    breakout_pct = ((breakout_high - consolidation_high) / consolidation_high) * 100
    
    if breakout_pct < StrategyConfig.MIN_BREAKOUT_PCT:
        return False, f"Breakout too weak: {breakout_pct:.2f}% (need {StrategyConfig.MIN_BREAKOUT_PCT}%+)", None, None
    
    # STEP 4: Verify last bar is strong (making the breakout)
    last_bar = recent[-1]
    
    # Must be green candle
    if last_bar['close'] <= last_bar['open']:
        return False, "Last bar not green (weak momentum)", None, None
    
    # Last bar should be near the breakout high
    if last_bar['high'] < consolidation_high * 1.005:  # Within 0.5% of breakout
        return False, "Current bar retreated from breakout", None, None
    
    # Pattern confirmed!
    message = f"Breakout: consolidated ${consolidation_low:.2f}-${consolidation_high:.2f} ({consolidation_range_pct:.1f}% range), broke out +{breakout_pct:.1f}% to ${breakout_high:.2f}"
    
    return True, message, consolidation_low, consolidation_high


def check_volume_conditions(bars):
    """
    Check volume conditions for breakout:
    1. HIGH relative volume (2x+ average) - strong institutional interest
    2. Volume spike on breakout bar (2.5x+ average) - confirms breakout
    
    Parameters:
    - bars: List of bar dictionaries with 'volume'
    
    Returns: (bool, str) - (condition_met, message)
    """
    if len(bars) < 5:
        return False, "Not enough bars for volume analysis"
    
    recent = bars[-StrategyConfig.VOLUME_LOOKBACK_BARS:] if len(bars) >= StrategyConfig.VOLUME_LOOKBACK_BARS else bars
    
    if len(recent) < 3:
        return False, "Not enough bars for volume analysis"
    
    last_bar = recent[-1]
    
    # Calculate average volume of previous bars (excluding last bar)
    history_bars = recent[:-1]
    if len(history_bars) == 0:
        return False, "Not enough historical bars for volume analysis"
    
    avg_volume = sum([bar['volume'] for bar in history_bars]) / len(history_bars)
    
    # Calculate relative volume of last bar
    relative_volume = last_bar['volume'] / avg_volume if avg_volume > 0 else 0
    
    # REQUIREMENT 1: High relative volume on breakout
    if relative_volume < StrategyConfig.MIN_RELATIVE_VOLUME:
        return False, f"Low breakout volume: {relative_volume:.2f}x avg (need {StrategyConfig.MIN_RELATIVE_VOLUME}x+)"
    
    # REQUIREMENT 2: Volume spike on breakout bar (even higher requirement)
    if relative_volume < StrategyConfig.BREAKOUT_VOLUME_SPIKE:
        return False, f"No volume spike: {relative_volume:.2f}x avg (need {StrategyConfig.BREAKOUT_VOLUME_SPIKE}x+ for strong breakout)"
    
    return True, f"Strong breakout volume: {relative_volume:.2f}x avg (last: {last_bar['volume']:.0f} vs avg: {avg_volume:.0f})"


def check_above_vwap(bars, current_price):
    """
    Check if current price is above VWAP
    Only take long trades when above VWAP
    
    Parameters:
    - bars: List of bar dictionaries for VWAP calculation
    - current_price: Current price to compare
    
    Returns: (bool, str) - (condition_met, message)
    """
    vwap = calculate_vwap(bars)
    
    if vwap is None:
        return False, "VWAP calculation failed"
    
    if current_price <= vwap:
        return False, f"Price below VWAP: ${current_price:.4f} <= ${vwap:.4f} (no long entry)"
    
    pct_above = ((current_price - vwap) / vwap) * 100
    return True, f"Price above VWAP: ${current_price:.4f} > ${vwap:.4f} (+{pct_above:.2f}%)"


def check_all_entry_conditions(bars_1m, current_price):
    """
    Check ALL entry conditions at once
    
    Parameters:
    - bars_1m: List of 1-minute bars for pattern/MACD/volume/VWAP
    - current_price: Current price
    
    Returns: (bool, dict, float, float) - (all_conditions_met, condition_results, consolidation_low, consolidation_high)
    """
    # Check each condition
    pattern_ok, pattern_msg, consolidation_low, consolidation_high = detect_breakout_pattern(bars_1m)
    macd_ok, macd_msg = check_macd_positive(bars_1m)
    volume_ok, volume_msg = check_volume_conditions(bars_1m)
    vwap_ok, vwap_msg = check_above_vwap(bars_1m, current_price)
    
    # Compile results
    results = {
        'pattern': {'ok': pattern_ok, 'msg': pattern_msg},
        'macd': {'ok': macd_ok, 'msg': macd_msg},
        'volume': {'ok': volume_ok, 'msg': volume_msg},
        'vwap': {'ok': vwap_ok, 'msg': vwap_msg}
    }
    
    all_ok = pattern_ok and macd_ok and volume_ok and vwap_ok
    
    return all_ok, results, consolidation_low, consolidation_high


# ==================== EXIT CONDITIONS ====================

def check_dynamic_exit(bars):
    """
    Check for first red candle exit signal (aggressive exit for breakout momentum loss)
    Exit if the latest completed bar closes red
    
    Parameters:
    - bars: List of bars since entry
    
    Returns: (bool, str) - (should_exit, message)
    """
    if len(bars) < 1:
        return False, "Insufficient bar data for exit check"
    
    # Get the last completed bar
    latest_bar = bars[-1]
    
    # Check if latest bar is red (momentum loss)
    if latest_bar['close'] < latest_bar['open']:
        message = f"Red candle detected (momentum loss): open ${latest_bar['open']:.2f} > close ${latest_bar['close']:.2f}"
        return True, message
    
    return False, f"No exit signal: green candle (open ${latest_bar['open']:.2f} < close ${latest_bar['close']:.2f})"


def check_stop_loss_hit(current_bar, stop_price):
    """
    Check if stop loss has been hit
    
    Parameters:
    - current_bar: Current bar dictionary with 'low'
    - stop_price: Stop loss price
    
    Returns: bool - True if stop hit
    """
    return current_bar['low'] <= stop_price


def check_profit_target_hit(current_bar, profit_price):
    """
    Check if profit target has been hit
    
    Parameters:
    - current_bar: Current bar dictionary with 'high'
    - profit_price: Profit target price
    
    Returns: bool - True if profit hit
    """
    return current_bar['high'] >= profit_price


def check_end_of_day(current_time):
    """
    Check if we're near end of day (should close positions)
    
    Parameters:
    - current_time: datetime object with hour and minute
    
    Returns: bool - True if near close
    """
    if current_time.hour == StrategyConfig.END_OF_DAY_HOUR and current_time.minute >= StrategyConfig.END_OF_DAY_MINUTE:
        return True
    elif current_time.hour > StrategyConfig.END_OF_DAY_HOUR:
        return True
    return False


# ==================== POSITION SIZING ====================

def calculate_position_size(account_balance, entry_price, stop_price):
    """
    Calculate position size for $500 account simulation:
    - Use $100 per trade (allows 5 trades per day)
    - Ignore actual account balance to simulate small account
    
    Parameters:
    - account_balance: Actual account balance (ignored for simulation)
    - entry_price: Entry price per share
    - stop_price: Stop loss price
    
    Returns: int - Number of shares to trade
    """
    # Simulate $500 account with $100 per trade
    simulated_trade_size = StrategyConfig.TRADE_SIZE_DOLLARS
    
    # Calculate shares based on entry price
    shares = int(simulated_trade_size / entry_price)
    
    return max(shares, 1)  # minimum 1 share


def calculate_commission(shares, trade_value, is_sell=False):
    """
    Calculate IBKR Fixed pricing commission
    
    Parameters:
    - shares: Number of shares
    - trade_value: Total trade value (price * shares)
    - is_sell: True if selling (includes SEC fee), False if buying
    
    Returns: float - Total commission and fees
    """
    # Base commission: $0.005 per share, $1 minimum
    commission = max(shares * StrategyConfig.COMMISSION_PER_SHARE, StrategyConfig.COMMISSION_MINIMUM)
    
    # Add SEC fee on sells
    if is_sell:
        sec_fee = trade_value * StrategyConfig.SEC_FEE_PER_DOLLAR
        commission += sec_fee
    
    return commission


def calculate_entry_exit_prices(current_price, consolidation_low, consolidation_high):
    """
    Calculate entry price, stop price, and profit target for breakout
    
    Stop loss placed below consolidation range (support level)
    
    Parameters:
    - current_price: Current market price
    - consolidation_low: Consolidation low price (for stop loss support)
    - consolidation_high: Consolidation high price (breakout level)
    
    Returns: (entry_price, stop_price, profit_price) or (None, None, None)
    """
    # Entry price: add spread
    entry_price = round(current_price * (1 + StrategyConfig.ENTRY_SPREAD_PCT), 2)
    
    # Stop loss: below consolidation low (support level) with 2% buffer
    stop_price = round(consolidation_low * 0.98, 2)
    
    # Profit target: % gain from entry
    profit_price = round(entry_price * (1 + StrategyConfig.PROFIT_TARGET_PCT), 2)
    
    # Validate stop loss (ensure at least 2% distance)
    stop_distance_pct = (entry_price - stop_price) / entry_price
    if stop_price >= entry_price or stop_distance_pct < 0.02:
        return None, None, None
    
    return entry_price, stop_price, profit_price


# ==================== UTILITY FUNCTIONS ====================

def get_strategy_summary():
    """Return a summary of current strategy configuration"""
    return f"""
Strategy Configuration:
======================
MACD: {StrategyConfig.MACD_FAST}/{StrategyConfig.MACD_SLOW}/{StrategyConfig.MACD_SIGNAL}
Profit Target: {StrategyConfig.PROFIT_TARGET_PCT*100:.1f}%
Pattern Lookback: {StrategyConfig.PATTERN_LOOKBACK_BARS} bars
Consolidation Range: max {StrategyConfig.MAX_CONSOLIDATION_RANGE_PCT}%
Min Breakout: {StrategyConfig.MIN_BREAKOUT_PCT}%
Volume Requirements: {StrategyConfig.MIN_RELATIVE_VOLUME}x avg, {StrategyConfig.BREAKOUT_VOLUME_SPIKE}x spike
Trade Size: ${StrategyConfig.TRADE_SIZE_DOLLARS} (of ${StrategyConfig.SIMULATED_ACCOUNT_SIZE} account)
End of Day: {StrategyConfig.END_OF_DAY_HOUR}:{StrategyConfig.END_OF_DAY_MINUTE:02d} PM
"""


if __name__ == "__main__":
    print("="*70)
    print("BREAKOUT TRADING STRATEGY - SHARED MODULE")
    print("="*70)
    print(get_strategy_summary())
    print("\nThis module is imported by:")
    print("  - Breakout-Algo.py (live trading)")
    print("  - Breakout-Backtest.py (backtesting)")
    print("\nModify StrategyConfig class to change strategy parameters.")
