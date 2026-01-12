import numpy as np
import pandas as pd

def add_log_returns(df: pd.DataFrame, target_col: str = "close") -> pd.DataFrame:
    """
    Calculates log returns to make price data stationary for the C++ engine.
    Definition: r_t = ln(P_t / P_{t-1})
    """
 
    df['log_return'] = np.log(df[target_col] / df[target_col].shift(1))
    df = df.dropna(subset=['log_return'])
    
    return df

def add_rolling_volatility(df: pd.DataFrame, log_ret_col: str = "log_return") -> pd.DataFrame:
    df = df.copy()

    df.loc[:, 'vol_20'] = df[log_ret_col].rolling(20).std()
    df.loc[:, 'vol_60'] = df[log_ret_col].rolling(60).std()

    df.loc[:, 'vol_20'] = df['vol_20'].replace(0, np.nan).ffill()
    df.loc[:, 'vol_60'] = df['vol_60'].replace(0, np.nan).ffill()

    return df



def add_moving_averages(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    df = df.copy()   # ← THIS LINE FIXES EVERYTHING

    df.loc[:, 'sma_20'] = df[price_col].rolling(window=20).mean()
    df.loc[:, 'sma_60'] = df[price_col].rolling(window=60).mean()

    df = df.dropna(subset=['sma_20', 'sma_60'])

    return df

def add_zscore(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.loc[:, 'mean_20'] = df['log_return'].rolling(20).mean()
    df.loc[:, 'zscore_20'] = (df['log_return'] - df['mean_20']) / df['vol_20']

    df.loc[:, 'zscore_20'] = (
        df['zscore_20']
        .replace([np.inf, -np.inf], np.nan)
        .ffill()
    )

    df = df.drop(columns=['mean_20'])

    return df
