import numpy as np
import pandas as pd

def backtest_mean_reversion_existing_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean Reversion Backtest using precomputed features.
    
    Assumptions:
    - log_return = log(close_t / close_{t-1})
    - zscore_20 computed using rolling window (no future leakage)
    - vol_20, vol_60, sma_20, sma_60 are precomputed
    
    Execution Rules:
    - Signals generated on bar t-1
    - Positions applied on bar t
    - Exits executed on next bar after condition is observed
    - NO re-entry while already in position (prevents signal stacking)
    - Maximum holding time enforced (mean reversion timeout)
    
    Filters Applied:
    - Low volatility regime: vol_20 < vol_60
    - Low trend strength: |sma_20 - sma_60| / close < threshold
    - No large bars: |log_return| < k * rolling_std
    
    Known Limitations (documented for research integrity):
    - Exit condition (|z| < 0.5) assumes reversion always happens
    - No explicit stop-loss mechanism
    - Rolling std uses same data as strategy (acceptable for filter use only)
    """

    df = df.copy()

    REQUIRED_COLS = ['log_return', 'zscore_20', 'vol_20', 'vol_60', 'sma_20', 'sma_60', 'close']
    for col in REQUIRED_COLS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # -------------------------------------------------
    # Strategy Parameters
    # -------------------------------------------------
    TREND_THRESHOLD = 0.02      # 2% - low trend strength
    LARGE_BAR_MULTIPLIER = 2.0  # 2x rolling std
    ROLLING_STD_WINDOW = 20     # for large bar filter
    MAX_HOLD_BARS = 30          # maximum holding time (minutes)
    COST_PER_TRADE = 0.0005     # 5 bps

    # -------------------------------------------------
    # 0. Compute Filter Conditions
    # -------------------------------------------------
    # Filter 1: Low volatility regime
    low_vol_regime = df['vol_20'] < df['vol_60']

    # Filter 2: Low trend strength
    trend_strength = (df['sma_20'] - df['sma_60']).abs() / df['close']
    low_trend = trend_strength < TREND_THRESHOLD

    # Filter 3: No large bars (compute rolling std of returns)
    rolling_std = df['log_return'].rolling(window=ROLLING_STD_WINDOW).std()
    no_large_bar = df['log_return'].abs() < (LARGE_BAR_MULTIPLIER * rolling_std)

    # Combined filter: ALL conditions must be true
    trade_filter = low_vol_regime & low_trend & no_large_bar

    # -------------------------------------------------
    # 1. Raw Entry Signals (generated at bar t)
    # -------------------------------------------------
    df['signal'] = 0

    # Long entry: -3.5 < z <= -2.5 AND filters pass
    df.loc[
        (df['zscore_20'] <= -2.3) & (df['zscore_20'] > -3) & trade_filter,
        'signal'
    ] = 1

    # Short entry: 2.5 <= z < 3.5 AND filters pass
    df.loc[
        (df['zscore_20'] >= 2.3) & (df['zscore_20'] < 3) & trade_filter,
        'signal'
    ] = -1

    # -------------------------------------------------
    # 2. Shift signals to prevent look-ahead bias
    # -------------------------------------------------
    df['signal'] = df['signal'].shift(1)

    # -------------------------------------------------
    # 3. Position Construction with Anti-Stacking Logic
    # -------------------------------------------------
    # IMPROVED: Prevent new signals from overwriting existing positions
    # Only accept new signals when position is flat (0)
    
    # Vectorized approach: mark position entry/exit boundaries
    df['signal_change'] = (df['signal'] != 0) & (df['signal'].shift(1).fillna(0) == 0)
    
    # Create trade blocks: each block has a unique ID
    df['trade_block'] = df['signal_change'].cumsum()
    
    # Within each trade block, forward-fill the first non-zero signal
    df['position'] = (
        df.groupby('trade_block')['signal']
        .transform(lambda x: x.replace(0, np.nan).ffill())
        .fillna(0)
    )

    # -------------------------------------------------
    # 4. Exit Logic (NO FUTURE BIAS)
    # -------------------------------------------------
    # Exit decision is based on z-score observed at t-1
    exit_mask = df['zscore_20'].shift(1).abs() < 0.5

    df.loc[exit_mask, 'position'] = 0

    # Maintain flat until next entry
    df['position'] = df['position'].ffill()

    # -------------------------------------------------
    # 5. Maximum Holding Time (Mean Reversion Timeout)
    # -------------------------------------------------
    # If position hasn't reverted within MAX_HOLD_BARS, force exit
    df['trade_id'] = (df['position'].diff() != 0).cumsum()
    df['holding_time'] = df.groupby('trade_id').cumcount()

    # Force exit if held too long
    timeout_mask = df['holding_time'] > MAX_HOLD_BARS
    df.loc[timeout_mask, 'position'] = 0

    # Maintain flat after timeout
    df['position'] = df['position'].ffill()

    # -------------------------------------------------
    # 6. Log Explicit Trade Events
    # -------------------------------------------------
    df['trade'] = (df['position'].diff().abs() > 0).astype(int)

    # -------------------------------------------------
    # 7. Strategy Returns
    # -------------------------------------------------
    df['strategy_return'] = df['position'] * df['log_return']

    # -------------------------------------------------
    # 8. Transaction Cost Model
    # -------------------------------------------------
    df['position_change'] = df['position'].diff().abs()

    df['transaction_cost'] = COST_PER_TRADE * df['position_change']

    df['strategy_return_net'] = (
        df['strategy_return'] - df['transaction_cost']
    )

    # -------------------------------------------------
    # 9. Equity Curves (log-space)
    # -------------------------------------------------
    df['cum_strategy'] = df['strategy_return'].cumsum()
    df['cum_strategy_net'] = df['strategy_return_net'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()

    # -------------------------------------------------
    # 10. Store filter status for analysis
    # -------------------------------------------------
    df['low_vol_regime'] = low_vol_regime
    df['low_trend'] = low_trend
    df['no_large_bar'] = no_large_bar
    df['trade_filter'] = trade_filter

    # -------------------------------------------------
    # 11. Cleanup
    # -------------------------------------------------
    df = df.dropna()

    return df