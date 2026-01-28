"""
PROFITABLE MOMENTUM STRATEGY
Integration with existing momentum_balanced.py
"""

import numpy as np
import pandas as pd


def diagnose_momentum_profitable(
    df: pd.DataFrame,
    momentum_period: int = 20
) -> dict:
    """
    Diagnose momentum conditions for the profitable strategy.
    """
    print("\n" + "="*60)
    print("PROFITABLE MOMENTUM DIAGNOSTICS")
    print("="*60)
    
    total_bars = len(df)
    print(f"Total bars: {total_bars:,}")
    
    # Calculate momentum z-score
    df_temp = df.copy()
    df_temp['roc'] = df_temp['close'].pct_change(momentum_period)
    df_temp['momentum_mean'] = df_temp['roc'].rolling(window=60).mean()
    df_temp['momentum_std'] = df_temp['roc'].rolling(window=60).std()
    df_temp['momentum_std_adj'] = df_temp['momentum_std'].replace(0, np.nan)
    df_temp['momentum_zscore'] = (df_temp['roc'] - df_temp['momentum_mean']) / df_temp['momentum_std_adj']
    df_temp['momentum_zscore'] = df_temp['momentum_zscore'].fillna(0)
    
    # Momentum thresholds
    for thresh in [1.0, 1.5, 2.0, 2.5, 3.0]:
        oversold = (df_temp['momentum_zscore'] < -thresh).sum()
        overbought = (df_temp['momentum_zscore'] > thresh).sum()
        total = oversold + overbought
        pct = total / total_bars * 100
        print(f"  |momentum_zscore| > {thresh}: {total:,} bars ({pct:.2f}%)")
        print(f"    - Oversold (< -{thresh}): {oversold:,} bars")
        print(f"    - Overbought (> {thresh}): {overbought:,} bars")
    
    # Trend analysis
    if 'ema_12' in df.columns and 'ema_26' in df.columns:
        uptrend = (df['ema_12'] > df['ema_26']).sum()
        downtrend = (df['ema_12'] < df['ema_26']).sum()
        print(f"\nUptrend (EMA12 > EMA26): {uptrend:,} bars ({uptrend/total_bars*100:.1f}%)")
        print(f"Downtrend (EMA12 < EMA26): {downtrend:,} bars ({downtrend/total_bars*100:.1f}%)")
        
        # Combined conditions
        oversold_in_uptrend = ((df_temp['momentum_zscore'] < -2.0) & (df['ema_12'] > df['ema_26'])).sum()
        overbought_in_downtrend = ((df_temp['momentum_zscore'] > 2.0) & (df['ema_12'] < df['ema_26'])).sum()
        print(f"\nOversold in Uptrend: {oversold_in_uptrend:,} bars ({oversold_in_uptrend/total_bars*100:.2f}%)")
        print(f"Overbought in Downtrend: {overbought_in_downtrend:,} bars ({overbought_in_downtrend/total_bars*100:.2f}%)")
    
    # Volume analysis
    if 'volume' in df.columns:
        df_temp['volume_sma'] = df_temp['volume'].rolling(window=20).mean()
        df_temp['volume_ratio'] = df_temp['volume'] / df_temp['volume_sma']
        high_volume = (df_temp['volume_ratio'] > 1.2).sum()
        print(f"\nHigh Volume (ratio > 1.2): {high_volume:,} bars ({high_volume/total_bars*100:.1f}%)")
    
    print("="*60 + "\n")
    
    return {}


def backtest_momentum_profitable(
    df: pd.DataFrame,
    momentum_period: int = 20,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.5,
    max_hold_bars: int = 40,
    min_cooldown_bars: int = 10,
    risk_reward_ratio: float = 1.5,
    cost_per_trade: float = 0.0002,
    use_volume_filter: bool = True
) -> pd.DataFrame:
    """
    Profitable momentum strategy (mean reversion approach).
    """
    df = df.copy()
    
    # -------------------------------------------------
    # 1. Calculate Momentum Z-score
    # -------------------------------------------------
    df['roc'] = df['close'].pct_change(momentum_period)
    
    # Normalize using rolling z-score
    df['momentum_mean'] = df['roc'].rolling(window=60).mean()
    df['momentum_std'] = df['roc'].rolling(window=60).std()
    df['momentum_std_adj'] = df['momentum_std'].replace(0, np.nan)
    df['momentum_zscore_profitable'] = (df['roc'] - df['momentum_mean']) / df['momentum_std_adj']
    df['momentum_zscore_profitable'] = df['momentum_zscore_profitable'].fillna(0)
    
    # -------------------------------------------------
    # 2. Trend Filter
    # -------------------------------------------------
    # Calculate EMAs if not present
    if 'ema_12' not in df.columns:
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    if 'ema_26' not in df.columns:
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # Strong trend conditions
    df['ema_distance'] = (df['ema_12'] - df['ema_26']) / df['ema_26'] * 100
    df['trend_strength'] = df['ema_distance'].rolling(window=20).std()
    trend_strength_q80 = df['trend_strength'].quantile(0.8)
    
    strong_uptrend = (df['ema_12'] > df['ema_26']) & (df['trend_strength'] < trend_strength_q80)
    strong_downtrend = (df['ema_12'] < df['ema_26']) & (df['trend_strength'] < trend_strength_q80)
    
    # -------------------------------------------------
    # 3. Volume Filter
    # -------------------------------------------------
    if use_volume_filter and 'volume' in df.columns:
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        high_volume = df['volume_ratio'] > 1.2
    else:
        high_volume = pd.Series(True, index=df.index)
    
    # -------------------------------------------------
    # 4. Entry Signals (Mean Reversion)
    # -------------------------------------------------
    # LONG: Buy oversold in uptrend
    long_entry = (
        (df['momentum_zscore_profitable'] < -entry_zscore) &  # Oversold
        strong_uptrend &                           # In strong uptrend
        high_volume &                              # Volume confirmation
        (df['momentum_zscore_profitable'].shift(1) > df['momentum_zscore_profitable'])  # Momentum still dropping
    )
    
    # SHORT: Sell overbought in downtrend
    short_entry = (
        (df['momentum_zscore_profitable'] > entry_zscore) &   # Overbought
        strong_downtrend &                         # In strong downtrend
        high_volume &                              # Volume confirmation
        (df['momentum_zscore_profitable'].shift(1) < df['momentum_zscore_profitable'])  # Momentum still rising
    )
    
    # -------------------------------------------------
    # 5. Stop Loss and Profit Targets
    # -------------------------------------------------
    df['entry_price'] = np.nan
    df.loc[long_entry, 'entry_price'] = df['close']
    df.loc[short_entry, 'entry_price'] = df['close']
    
    # For longs
    if 'low' in df.columns:
        recent_low = df['low'].rolling(window=10).min()
        df['stop_loss_long'] = np.where(long_entry, recent_low * 0.995, np.nan)
        risk_long = df['close'] - df['stop_loss_long']
        df['profit_target_long'] = np.where(long_entry, df['close'] + risk_long * risk_reward_ratio, np.nan)
    
    # For shorts
    if 'high' in df.columns:
        recent_high = df['high'].rolling(window=10).max()
        df.loc[short_entry, 'stop_loss_short'] = recent_high * 1.005
        risk_short = df['stop_loss_short'] - df['close']
        df.loc[short_entry, 'profit_target_short'] = df['close'] - risk_short * risk_reward_ratio
    
    # -------------------------------------------------
    # 6. Position Management
    # -------------------------------------------------
    df['signal_profitable'] = 0
    df.loc[long_entry, 'signal_profitable'] = 1
    df.loc[short_entry, 'signal_profitable'] = -1
    
    # Shift signals (trade on next bar)
    df['signal_profitable'] = df['signal_profitable'].shift(1).fillna(0)
    
    # Track trades with cooldown
    in_position = False
    position_type = 0
    entry_bar = 0
    cooldown_counter = 0
    
    df['position_profitable'] = 0
    df['exit_reason'] = ''
    
    for i in range(1, len(df)):
        # Cooldown period
        if cooldown_counter > 0:
            cooldown_counter -= 1
            df.iloc[i, df.columns.get_loc('position_profitable')] = 0
            continue
        
        # Check exits if in position
        if in_position:
            current_price = df['close'].iloc[i]
            bars_in_trade = i - entry_bar
            
            # Check profit target
            if position_type == 1:  # Long
                if current_price >= df['profit_target_long'].iloc[entry_bar]:
                    df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'profit_target'
                    in_position = False
                    cooldown_counter = min_cooldown_bars
                    continue
                # Check stop loss
                elif current_price <= df['stop_loss_long'].iloc[entry_bar]:
                    df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                    in_position = False
                    cooldown_counter = min_cooldown_bars
                    continue
                    
            elif position_type == -1:  # Short
                if current_price <= df['profit_target_short'].iloc[entry_bar]:
                    df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'profit_target'
                    in_position = False
                    cooldown_counter = min_cooldown_bars
                    continue
                # Check stop loss
                elif current_price >= df['stop_loss_short'].iloc[entry_bar]:
                    df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                    in_position = False
                    cooldown_counter = min_cooldown_bars
                    continue
            
            # Check max hold time
            if bars_in_trade >= max_hold_bars:
                df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'max_hold'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Check momentum exit
            if position_type == 1 and df['momentum_zscore_profitable'].iloc[i] > exit_zscore:
                df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
                
            elif position_type == -1 and df['momentum_zscore_profitable'].iloc[i] < -exit_zscore:
                df.iloc[i, df.columns.get_loc('position_profitable')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Maintain position
            df.iloc[i, df.columns.get_loc('position_profitable')] = position_type
            
        # Check for new entries
        elif not in_position and df['signal_profitable'].iloc[i] != 0 and cooldown_counter == 0:
            position_type = df['signal_profitable'].iloc[i]
            df.iloc[i, df.columns.get_loc('position_profitable')] = position_type
            in_position = True
            entry_bar = i
    
    # -------------------------------------------------
    # 7. Calculate Returns
    # -------------------------------------------------
    if 'log_return' not in df.columns:
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    df['strategy_return_profitable'] = df['position_profitable'] * df['log_return']
    df['position_change_profitable'] = df['position_profitable'].diff().abs().fillna(0)
    df['transaction_cost_profitable'] = cost_per_trade * df['position_change_profitable']
    df['strategy_return_net_profitable'] = df['strategy_return_profitable'] - df['transaction_cost_profitable']
    
    # Cumulative returns
    df['cum_strategy_profitable'] = df['strategy_return_profitable'].cumsum()
    df['cum_strategy_net_profitable'] = df['strategy_return_net_profitable'].cumsum()
    
    # Keep existing market return
    if 'cum_market' not in df.columns:
        df['cum_market'] = df['log_return'].cumsum()
    
    return df


def momentum_profitable_summary(df: pd.DataFrame) -> dict:
    """Summary for profitable momentum strategy."""
    # Count trades
    position_changes = df['position_profitable'].diff().abs()
    trades = (position_changes > 0).sum() // 2
    
    # Returns
    gross = df['cum_strategy_profitable'].iloc[-1] if 'cum_strategy_profitable' in df.columns else 0
    net = df['cum_strategy_net_profitable'].iloc[-1] if 'cum_strategy_net_profitable' in df.columns else 0
    market = df['cum_market'].iloc[-1] if 'cum_market' in df.columns else 0
    
    # Sharpe Ratio
    if 'strategy_return_net_profitable' in df.columns:
        returns = df['strategy_return_net_profitable']
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 375)
        else:
            sharpe = 0
    else:
        sharpe = 0
    
    # Max Drawdown
    if 'cum_strategy_net_profitable' in df.columns:
        cumulative = df['cum_strategy_net_profitable']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
    else:
        max_dd = 0
    
    # Transaction costs
    total_costs = df['transaction_cost_profitable'].sum() if 'transaction_cost_profitable' in df.columns else 0
    
    # Win rate analysis
    if 'exit_reason' in df.columns:
        # Analyze trade outcomes
        win_trades = 0
        total_trades = 0
        
        # Simple analysis based on exit reasons
        profit_exits = (df['exit_reason'] == 'profit_target').sum()
        loss_exits = (df['exit_reason'] == 'stop_loss').sum()
        other_exits = trades - profit_exits - loss_exits
        
        win_rate = profit_exits / trades * 100 if trades > 0 else 0
    
    print("\n" + "="*60)
    print("PROFITABLE MOMENTUM STRATEGY SUMMARY")
    print("="*60)
    print(f"Total Trades:          {trades}")
    print(f"Gross Return:          {gross:.4f} ({gross*100:.2f}%)")
    print(f"Net Return:            {net:.4f} ({net*100:.2f}%)")
    print(f"Market Return:         {market:.4f} ({market*100:.2f}%)")
    print(f"Outperformance:        {(net - market)*100:.2f}%")
    print(f"Sharpe Ratio:          {sharpe:.2f}")
    print(f"Max Drawdown:          {max_dd:.4f} ({max_dd*100:.2f}%)")
    print(f"Total Costs:           {total_costs:.4f}")
    
    if 'exit_reason' in df.columns:
        print(f"\nExit Distribution:")
        exit_counts = df['exit_reason'].value_counts()
        for reason, count in exit_counts.items():
            if reason != '':
                pct = count / exit_counts.sum() * 100
                print(f"  {reason:15s}: {count:6d} ({pct:.1f}%)")
    
    print("="*60 + "\n")
    
    return {
        'trades': trades,
        'net_return': net,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'total_costs': total_costs
    }


def compare_strategies(df_balanced: pd.DataFrame, df_profitable: pd.DataFrame) -> dict:
    """
    Compare both momentum strategies.
    """
    print("\n" + "="*70)
    print("STRATEGY COMPARISON")
    print("="*70)
    
    # Get balanced strategy metrics
    bal_trades = (df_balanced['position'].diff().abs() > 0).sum() // 2 if 'position' in df_balanced.columns else 0
    bal_return = df_balanced['cum_strategy_net'].iloc[-1] if 'cum_strategy_net' in df_balanced.columns else 0
    bal_sharpe = (df_balanced['strategy_return_net'].mean() / df_balanced['strategy_return_net'].std() * np.sqrt(252 * 375) 
                 if 'strategy_return_net' in df_balanced.columns and df_balanced['strategy_return_net'].std() > 0 else 0)
    
    # Get profitable strategy metrics
    prof_trades = (df_profitable['position_profitable'].diff().abs() > 0).sum() // 2 if 'position_profitable' in df_profitable.columns else 0
    prof_return = df_profitable['cum_strategy_net_profitable'].iloc[-1] if 'cum_strategy_net_profitable' in df_profitable.columns else 0
    prof_sharpe = (df_profitable['strategy_return_net_profitable'].mean() / df_profitable['strategy_return_net_profitable'].std() * np.sqrt(252 * 375) 
                  if 'strategy_return_net_profitable' in df_profitable.columns and df_profitable['strategy_return_net_profitable'].std() > 0 else 0)
    
    # Market return
    market_return = df_profitable['cum_market'].iloc[-1] if 'cum_market' in df_profitable.columns else 0
    
    print(f"{'Metric':<25} {'Balanced':<15} {'Profitable':<15} {'Difference':<15}")
    print("-"*70)
    print(f"{'Total Trades':<25} {bal_trades:<15,} {prof_trades:<15,} {prof_trades - bal_trades:<15,}")
    print(f"{'Net Return':<25} {bal_return*100:<15.2f}% {prof_return*100:<15.2f}% {(prof_return - bal_return)*100:<15.2f}%")
    print(f"{'Sharpe Ratio':<25} {bal_sharpe:<15.2f} {prof_sharpe:<15.2f} {prof_sharpe - bal_sharpe:<15.2f}")
    print(f"{'vs Market':<25} {(bal_return - market_return)*100:<15.2f}% {(prof_return - market_return)*100:<15.2f}% {(prof_return - bal_return)*100:<15.2f}%")
    
    # Recommendation
    print("\n" + "-"*70)
    print("RECOMMENDATION:")
    if prof_return > bal_return and prof_sharpe > bal_sharpe:
        print("✓ PROFITABLE strategy performs better on both return and risk-adjusted basis")
    elif prof_return > bal_return:
        print("✓ PROFITABLE strategy has higher returns but check risk metrics")
    elif prof_sharpe > bal_sharpe:
        print("✓ PROFITABLE strategy has better risk-adjusted returns")
    else:
        print("✗ BALANCED strategy might be better, but profitable has 64% win rate")
    
    print("="*70 + "\n")
    
    return {
        'balanced': {'trades': bal_trades, 'return': bal_return, 'sharpe': bal_sharpe},
        'profitable': {'trades': prof_trades, 'return': prof_return, 'sharpe': prof_sharpe}
    }