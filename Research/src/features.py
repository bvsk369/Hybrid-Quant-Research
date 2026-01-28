import numpy as np
import pandas as pd

def add_log_returns(df: pd.DataFrame, target_col: str = "close") -> pd.DataFrame:
    """
    Calculates log returns.
    Definition: r_t = ln(P_t / P_{t-1})
    """
    df = df.copy()
    df['log_return'] = np.log(df[target_col] / df[target_col].shift(1))
    return df

def add_rolling_volatility(df: pd.DataFrame, log_ret_col: str = "log_return") -> pd.DataFrame:
    """
    Adds rolling volatility (standard deviation of log returns).
    """
    df = df.copy()
    df['vol_20'] = df[log_ret_col].rolling(20).std()
    df['vol_60'] = df[log_ret_col].rolling(60).std()
    
    # Fill zeros or NaNs to avoid division errors later
    df['vol_20'] = df['vol_20'].replace(0, np.nan).ffill()
    df['vol_60'] = df['vol_60'].replace(0, np.nan).ffill()
    return df

def add_moving_averages(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    """
    Adds Simple Moving Averages (SMA).
    """
    df = df.copy()
    df['sma_20'] = df[price_col].rolling(window=20).mean()
    df['sma_60'] = df[price_col].rolling(window=60).mean()
    return df

def add_ema(df: pd.DataFrame, periods: list = [12, 26], price_col: str = "close") -> pd.DataFrame:
    """
    Adds Exponential Moving Averages (EMA).
    """
    df = df.copy()
    for period in periods:
        df[f'ema_{period}'] = df[price_col].ewm(span=period, adjust=False).mean()
    return df

def add_rsi(df: pd.DataFrame, period: int = 14, price_col: str = "close") -> pd.DataFrame:
    """
    Adds Relative Strength Index (RSI).
    """
    df = df.copy()
    delta = df[price_col].diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
    df[f'rsi_{period}'] = df[f'rsi_{period}'].replace([np.inf, -np.inf], np.nan).ffill()
    return df

def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, price_col: str = "close") -> pd.DataFrame:
    """
    Adds MACD (Line, Signal, Histogram).
    """
    df = df.copy()
    ema_fast = df[price_col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[price_col].ewm(span=slow, adjust=False).mean()
    
    df['macd_line'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    df['macd_histogram'] = df['macd_line'] - df['macd_signal']
    return df

def add_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0, price_col: str = "close") -> pd.DataFrame:
    """
    Adds Bollinger Bands (Upper, Lower, Middle, Width, Position).
    """
    df = df.copy()
    df['bb_middle'] = df[price_col].rolling(period).mean()
    rolling_std = df[price_col].rolling(period).std()
    
    df['bb_upper'] = df['bb_middle'] + (num_std * rolling_std)
    df['bb_lower'] = df['bb_middle'] - (num_std * rolling_std)
    
    # Bandwidth: volatility measure
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # Position: -1 at lower band, 0 at middle, +1 at upper band
    df['bb_position'] = (df[price_col] - df['bb_middle']) / (num_std * rolling_std)
    return df

def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Adds Average True Range (ATR).
    """
    df = df.copy()
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df[f'atr_{period}'] = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return df

def add_momentum(df: pd.DataFrame, periods: list = [10, 20], price_col: str = "close") -> pd.DataFrame:
    """
    Adds Price Momentum and Momentum Z-Score.
    """
    df = df.copy()
    for period in periods:
        # Simple momentum (rate of change)
        df[f'momentum_{period}'] = df[price_col].pct_change(period)
        
        # Momentum z-score (standardized)
        rolling_mean = df[f'momentum_{period}'].rolling(period).mean()
        rolling_std = df[f'momentum_{period}'].rolling(period).std()
        df[f'momentum_zscore_{period}'] = (df[f'momentum_{period}'] - rolling_mean) / rolling_std
        
        df[f'momentum_zscore_{period}'] = df[f'momentum_zscore_{period}'].replace([np.inf, -np.inf], np.nan).ffill()
    return df

def add_return_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds Z-Score based on Log Returns (from original file 1).
    Requires 'log_return' and 'vol_20' to exist.
    """
    df = df.copy()
    mean_20 = df['log_return'].rolling(20).mean()
    
    # Standard Z-Score formula: (Value - Mean) / StdDev
    df['zscore_20'] = (df['log_return'] - mean_20) / df['vol_20']
    
    df['zscore_20'] = df['zscore_20'].replace([np.inf, -np.inf], np.nan).ffill()
    return df

def generate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    MASTER FUNCTION: Runs the entire feature engineering pipeline.
    """
    # 1. Base Calculations
    df = add_log_returns(df)
    df = add_rolling_volatility(df)
    
    # 2. Trends & Averages
    df = add_moving_averages(df)
    df = add_ema(df, periods=[12, 26])
    
    # 3. Oscillators & Momentum
    df = add_rsi(df, period=14)
    df = add_macd(df)
    df = add_momentum(df, periods=[10, 20])
    
    # 4. Volatility Bands & ATR
    df = add_bollinger_bands(df, period=20, num_std=2.0)
    df = add_atr(df, period=14)
    
    # 5. Advanced Stats (Requires previous steps)
    df = add_return_zscore(df)
    
    # 6. Final Cleanup
    # Drop initial rows where rolling windows haven't filled yet
    df = df.dropna()
    
    return df

# USAGE:
# from features import generate_features
# df_enriched = generate_features(df_raw)