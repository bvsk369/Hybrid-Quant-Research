import numpy as np
import pandas as pd

def momentum_signal(df: pd.DataFrame) -> pd.Series:
    """
    LEGACY: Basic momentum signal (kept for backward compatibility).
    For enhanced features, use momentum_signal_enhanced() instead.
    
    Returns:
        Signal series: +1 = long, -1 = short, 0 = no signal
    """
    signal = np.zeros(len(df))
    
    signal[df['momentum_zscore_20'] > 1.5] = 1
    signal[df['momentum_zscore_20'] < -1.5] = -1
    
    return pd.Series(signal, index=df.index)


def momentum_signal_enhanced(
    df: pd.DataFrame,
    entry_zscore: float = 1.5,
    exit_zscore: float = 0.3,
    atr_stop_multiplier: float = 2.5,
    trailing_stop_atr: float = 2.0,
    base_position_size: float = 0.8,
    max_position_size: float = 1.0,
    use_trend_filter: bool = True,
    use_volume_filter: bool = False
) -> pd.DataFrame:
    """
    Enhanced momentum strategy with comprehensive risk management.
    
    Features:
    - ATR-based dynamic stop loss
    - Trailing stops to protect profits
    - Volatility-based position sizing
    - Trend and volume filters
    - Momentum acceleration confirmation
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with features (must have: momentum_zscore_20, atr_14, ema_12, ema_26, volume, rsi_14)
    entry_zscore : float
        Momentum z-score threshold for entry (default: 1.8)
    exit_zscore : float
        Z-score below which to exit (default: 0.5)
    atr_stop_multiplier : float
        Stop loss distance in ATR units (default: 2.0)
    trailing_stop_atr : float
        Trailing stop distance in ATR units (default: 1.5)
    base_position_size : float
        Base position size as fraction of capital (default: 0.5)
    max_position_size : float
        Maximum position size (default: 1.0)
    use_trend_filter : bool
        Use EMA trend filter (default: True)
    use_volume_filter : bool
        Require above-average volume (default: True)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - signal: +1 (long), -1 (short), 0 (neutral)
        - stop_loss: stop loss price
        - trailing_stop: trailing stop price
        - position_size: recommended position size (0.0 to 1.0)
        - entry_price: price at signal generation
    """
    df = df.copy()
    
    # Required columns check
    required = ['momentum_zscore_20', 'atr_14', 'close', 'ema_12', 'ema_26', 'volume', 'rsi_14', 'vol_20']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Initialize result columns
    signal = np.zeros(len(df))
    stop_loss = np.full(len(df), np.nan)
    trailing_stop = np.full(len(df), np.nan)
    position_size = np.zeros(len(df))
    entry_price = df['close'].values.copy()
    
    # Get basic signals
    momentum_z = df['momentum_zscore_20'].values
    close = df['close'].values
    atr = df['atr_14'].values
    
    # Entry Filters
    long_momentum = momentum_z > entry_zscore
    short_momentum = momentum_z < -entry_zscore
    
    # Trend Filter: EMA cross
    if use_trend_filter:
        trend_up = df['ema_12'] > df['ema_26']
        trend_down = df['ema_12'] < df['ema_26']
    else:
        trend_up = np.ones(len(df), dtype=bool)
        trend_down = np.ones(len(df), dtype=bool)
    
    # Volume Filter: above 20-period average
    if use_volume_filter:
        avg_volume = df['volume'].rolling(20).mean()
        high_volume = df['volume'] > avg_volume
    else:
        high_volume = np.ones(len(df), dtype=bool)
    
    # RSI Filter: avoid extreme overbought/oversold
    rsi_not_extreme_high = df['rsi_14'] < 75
    rsi_not_extreme_low = df['rsi_14'] > 25
    
    # Momentum Acceleration (momentum is accelerating)
    momentum_accel = df['momentum_zscore_20'].diff() > 0
    momentum_decel = df['momentum_zscore_20'].diff() < 0
    
    # Entry Conditions
    long_entry = (
        long_momentum & 
        trend_up & 
        high_volume & 
        rsi_not_extreme_high &
        momentum_accel
    )
    
    short_entry = (
        short_momentum & 
        trend_down & 
        high_volume & 
        rsi_not_extreme_low &
        momentum_decel
    )
    
    # Exit Conditions (momentum weakening)
    momentum_weak = np.abs(momentum_z) < exit_zscore
    
    # Generate signals
    signal[long_entry] = 1
    signal[short_entry] = -1
    signal[momentum_weak] = 0  # Exit when momentum weakens
    
    # Calculate Stop Losses (ATR-based)
    for i in range(len(df)):
        if signal[i] == 1:  # Long
            stop_loss[i] = close[i] - (atr_stop_multiplier * atr[i])
            trailing_stop[i] = close[i] - (trailing_stop_atr * atr[i])
        elif signal[i] == -1:  # Short
            stop_loss[i] = close[i] + (atr_stop_multiplier * atr[i])
            trailing_stop[i] = close[i] + (trailing_stop_atr * atr[i])
    
    # Position Sizing (volatility-based)
    # Lower size in high volatility, higher size in low volatility
    vol_20 = df['vol_20'].values
    vol_percentile = pd.Series(vol_20).rank(pct=True).values
    
    # Scale position: higher volatility = smaller position
    size_factor = 1.0 - (vol_percentile * 0.5)  # 0.5 to 1.0
    
    for i in range(len(df)):
        if signal[i] != 0:
            position_size[i] = np.clip(
                base_position_size * size_factor[i],
                0.0,
                max_position_size
            )
    
    # Return DataFrame
    result = pd.DataFrame({
        'signal': signal,
        'stop_loss': stop_loss,
        'trailing_stop': trailing_stop,
        'position_size': position_size,
        'entry_price': entry_price
    }, index=df.index)
    
    return result
