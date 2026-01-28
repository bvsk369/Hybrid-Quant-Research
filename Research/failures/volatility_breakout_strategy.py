"""
Volatility Breakout Strategy

Logic: Trade when price breaks out of Bollinger Bands during high volatility.
Breakouts during high volatility tend to continue (momentum effect).

Entry:
- Long: price breaks above upper Bollinger Band + high volatility
- Short: price breaks below lower Bollinger Band + high volatility

Exit:
- Price returns to middle band
- Or volatility contracts
- Or max holding time exceeded
"""

import numpy as np
import pandas as pd


def backtest_volatility_breakout(
    df: pd.DataFrame,
    bb_breakout_threshold: float = 1.0,
    vol_high_quantile: float = 0.7,
    exit_bb_threshold: float = 0.3,
    max_hold_bars: int = 20,
    cost_per_trade: float = 0.0005
) -> pd.DataFrame:
    """
    Volatility breakout strategy backtest.
    
    Parameters:
    -----------
    df : DataFrame with Bollinger Band features (bb_position, bb_width)
    bb_breakout_threshold : bb_position threshold for breakout (default 1.0 = at upper band)
    vol_high_quantile : quantile threshold for "high volatility" (default 0.7)
    exit_bb_threshold : bb_position to exit (default 0.3 = near middle)
    max_hold_bars : maximum bars to hold
    cost_per_trade : transaction cost
    
    Returns:
    --------
    DataFrame with strategy signals and PnL
    """
    df = df.copy()
    
    # Validate required columns
    required = ['bb_position', 'bb_width', 'log_return', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # -------------------------------------------------
    # 1. Define High Volatility Regime
    # -------------------------------------------------
    vol_threshold = df['bb_width'].rolling(100).quantile(vol_high_quantile)
    high_vol = df['bb_width'] > vol_threshold
    
    # -------------------------------------------------
    # 2. Generate Entry Signals
    # -------------------------------------------------
    df['signal'] = 0
    
    # Long: price breaks above upper band in high vol
    long_entry = (df['bb_position'] > bb_breakout_threshold) & high_vol
    df.loc[long_entry, 'signal'] = 1
    
    # Short: price breaks below lower band in high vol
    short_entry = (df['bb_position'] < -bb_breakout_threshold) & high_vol
    df.loc[short_entry, 'signal'] = -1
    
    # Shift to avoid look-ahead bias
    df['signal'] = df['signal'].shift(1).fillna(0)
    
    # -------------------------------------------------
    # 3. Position Construction
    # -------------------------------------------------
    df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
    
    # -------------------------------------------------
    # 4. Exit Logic
    # -------------------------------------------------
    # Exit when price returns to middle band region
    exit_long = (df['position'] == 1) & (df['bb_position'].shift(1) < exit_bb_threshold)
    exit_short = (df['position'] == -1) & (df['bb_position'].shift(1) > -exit_bb_threshold)
    
    df.loc[exit_long | exit_short, 'position'] = 0
    df['position'] = df['position'].ffill().fillna(0)
    
    # -------------------------------------------------
    # 5. Max Holding Time
    # -------------------------------------------------
    trade_id = (df['position'].diff() != 0).cumsum()
    holding_time = df.groupby(trade_id).cumcount()
    
    df.loc[holding_time > max_hold_bars, 'position'] = 0
    df['position'] = df['position'].ffill().fillna(0)
    
    # -------------------------------------------------
    # 6. Calculate Returns
    # -------------------------------------------------
    df['strategy_return'] = df['position'] * df['log_return']
    
    df['position_change'] = df['position'].diff().abs().fillna(0)
    df['transaction_cost'] = cost_per_trade * df['position_change']
    df['strategy_return_net'] = df['strategy_return'] - df['transaction_cost']
    
    df['cum_strategy'] = df['strategy_return'].cumsum()
    df['cum_strategy_net'] = df['strategy_return_net'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()
    
    # Store filter for analysis
    df['high_vol_regime'] = high_vol
    
    return df


def volatility_breakout_summary(df: pd.DataFrame) -> dict:
    """
    Print and return summary statistics for volatility breakout strategy.
    """
    trades = (df['position_change'] > 0).sum() // 2
    
    gross_return = df['cum_strategy'].iloc[-1]
    net_return = df['cum_strategy_net'].iloc[-1]
    market_return = df['cum_market'].iloc[-1]
    
    bars_per_year = 252 * 375
    strategy_std = df['strategy_return_net'].std()
    sharpe = (df['strategy_return_net'].mean() / strategy_std) * np.sqrt(bars_per_year) if strategy_std > 0 else 0
    
    cum_max = df['cum_strategy_net'].cummax()
    drawdown = df['cum_strategy_net'] - cum_max
    max_drawdown = drawdown.min()
    
    high_vol_pct = df['high_vol_regime'].mean() if 'high_vol_regime' in df.columns else 0
    
    summary = {
        'trades': trades,
        'gross_return': gross_return,
        'net_return': net_return,
        'market_return': market_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'high_vol_regime_pct': high_vol_pct
    }
    
    print("\n" + "="*50)
    print("VOLATILITY BREAKOUT STRATEGY SUMMARY")
    print("="*50)
    print(f"Total Trades:     {trades}")
    print(f"Gross Return:     {gross_return:.4f} ({gross_return*100:.2f}%)")
    print(f"Net Return:       {net_return:.4f} ({net_return*100:.2f}%)")
    print(f"Market Return:    {market_return:.4f} ({market_return*100:.2f}%)")
    print(f"Sharpe Ratio:     {sharpe:.2f}")
    print(f"Max Drawdown:     {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
    print(f"High Vol Regime:  {high_vol_pct*100:.1f}% of time")
    print("="*50 + "\n")
    
    return summary


# Usage in notebook:
# from volatility_breakout_strategy import backtest_volatility_breakout, volatility_breakout_summary
# df = backtest_volatility_breakout(df)
# stats = volatility_breakout_summary(df)
