# Robust Momentum Strategy Guide

## Overview

I've created a **robust momentum strategy** (`momentum_robust.py`) that addresses the high drawdown issue in your existing momentum strategies. This strategy includes comprehensive risk management features.

## Key Improvements

### 1. **Advanced Risk Management**
- **ATR-based stops**: Dynamic stop-loss based on volatility
- **Trailing stops**: Protects profits as trade moves in your favor
- **Position sizing**: Scales position based on volatility and drawdown
- **Circuit breakers**: Reduces trading when drawdown exceeds limits

### 2. **Better Entry/Exit Logic**
- **Multiple confirmations**: Trend, volume, momentum, RSI filters
- **MACD confirmation**: Additional trend filter
- **RSI filter**: Avoids extreme overbought/oversold conditions
- **Momentum acceleration**: Only enters when momentum is accelerating

### 3. **Drawdown Control**
- **Max drawdown limit**: 15% default (configurable)
- **Automatic position reduction**: Reduces size when drawdown is high
- **Volatility scaling**: Adjusts position size based on market volatility

## How to Use

### Quick Start

**In a Notebook (from `Research/notebooks/`):**

```python
# First, set up the import path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.getcwd()), 'src'))

# Or use the helper:
# exec(open('import_helper.py').read())

# Now import
from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
from features_2 import add_all_features
from feature import add_log_returns, add_rolling_volatility, add_moving_averages, add_zscore

# Load your data (with features)
df = pd.read_csv('../Data/your_data.csv', parse_dates=True, index_col=0)

# Add features if not already present
df = add_log_returns(df)
df = add_rolling_volatility(df)
df = add_moving_averages(df)
df = add_zscore(df)
df = add_all_features(df)

# Run strategy
df_results = backtest_momentum_robust(
    df,
    entry_zscore=1.8,      # Entry threshold
    exit_zscore=0.3,       # Exit threshold
    max_hold_bars=50,      # Maximum holding period
    atr_stop_multiplier=2.0,  # Stop loss in ATR units
    trailing_stop_atr=1.5,     # Trailing stop in ATR units
    max_drawdown_limit=0.15    # 15% max drawdown
)

# Analyze results
metrics = analyze_momentum_robust(df_results)
```

**From Python Script (from `Research/src/`):**

```python
from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
from features_2 import add_all_features
from feature import add_log_returns, add_rolling_volatility, add_moving_averages, add_zscore

# Load and prepare data
df = pd.read_csv('your_data.csv', parse_dates=True, index_col=0)
df = add_log_returns(df)
df = add_rolling_volatility(df)
df = add_moving_averages(df)
df = add_zscore(df)
df = add_all_features(df)

# Run strategy
df_results = backtest_momentum_robust(df)
metrics = analyze_momentum_robust(df_results)
```

### Using the Test Script

```bash
cd Research/src/strategies
python test_momentum_robust.py
```

## Parameters Explained

### Entry/Exit Parameters
- `entry_zscore` (default: 1.8): Momentum z-score threshold for entry
  - Lower = more trades, higher = fewer but stronger signals
- `exit_zscore` (default: 0.3): Exit when momentum normalizes
  - Lower = exit earlier, higher = hold longer
- `max_hold_bars` (default: 50): Maximum bars to hold a position

### Risk Management Parameters
- `atr_stop_multiplier` (default: 2.0): Stop loss distance in ATR units
  - Higher = wider stops, lower = tighter stops
- `trailing_stop_atr` (default: 1.5): Trailing stop distance
  - Protects profits as price moves favorably
- `max_drawdown_limit` (default: 0.15): 15% max drawdown before reducing position size
- `base_position_size` (default: 0.5): Base position size (0.0 to 1.0)
- `max_position_size` (default: 1.0): Maximum position size

### Filter Parameters
- `use_trend_filter`: Use EMA trend filter (recommended: True)
- `use_volume_filter`: Require above-average volume (recommended: True)
- `use_momentum_confirmation`: Require momentum acceleration (recommended: True)
- `use_macd`: Use MACD for trend confirmation (recommended: True)

## Expected Performance

### Target Metrics
- **Sharpe Ratio**: > 1.5
- **Calmar Ratio**: > 2.0
- **Max Drawdown**: < 15%
- **Win Rate**: > 55%
- **Profit Factor**: > 1.5

### Comparison with Previous Strategies

| Metric | Old Momentum | Robust Momentum |
|--------|--------------|-----------------|
| Drawdown Control | ❌ None | ✅ ATR-based stops |
| Position Sizing | ❌ Fixed | ✅ Dynamic (volatility-based) |
| Trailing Stops | ❌ No | ✅ Yes |
| Circuit Breakers | ❌ No | ✅ Yes |
| Multiple Filters | ⚠️ Basic | ✅ Comprehensive |

## Parameter Tuning

### If Drawdown is Still Too High
1. **Reduce position size**: Lower `base_position_size` to 0.3-0.4
2. **Tighten stops**: Reduce `atr_stop_multiplier` to 1.5
3. **Lower drawdown limit**: Set `max_drawdown_limit` to 0.10 (10%)
4. **Increase cooldown**: Increase `min_cooldown_bars` to 10-15

### If Not Enough Trades
1. **Lower entry threshold**: Reduce `entry_zscore` to 1.5
2. **Relax filters**: Set some filters to False
3. **Reduce cooldown**: Lower `min_cooldown_bars` to 5

### If Too Many Losing Trades
1. **Raise entry threshold**: Increase `entry_zscore` to 2.0-2.5
2. **Tighten filters**: Enable all filters
3. **Tighter stops**: Reduce `atr_stop_multiplier` to 1.5

## Next Steps

1. **Test on your data**: Run the strategy and compare with previous results
2. **Parameter optimization**: Use grid search to find optimal parameters
3. **Multi-timeframe**: Test on 1min, 5min, 15min data
4. **Walk-forward analysis**: Test robustness across different periods

## C++ Integration

See `PROJECT_ROADMAP.md` for details on:
- Porting to C++ for 10-100x speedup
- Building the C++ engine
- Python bindings for easy testing

## Troubleshooting

### "Missing required column" error
- Make sure you've run all feature calculation functions
- Check that `add_all_features()` was called

### Strategy produces no trades
- Lower `entry_zscore` threshold
- Check that filters aren't too restrictive
- Verify data has sufficient volatility

### Still high drawdown
- Reduce `base_position_size`
- Tighten `atr_stop_multiplier`
- Lower `max_drawdown_limit`

## Files Created

1. **`momentum_robust.py`**: Main strategy implementation
2. **`test_momentum_robust.py`**: Test script
3. **`PROJECT_ROADMAP.md`**: C++ integration roadmap
4. **`Engine/`**: C++ project structure (starter template)

## Questions?

- Check the code comments for detailed explanations
- Review `PROJECT_ROADMAP.md` for next steps
- Test with different parameters to find what works for your data
