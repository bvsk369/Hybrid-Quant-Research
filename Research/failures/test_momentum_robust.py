"""
Test script for robust momentum strategy.

Usage:
    python test_momentum_robust.py
"""

import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
from feature import add_log_returns, add_rolling_volatility, add_moving_averages, add_zscore
from features_2 import add_all_features
from cleaning import clean_equity_data


def load_and_prepare_data(data_path: str) -> pd.DataFrame:
    """
    Load and prepare data with all features.
    """
    print(f"Loading data from {data_path}...")
    
    # Load cleaned data or clean raw data
    if 'Cleaned' in data_path or 'Feature' in data_path:
        df = pd.read_csv(data_path, parse_dates=True, index_col=0)
    else:
        df = clean_equity_data(data_path)
    
    # Add basic features
    print("Adding basic features...")
    df = add_log_returns(df)
    df = add_rolling_volatility(df)
    df = add_moving_averages(df)
    df = add_zscore(df)
    
    # Add advanced features
    print("Adding advanced features...")
    df = add_all_features(df)
    
    print(f"Data loaded: {len(df)} bars")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    return df


def test_robust_momentum(data_path: str):
    """
    Test the robust momentum strategy.
    """
    # Load data
    df = load_and_prepare_data(data_path)
    
    # Run robust momentum strategy
    print("\n" + "="*70)
    print("RUNNING ROBUST MOMENTUM STRATEGY")
    print("="*70)
    
    df_results = backtest_momentum_robust(
        df,
        momentum_period=20,
        entry_zscore=1.8,
        exit_zscore=0.3,
        max_hold_bars=50,
        min_cooldown_bars=8,
        max_position_size=1.0,
        base_position_size=0.5,
        atr_stop_multiplier=2.0,
        trailing_stop_atr=1.5,
        max_drawdown_limit=0.15,
        volatility_scaling=True,
        cost_per_trade=0.0002,
        use_trend_filter=True,
        use_volume_filter=True,
        use_momentum_confirmation=True,
        use_macd=True
    )
    
    # Analyze results
    print("\nAnalyzing results...")
    metrics = analyze_momentum_robust(df_results)
    
    # Compare with market
    market_return = df_results['cum_market'].iloc[-1]
    strategy_return = metrics['net_return']
    outperformance = (strategy_return - market_return) * 100
    
    print(f"\n{'='*70}")
    print("KEY METRICS SUMMARY")
    print(f"{'='*70}")
    print(f"Strategy Return:     {strategy_return*100:.2f}%")
    print(f"Market Return:       {market_return*100:.2f}%")
    print(f"Outperformance:     {outperformance:.2f}%")
    print(f"Sharpe Ratio:        {metrics['sharpe']:.2f}")
    print(f"Max Drawdown:        {metrics['max_drawdown_pct']:.2f}%")
    print(f"Win Rate:            {metrics['win_rate']:.1f}%")
    print(f"Profit Factor:       {metrics['profit_factor']:.2f}")
    print(f"{'='*70}\n")
    
    return df_results, metrics


if __name__ == "__main__":
    # Example usage - adjust path to your data
    data_paths = [
        "../Data/ICICIBANK_Features2.csv",
        "../Data/ICICIBANK_5minute_features.csv",
        "../Data/ICICIBANK_Cleaned_Final.csv"
    ]
    
    # Try to find available data
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    for path in data_paths:
        full_path = os.path.join(base_dir, "Data", os.path.basename(path))
        if os.path.exists(full_path):
            print(f"Found data: {full_path}")
            test_robust_momentum(full_path)
            break
    else:
        print("ERROR: No data file found. Please specify the path to your data file.")
        print("\nUsage:")
        print("  python test_momentum_robust.py")
        print("\nOr modify the data_paths list in the script.")
