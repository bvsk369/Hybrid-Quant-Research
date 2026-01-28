import numpy as np
import pandas as pd

def mean_reversion_signal(df: pd.DataFrame) -> pd.Series:
    """
    LEGACY: Basic mean reversion signal (kept for backward compatibility).
    For enhanced features, use mean_reversion_signal_enhanced() instead.
    
    Returns:
        Signal series: +1 = long, -1 = short, 0 = no signal
    """
    signal = np.zeros(len(df))
    
    long_cond = (df['bb_position'] < -0.8) & (df['rsi_14'] < 30)
    short_cond = (df['bb_position'] > 0.8) & (df['rsi_14'] > 70)
    
    signal[long_cond] = 1
    signal[short_cond] = -1
    
    return pd.Series(signal, index=df.index)


def mean_reversion_signal_enhanced(
    df: pd.DataFrame,
    bb_threshold: float = 0.6,
    rsi_oversold: float = 35,
    rsi_overbought: float = 65,
    atr_stop_multiplier: float = 2.0,
    take_profit_target: float = 0.1,
    base_position_size: float = 0.8,
    max_position_size: float = 1.0,
    use_volatility_filter: bool = False
) -> pd.DataFrame:
    """
    Enhanced mean reversion strategy with comprehensive risk management.
    
    Features:
    - ATR-based dynamic stop loss
    - Take profit targets at BB middle or opposite extreme
    - Position sizing based on distance from mean
    - Volatility filter (only trade in low volatility)
    - Better confirmation with multiple indicators
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with features (must have: bb_position, rsi_14, atr_14, bb_middle, vol_20, vol_60)
    bb_threshold : float
        Bollinger Band position threshold for entry (default: 0.8)
    rsi_oversold : float
        RSI oversold threshold for long entry (default: 30)
    rsi_overbought : float
        RSI overbought threshold for short entry (default: 70)
    atr_stop_multiplier : float
        Stop loss distance in ATR units (default: 1.5)
    take_profit_target : float
        Take profit at BB position level (default: 0.2, near middle)
    base_position_size : float
        Base position size as fraction of capital (default: 0.5)
    max_position_size : float
        Maximum position size (default: 1.0)
    use_volatility_filter : bool
        Only trade in low volatility regimes (default: True)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - signal: +1 (long), -1 (short), 0 (neutral)
        - stop_loss: stop loss price
        - take_profit: take profit target price
        - position_size: recommended position size (0.0 to 1.0)
        - entry_price: price at signal generation
    """
    df = df.copy()
    
    # Required columns check
    required = ['bb_position', 'rsi_14', 'atr_14', 'close', 'bb_middle', 'bb_upper', 'bb_lower', 'vol_20', 'vol_60']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Initialize result columns
    signal = np.zeros(len(df))
    stop_loss = np.full(len(df), np.nan)
    take_profit = np.full(len(df), np.nan)
    position_size = np.zeros(len(df))
    entry_price = df['close'].values.copy()
    
    # Get basic signals
    bb_pos = df['bb_position'].values
    rsi = df['rsi_14'].values
    close = df['close'].values
    atr = df['atr_14'].values
    bb_middle = df['bb_middle'].values
    bb_upper = df['bb_upper'].values
    bb_lower = df['bb_lower'].values
    
    # Volatility Filter: only trade in low volatility
    if use_volatility_filter:
        low_vol = df['vol_20'] < df['vol_60']
    else:
        low_vol = np.ones(len(df), dtype=bool)
    
    # Entry Conditions (oversold/overbought with confirmation)
    # Long: price near lower band AND RSI oversold AND low volatility
    long_entry = (
        (bb_pos < -bb_threshold) & 
        (rsi < rsi_oversold) & 
        low_vol
    )
    
    # Short: price near upper band AND RSI overbought AND low volatility
    short_entry = (
        (bb_pos > bb_threshold) & 
        (rsi > rsi_overbought) & 
        low_vol
    )
    
    # Exit Conditions (price returning to mean)
    # Exit longs when BB position rises above take_profit_target
    # Exit shorts when BB position falls below -take_profit_target
    exit_long = bb_pos > take_profit_target
    exit_short = bb_pos < -take_profit_target
    
    # Generate signals
    signal[long_entry] = 1
    signal[short_entry] = -1
    
    # Apply exits
    signal[exit_long & (signal == 1)] = 0
    signal[exit_short & (signal == -1)] = 0
    
    # Calculate Stop Losses and Take Profits
    for i in range(len(df)):
        if signal[i] == 1:  # Long entry
            # Stop: below entry by ATR
            stop_loss[i] = close[i] - (atr_stop_multiplier * atr[i])
            # Take profit: BB middle or slightly above
            take_profit[i] = bb_middle[i]
            
        elif signal[i] == -1:  # Short entry
            # Stop: above entry by ATR
            stop_loss[i] = close[i] + (atr_stop_multiplier * atr[i])
            # Take profit: BB middle or slightly below
            take_profit[i] = bb_middle[i]
    
    # Position Sizing (based on distance from mean)
    # Larger position when further from mean (higher conviction)
    # But scaled down in higher volatility
    
    distance_from_mean = np.abs(bb_pos)
    
    # Normalize distance: 0.8 (threshold) = 0.5, 1.0 (extreme) = 1.0
    normalized_distance = np.clip((distance_from_mean - bb_threshold) / (1.0 - bb_threshold), 0.0, 1.0)
    
    # Volatility adjustment
    vol_ratio = df['vol_20'] / df['vol_60']
    vol_adjustment = np.clip(2.0 - vol_ratio.values, 0.5, 1.0)  # Lower size in high vol
    
    for i in range(len(df)):
        if signal[i] != 0:
            # Size based on distance and volatility
            size = base_position_size * (0.5 + 0.5 * normalized_distance[i]) * vol_adjustment[i]
            position_size[i] = np.clip(size, 0.0, max_position_size)
    
    # Return DataFrame
    result = pd.DataFrame({
        'signal': signal,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'position_size': position_size,
        'entry_price': entry_price
    }, index=df.index)
    
    return result
