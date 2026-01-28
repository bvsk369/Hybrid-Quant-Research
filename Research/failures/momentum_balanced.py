"""
PROFITABLE MOMENTUM STRATEGY FIX

Key Issues Fixed:
1. Excessive trading frequency - added proper cooldown
2. Wrong entry/exit logic - momentum needs mean reversion approach
3. Transaction costs killing profits - reduced trade frequency
4. Added profit targets and stop losses
5. Better trend filtering
"""

import numpy as np
import pandas as pd

def backtest_profitable_momentum(
    df: pd.DataFrame,
    momentum_period: int = 20,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.5,
    max_hold_bars: int = 40,
    min_cooldown_bars: int = 10,
    risk_reward_ratio: float = 1.5,
    use_dynamic_stops: bool = True,
    cost_per_trade: float = 0.0002,
    position_size: float = 1.0
) -> pd.DataFrame:
    """
    Profitable momentum strategy with mean reversion elements.
        """
    df = df.copy()
    
    # -------------------------------------------------
    # 1. Calculate Momentum (Rate of Change)
    # -------------------------------------------------
    df['roc'] = df['close'].pct_change(momentum_period)
    
    # Normalize using rolling z-score
    df['momentum_mean'] = df['roc'].rolling(window=60).mean()
    df['momentum_std'] = df['roc'].rolling(window=60).std()
    df['momentum_zscore'] = (df['roc'] - df['momentum_mean']) / df['momentum_std'].replace(0, np.nan)
    
    # Fill NaN values
    df['momentum_zscore'] = df['momentum_zscore'].fillna(0)
    
    # -------------------------------------------------
    # 2. Trend Filter (Smoothed)
    # -------------------------------------------------
    # Calculate EMAs if not present
    if 'ema_12' not in df.columns:
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    if 'ema_26' not in df.columns:
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # Trend strength
    df['ema_distance'] = (df['ema_12'] - df['ema_26']) / df['ema_26'] * 100
    df['trend_strength'] = df['ema_distance'].rolling(window=20).std()
    
    # Only trade when trend is established but not extreme
    strong_uptrend = (df['ema_12'] > df['ema_26']) & (df['trend_strength'] < df['trend_strength'].quantile(0.8))
    strong_downtrend = (df['ema_12'] < df['ema_26']) & (df['trend_strength'] < df['trend_strength'].quantile(0.8))
    
    # -------------------------------------------------
    # 3. Volume Confirmation
    # -------------------------------------------------
    if 'volume' in df.columns:
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        high_volume = df['volume_ratio'] > 1.2
    else:
        high_volume = pd.Series(True, index=df.index)
    
    # -------------------------------------------------
    # 4. Entry Signals (Mean Reversion of Momentum)
    # -------------------------------------------------
    # LONG: Momentum oversold in uptrend
    long_entry = (
        (df['momentum_zscore'] < -entry_zscore) &  # Oversold
        strong_uptrend &                           # In uptrend
        high_volume &                              # Volume confirmation
        (df['momentum_zscore'].shift(1) > df['momentum_zscore'])  # Still dropping (catch the bottom)
    )
    
    # SHORT: Momentum overbought in downtrend
    short_entry = (
        (df['momentum_zscore'] > entry_zscore) &   # Overbought
        strong_downtrend &                         # In downtrend
        high_volume &                              # Volume confirmation
        (df['momentum_zscore'].shift(1) < df['momentum_zscore'])  # Still rising (catch the top)
    )
    
    # -------------------------------------------------
    # 5. Entry Price and Initial Stop/Profit Targets
    # -------------------------------------------------
    df['entry_price'] = np.nan
    df.loc[long_entry, 'entry_price'] = df['close']
    df.loc[short_entry, 'entry_price'] = df['close']
    
    # For longs: stop below recent low
    if 'low' in df.columns:
        recent_low = df['low'].rolling(window=10).min()
        df['stop_loss'] = np.where(long_entry, recent_low * 0.995, np.nan)
        
        # Profit target based on risk-reward
        entry_mask = long_entry.fillna(False)
        risk = df['close'] - df['stop_loss']
        df['profit_target'] = np.where(entry_mask, df['close'] + risk * risk_reward_ratio, np.nan)
    
    # For shorts: stop above recent high
    if 'high' in df.columns:
        recent_high = df['high'].rolling(window=10).max()
        df.loc[short_entry, 'stop_loss'] = recent_high * 1.005
        
        # Profit target for shorts
        risk = df['stop_loss'] - df['close']
        df.loc[short_entry, 'profit_target'] = df['close'] - risk * risk_reward_ratio
    
    # -------------------------------------------------
    # 6. Position Management
    # -------------------------------------------------
    df['signal'] = 0
    df.loc[long_entry, 'signal'] = 1
    df.loc[short_entry, 'signal'] = -1
    
    # Apply cooldown
    df['signal_shifted'] = df['signal'].shift(1).fillna(0)
    
    # Track trades and cooldown
    in_position = False
    position_type = 0  # 1 for long, -1 for short
    entry_bar = 0
    cooldown_counter = 0
    
    df['position'] = 0
    df['exit_reason'] = ''
    
    for i in range(1, len(df)):
        # Check if cooldown period has passed
        if cooldown_counter > 0:
            cooldown_counter -= 1
            df.iloc[i, df.columns.get_loc('position')] = 0
            continue
        
        # Check for exits if in position
        if in_position:
            current_price = df['close'].iloc[i]
            bars_in_trade = i - entry_bar
            
            # Check profit target
            if position_type == 1 and current_price >= df['profit_target'].iloc[entry_bar]:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'profit_target'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
                
            elif position_type == -1 and current_price <= df['profit_target'].iloc[entry_bar]:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'profit_target'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Check stop loss
            if position_type == 1 and current_price <= df['stop_loss'].iloc[entry_bar]:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
                
            elif position_type == -1 and current_price >= df['stop_loss'].iloc[entry_bar]:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Check max hold time
            if bars_in_trade >= max_hold_bars:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'max_hold'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Check momentum exit
            if position_type == 1 and df['momentum_zscore'].iloc[i] > exit_zscore:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
                
            elif position_type == -1 and df['momentum_zscore'].iloc[i] < -exit_zscore:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown_counter = min_cooldown_bars
                continue
            
            # Otherwise maintain position
            df.iloc[i, df.columns.get_loc('position')] = position_type
            
        # Check for new entries if not in position
        elif not in_position and df['signal_shifted'].iloc[i] != 0 and cooldown_counter == 0:
            position_type = df['signal_shifted'].iloc[i]
            df.iloc[i, df.columns.get_loc('position')] = position_type
            in_position = True
            entry_bar = i
    
    # -------------------------------------------------
    # 7. Calculate Returns
    # -------------------------------------------------
    if 'log_return' not in df.columns:
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    df['strategy_return'] = df['position'] * df['log_return']
    
    # Calculate transaction costs (only on position changes)
    df['position_change'] = df['position'].diff().abs().fillna(0)
    df['transaction_cost'] = cost_per_trade * df['position_change']
    df['strategy_return_net'] = df['strategy_return'] - df['transaction_cost']
    
    # Cumulative returns
    df['cum_strategy'] = df['strategy_return'].cumsum()
    df['cum_strategy_net'] = df['strategy_return_net'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()
    
    return df


def analyze_trades(df: pd.DataFrame) -> dict:
    """
    Detailed trade analysis.
    """
    # Find trade entries and exits
    df['trade_id'] = (df['position'].diff() != 0).cumsum()
    
    trade_results = []
    in_trade = False
    current_trade = {}
    
    for i in range(len(df)):
        if not in_trade and df['position'].iloc[i] != 0:
            # Trade entry
            in_trade = True
            current_trade = {
                'entry_bar': i,
                'entry_price': df['close'].iloc[i],
                'position': df['position'].iloc[i],
                'entry_momentum': df['momentum_zscore'].iloc[i]
            }
        elif in_trade and df['position'].iloc[i] == 0:
            # Trade exit
            current_trade.update({
                'exit_bar': i,
                'exit_price': df['close'].iloc[i],
                'exit_momentum': df['momentum_zscore'].iloc[i],
                'exit_reason': df['exit_reason'].iloc[i] if 'exit_reason' in df.columns else 'unknown',
                'duration': i - current_trade['entry_bar']
            })
            
            # Calculate P&L
            if current_trade['position'] == 1:  # Long
                current_trade['return'] = np.log(current_trade['exit_price'] / current_trade['entry_price'])
            else:  # Short
                current_trade['return'] = np.log(current_trade['entry_price'] / current_trade['exit_price'])
            
            trade_results.append(current_trade.copy())
            in_trade = False
    
    if trade_results:
        trades_df = pd.DataFrame(trade_results)
        
        print("\n" + "="*60)
        print("TRADE ANALYSIS")
        print("="*60)
        print(f"Total Trades: {len(trades_df)}")
        print(f"Win Rate: {(trades_df['return'] > 0).mean()*100:.1f}%")
        print(f"Avg Win: {trades_df[trades_df['return'] > 0]['return'].mean()*100:.2f}%")
        print(f"Avg Loss: {trades_df[trades_df['return'] <= 0]['return'].mean()*100:.2f}%")
        print(f"Profit Factor: {-trades_df[trades_df['return'] > 0]['return'].sum() / trades_df[trades_df['return'] <= 0]['return'].sum():.2f}")
        print(f"Avg Duration: {trades_df['duration'].mean():.0f} bars")
        
        if 'exit_reason' in trades_df.columns:
            print("\nExit Reasons:")
            print(trades_df['exit_reason'].value_counts())
        
        return trades_df
    
    return {}


def optimize_parameters(df: pd.DataFrame, n_trials: int = 50) -> dict:
    """
    Simple parameter optimization.
    """
    best_sharpe = -np.inf
    best_params = {}
    
    # Parameter ranges to test
    entry_thresholds = [1.8, 2.0, 2.2, 2.5]
    hold_periods = [20, 30, 40, 50]
    rr_ratios = [1.0, 1.5, 2.0]
    
    for entry in entry_thresholds:
        for hold in hold_periods:
            for rr in rr_ratios:
                df_test = backtest_profitable_momentum(
                    df,
                    entry_zscore=entry,
                    max_hold_bars=hold,
                    risk_reward_ratio=rr
                )
                
                # Calculate Sharpe ratio
                returns = df_test['strategy_return_net']
                if len(returns) > 1 and returns.std() > 0:
                    sharpe = returns.mean() / returns.std() * np.sqrt(252 * 375)
                else:
                    sharpe = -np.inf
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = {
                        'entry_zscore': entry,
                        'max_hold_bars': hold,
                        'risk_reward_ratio': rr,
                        'sharpe': sharpe
                    }
    
    print(f"\nBest Parameters: {best_params}")
    return best_params


# Usage:
# Load your data first
# df = pd.read_csv('data file.csv', parse_dates=True)
# 
# # Run the profitable strategy
# df_results = backtest_profitable_momentum(df)
# 
# # Analyze trades
# trades = analyze_trades(df_results)
# 
# # Optional: Optimize parameters
# best_params = optimize_parameters(df)