"""
Momentum Strategy (ULTRA-CONSERVATIVE)

Very strict rules to minimize trades and maximize signal quality.
Target: <500 trades over entire dataset, positive net returns.

Key filters:
1. Very high momentum threshold (3.0+ z-score)
2. Trend confirmation (EMA cross + price above/below EMA)
3. Volatility filter (avoid high volatility noise)
4. Long cooldown between trades (100+ bars = ~1.5 hours)
5. Only trade when momentum is sustained (consecutive bars)
"""

import numpy as np
import pandas as pd


def backtest_momentum_strict(
    df: pd.DataFrame,
    entry_threshold: float = 3.0,         # Very high threshold
    exit_threshold: float = 1.0,          # Don't exit too early
    max_hold_bars: int = 120,             # Hold up to 2 hours
    min_bars_between_trades: int = 100,   # ~1.5 hour cooldown
    consecutive_bars: int = 3,            # Must have signal for 3 bars
    cost_per_trade: float = 0.0005,
    momentum_col: str = "momentum_zscore_20"
) -> pd.DataFrame:
    """
    Ultra-conservative momentum strategy.
    
    Parameters:
    -----------
    entry_threshold : z-score threshold (default 3.0 = very strong)
    exit_threshold : exit when momentum falls below this (default 1.0)
    max_hold_bars : maximum holding period (default 120)
    min_bars_between_trades : cooldown in bars (default 100)
    consecutive_bars : consecutive bars needed for entry (default 3)
    
    Returns:
    --------
    DataFrame with strategy signals and PnL
    """
    df = df.copy()
    
    # Validate columns
    required = [momentum_col, 'log_return', 'close', 'ema_12', 'ema_26', 'vol_20', 'vol_60']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing: {col}")
    
    # -------------------------------------------------
    # 1. Trend Filter (EMA cross)
    # -------------------------------------------------
    uptrend = (df['ema_12'] > df['ema_26']) & (df['close'] > df['ema_26'])
    downtrend = (df['ema_12'] < df['ema_26']) & (df['close'] < df['ema_26'])
    
    # -------------------------------------------------
    # 2. Volatility Filter (avoid high vol = noise)
    # -------------------------------------------------
    low_vol = df['vol_20'] < df['vol_60']  # Low vol regime
    
    # -------------------------------------------------
    # 3. Raw Signal (very strong momentum + trend + low vol)
    # -------------------------------------------------
    long_raw = (df[momentum_col] > entry_threshold) & uptrend & low_vol
    short_raw = (df[momentum_col] < -entry_threshold) & downtrend & low_vol
    
    # -------------------------------------------------
    # 4. Consecutive Bar Filter
    # -------------------------------------------------
    # Long signal must persist for consecutive_bars
    long_consecutive = long_raw.rolling(consecutive_bars).sum() >= consecutive_bars
    short_consecutive = short_raw.rolling(consecutive_bars).sum() >= consecutive_bars
    
    df['raw_signal'] = 0
    df.loc[long_consecutive, 'raw_signal'] = 1
    df.loc[short_consecutive, 'raw_signal'] = -1
    
    # Shift to avoid look-ahead
    df['raw_signal'] = df['raw_signal'].shift(1).fillna(0)
    
    # -------------------------------------------------
    # 5. Cooldown Filter (vectorized for speed)
    # -------------------------------------------------
    df['signal'] = 0
    
    signal_changes = df['raw_signal'].diff().fillna(0) != 0
    signal_indices = df.index[signal_changes & (df['raw_signal'] != 0)].tolist()
    
    last_trade_idx = -min_bars_between_trades - 1
    for i, idx in enumerate(df.index):
        if idx in signal_indices:
            bar_num = df.index.get_loc(idx)
            if bar_num - last_trade_idx >= min_bars_between_trades:
                df.loc[idx, 'signal'] = df.loc[idx, 'raw_signal']
                last_trade_idx = bar_num
    
    df = df.drop(columns=['raw_signal'])
    
    # -------------------------------------------------
    # 6. Position Construction
    # -------------------------------------------------
    df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    
    # -------------------------------------------------
    # 7. Exit Logic
    # -------------------------------------------------
    exit_long = (df['position'] == 1) & (df[momentum_col].shift(1) < exit_threshold)
    exit_short = (df['position'] == -1) & (df[momentum_col].shift(1) > -exit_threshold)
    
    df.loc[exit_long | exit_short, 'position'] = 0
    df['position'] = df['position'].ffill().fillna(0)
    
    # -------------------------------------------------
    # 8. Max Hold Time
    # -------------------------------------------------
    trade_id = (df['position'].diff() != 0).cumsum()
    holding_time = df.groupby(trade_id).cumcount()
    
    df.loc[holding_time > max_hold_bars, 'position'] = 0
    df['position'] = df['position'].ffill().fillna(0)
    
    # -------------------------------------------------
    # 9. Returns
    # -------------------------------------------------
    df['strategy_return'] = df['position'] * df['log_return']
    df['position_change'] = df['position'].diff().abs().fillna(0)
    df['transaction_cost'] = cost_per_trade * df['position_change']
    df['strategy_return_net'] = df['strategy_return'] - df['transaction_cost']
    
    df['cum_strategy'] = df['strategy_return'].cumsum()
    df['cum_strategy_net'] = df['strategy_return_net'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()
    
    return df


def momentum_strict_summary(df: pd.DataFrame) -> dict:
    """Summary stats for strict momentum strategy."""
    trades = (df['position_change'] > 0).sum() // 2
    
    gross_return = df['cum_strategy'].iloc[-1]
    net_return = df['cum_strategy_net'].iloc[-1]
    market_return = df['cum_market'].iloc[-1]
    
    bars_per_year = 252 * 375
    strategy_std = df['strategy_return_net'].std()
    sharpe = (df['strategy_return_net'].mean() / strategy_std) * np.sqrt(bars_per_year) if strategy_std > 0 else 0
    
    cum_max = df['cum_strategy_net'].cummax()
    max_drawdown = (df['cum_strategy_net'] - cum_max).min()
    
    # Win rate on closed trades
    trade_pnl = []
    in_trade = False
    trade_start_val = 0
    
    for i in range(1, len(df)):
        if df['position_change'].iloc[i] > 0:
            if not in_trade:
                in_trade = True
                trade_start_val = df['cum_strategy_net'].iloc[i-1]
            else:
                trade_pnl.append(df['cum_strategy_net'].iloc[i-1] - trade_start_val)
                in_trade = False
    
    win_rate = sum(1 for p in trade_pnl if p > 0) / len(trade_pnl) if trade_pnl else 0
    avg_win = np.mean([p for p in trade_pnl if p > 0]) if any(p > 0 for p in trade_pnl) else 0
    avg_loss = np.mean([p for p in trade_pnl if p <= 0]) if any(p <= 0 for p in trade_pnl) else 0
    
    print("\n" + "="*55)
    print("MOMENTUM STRATEGY (STRICT) SUMMARY")
    print("="*55)
    print(f"Total Trades:     {trades}")
    print(f"Gross Return:     {gross_return:.4f} ({gross_return*100:.2f}%)")
    print(f"Net Return:       {net_return:.4f} ({net_return*100:.2f}%)")
    print(f"Market Return:    {market_return:.4f} ({market_return*100:.2f}%)")
    print(f"Sharpe Ratio:     {sharpe:.2f}")
    print(f"Max Drawdown:     {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
    print(f"Win Rate:         {win_rate*100:.1f}%")
    print(f"Avg Win:          {avg_win:.4f}")
    print(f"Avg Loss:         {avg_loss:.4f}")
    print(f"Total Costs:      {df['transaction_cost'].sum():.4f}")
    print("="*55 + "\n")
    
    return {'trades': trades, 'net_return': net_return, 'sharpe': sharpe, 'win_rate': win_rate}


# Usage:
# from momentum_strict import backtest_momentum_strict, momentum_strict_summary
# df = backtest_momentum_strict(df)
# momentum_strict_summary(df)
