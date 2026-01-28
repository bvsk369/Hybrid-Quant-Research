import numpy as np
import pandas as pd

def detect_regime(df: pd.DataFrame, trend_threshold: float = 0.005) -> pd.Series:
    """
    Detect market regime based on volatility and trend strength.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Data with vol_20, vol_60, close, sma_60 columns
    trend_threshold : float
        Threshold for trend detection (default: 0.5% = 0.005)
        Lower = more bars classified as trending
        Old value was 0.01 (1%) which was too strict
    
    Regimes:
    - LV_TREND: Low volatility + trending (momentum works well)
    - HV_TREND: High volatility + trending (momentum with caution)
    - LV_RANGE: Low volatility + ranging (mean reversion works)
    - HV_RANGE: High volatility + ranging (reduced position, not cash)
    """
    low_vol = df['vol_20'] < df['vol_60']

    trend_strength = abs(df['close'] - df['sma_60']) / df['sma_60']
    trending = trend_strength > trend_threshold  # Lowered from 0.01 to 0.005

    regime = np.full(len(df), 'UNDEFINED', dtype=object)

    regime[ low_vol &  trending] = 'LV_TREND'
    regime[~low_vol &  trending] = 'HV_TREND'
    regime[ low_vol & ~trending] = 'LV_RANGE'
    regime[~low_vol & ~trending] = 'HV_RANGE'

    return pd.Series(regime, index=df.index)
