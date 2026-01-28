"""
ROBUST MOMENTUM STRATEGY WITH ADVANCED RISK MANAGEMENT

Key Features:
1. Volatility-based position sizing (ATR-based)
2. Trailing stops with momentum confirmation
3. Drawdown limits and circuit breakers
4. Dynamic stop-loss based on volatility
5. Portfolio-level risk controls
6. Better entry/exit timing with multiple confirmations

This addresses the high drawdown issue while maintaining profitability.
"""

import numpy as np
import pandas as pd


def backtest_momentum_robust(
    df: pd.DataFrame,
    # Entry/Exit Parameters
    momentum_period: int = 20,
    entry_zscore: float = 1.8,      # Lower threshold for more opportunities
    exit_zscore: float = 0.3,       # Exit when momentum normalizes
    max_hold_bars: int = 50,
    min_cooldown_bars: int = 8,
    
    # Risk Management Parameters
    max_position_size: float = 1.0,  # Maximum position size
    base_position_size: float = 0.5,  # Base position size
    atr_stop_multiplier: float = 2.0,  # ATR multiplier for stop loss
    trailing_stop_atr: float = 1.5,    # Trailing stop in ATR units
    max_drawdown_limit: float = 0.15,   # 15% max drawdown before reducing size
    volatility_scaling: bool = True,   # Scale position by volatility
    
    # Transaction Costs
    cost_per_trade: float = 0.0002,
    
    # Filters
    use_trend_filter: bool = True,
    use_volume_filter: bool = True,
    use_momentum_confirmation: bool = True,
    
    # MACD Confirmation
    use_macd: bool = True,
    
    # RSI Filter (avoid extreme overbought/oversold)
    rsi_period: int = 14,
    rsi_upper: float = 75,
    rsi_lower: float = 25,
) -> pd.DataFrame:
    """
    Robust momentum strategy with comprehensive risk management.
    
    IMPORTANT: This function assumes all features are already created!
    Required features from features_2.py:
    - momentum_zscore_20, atr_14, rsi_14, ema_12, ema_26
    - macd_line, macd_signal, macd_histogram
    
    Required features from feature.py:
    - log_return, vol_20
    
    Usage:
        from features_2 import add_all_features
        from feature import add_log_returns, add_rolling_volatility
        df = add_log_returns(df)
        df = add_rolling_volatility(df)
        df = add_all_features(df)  # Creates all features_2.py features
        df_results = backtest_momentum_robust(df)
    
    Strategy Logic:
    - Enter long when momentum is strong AND trend is up AND not overbought
    - Enter short when momentum is weak AND trend is down AND not oversold
    - Use ATR-based stops for dynamic risk management
    - Scale position size based on volatility and recent performance
    - Implement trailing stops to protect profits
    - Circuit breaker: reduce trading if drawdown exceeds limit
    """
    df = df.copy()
    
    # ============================================================
    # 0. VERIFY REQUIRED FEATURES EXIST (from features_2.py)
    # ============================================================
    # Features from features_2.py that should already exist:
    required_features = ['momentum_zscore_20', 'atr_14', 'rsi_14', 'ema_12', 'ema_26', 'macd_line', 'macd_signal', 'macd_histogram']
    missing_features = [f for f in required_features if f not in df.columns]
    
    if missing_features:
        raise ValueError(
            f"Missing required features from features_2.py: {missing_features}\n"
            f"Please run: from features_2 import add_all_features; df = add_all_features(df)"
        )
    
    # Features from feature.py (first features) that should exist:
    basic_features = ['log_return', 'vol_20']
    missing_basic = [f for f in basic_features if f not in df.columns]
    if missing_basic:
        raise ValueError(
            f"Missing required basic features: {missing_basic}\n"
            f"Please run feature.py functions first"
        )
    
    # ============================================================
    # 1. USE EXISTING MOMENTUM INDICATORS (from features_2.py)
    # ============================================================
    momentum_col = 'momentum_zscore_20'  # Already created in features_2.py
    
    # ============================================================
    # 2. USE EXISTING RISK MANAGEMENT INDICATORS
    # ============================================================
    # ATR already exists from features_2.py: 'atr_14'
    # Vol_20 already exists from feature.py
    
    # ============================================================
    # 3. USE EXISTING TREND FILTERS (from features_2.py)
    # ============================================================
    if use_trend_filter:
        # EMA_12 and EMA_26 already exist from features_2.py
        uptrend = df['ema_12'] > df['ema_26']
        downtrend = df['ema_12'] < df['ema_26']
        
        # MACD already exists from features_2.py
        if use_macd:
            macd_bullish = df['macd_histogram'] > 0
            macd_bearish = df['macd_histogram'] < 0
            uptrend = uptrend & macd_bullish
            downtrend = downtrend & macd_bearish
    else:
        uptrend = pd.Series(True, index=df.index)
        downtrend = pd.Series(True, index=df.index)
    
    # ============================================================
    # 4. USE EXISTING RSI FILTER (from features_2.py)
    # ============================================================
    # RSI_14 already exists from features_2.py
    rsi_ok_long = df['rsi_14'] < rsi_upper
    rsi_ok_short = df['rsi_14'] > rsi_lower
    
    # ============================================================
    # 5. VOLUME FILTER
    # ============================================================
    if use_volume_filter and 'volume' in df.columns:
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        high_volume = df['volume_ratio'] > 1.1  # At least 10% above average
    else:
        high_volume = pd.Series(True, index=df.index)
    
    # ============================================================
    # 6. MOMENTUM CONFIRMATION
    # ============================================================
    if use_momentum_confirmation:
        # Momentum should be accelerating (not decelerating)
        momentum_change = df[momentum_col].diff()
        momentum_accelerating_long = momentum_change > 0  # Momentum increasing
        momentum_accelerating_short = momentum_change < 0  # Momentum decreasing
    else:
        momentum_accelerating_long = pd.Series(True, index=df.index)
        momentum_accelerating_short = pd.Series(True, index=df.index)
    
    # ============================================================
    # 7. ENTRY SIGNALS
    # ============================================================
    # LONG: Strong positive momentum in uptrend
    long_entry = (
        (df[momentum_col] > entry_zscore) &  # Strong momentum
        uptrend &                              # Uptrend
        rsi_ok_long &                          # Not extremely overbought
        high_volume &                          # Volume confirmation
        momentum_accelerating_long              # Momentum accelerating
    )
    
    # SHORT: Strong negative momentum in downtrend
    short_entry = (
        (df[momentum_col] < -entry_zscore) &  # Strong negative momentum
        downtrend &                             # Downtrend
        rsi_ok_short &                          # Not extremely oversold
        high_volume &                           # Volume confirmation
        momentum_accelerating_short              # Momentum accelerating
    )
    
    # ============================================================
    # 8. POSITION MANAGEMENT WITH RISK CONTROLS
    # ============================================================
    df['signal'] = 0
    df.loc[long_entry, 'signal'] = 1
    df.loc[short_entry, 'signal'] = -1
    
    # Shift signals for next-bar execution
    df['signal'] = df['signal'].shift(1).fillna(0)
    
    # Initialize position tracking
    df['position'] = 0.0
    df['position_size'] = 0.0
    df['entry_price'] = np.nan
    df['stop_loss'] = np.nan
    df['trailing_stop'] = np.nan
    df['exit_reason'] = ''
    
    # State variables
    in_position = False
    position_type = 0  # 1=long, -1=short
    entry_idx = 0
    entry_price = 0.0
    stop_loss_price = 0.0
    trailing_stop_price = 0.0
    cooldown = 0
    
    # Portfolio-level tracking
    cumulative_return = 0.0
    peak_cumulative = 0.0
    current_drawdown = 0.0
    
    # Iterate through bars
    for i in range(1, len(df)):
        # Update cumulative return for drawdown tracking
        # log_return already exists from feature.py (validated above)
        cumulative_return += df['log_return'].iloc[i]
        peak_cumulative = max(peak_cumulative, cumulative_return)
        current_drawdown = peak_cumulative - cumulative_return
        
        # Cooldown period
        if cooldown > 0:
            cooldown -= 1
            df.iloc[i, df.columns.get_loc('position')] = 0
            df.iloc[i, df.columns.get_loc('position_size')] = 0
            continue
        
        # Check if we're in a position
        if in_position:
            current_price = df['close'].iloc[i]
            bars_in_trade = i - entry_idx
            
            # Calculate position size based on drawdown (circuit breaker)
            if current_drawdown > max_drawdown_limit:
                size_multiplier = max(0.3, 1.0 - (current_drawdown - max_drawdown_limit) / max_drawdown_limit)
            else:
                size_multiplier = 1.0
            
            # Volatility-based position sizing (vol_20 already exists from feature.py)
            if volatility_scaling:
                vol_factor = df['vol_20'].iloc[entry_idx]
                vol_median = df['vol_20'].rolling(60).median().iloc[entry_idx]
                if vol_factor > 0 and vol_median > 0:
                    vol_scaling = min(1.5, max(0.5, vol_median / vol_factor))
                else:
                    vol_scaling = 1.0
            else:
                vol_scaling = 1.0
            
            position_size = base_position_size * size_multiplier * vol_scaling
            position_size = min(position_size, max_position_size)
            
            # Update trailing stop (atr_14 already exists from features_2.py)
            atr_value = df['atr_14'].iloc[i]
            
            if position_type == 1:  # Long
                # Update trailing stop (highest price - trailing_stop_atr * ATR)
                if i == entry_idx + 1:
                    trailing_stop_price = current_price - (trailing_stop_atr * atr_value)
                else:
                    new_trailing = current_price - (trailing_stop_atr * atr_value)
                    trailing_stop_price = max(trailing_stop_price, new_trailing)
                
                # Check trailing stop
                if current_price <= trailing_stop_price:
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    df.iloc[i, df.columns.get_loc('position_size')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'trailing_stop'
                    in_position = False
                    cooldown = min_cooldown_bars
                    continue
                
                # Check stop loss
                if current_price <= stop_loss_price:
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    df.iloc[i, df.columns.get_loc('position_size')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                    in_position = False
                    cooldown = min_cooldown_bars
                    continue
                
            elif position_type == -1:  # Short
                # Update trailing stop (lowest price + trailing_stop_atr * ATR)
                if i == entry_idx + 1:
                    trailing_stop_price = current_price + (trailing_stop_atr * atr_value)
                else:
                    new_trailing = current_price + (trailing_stop_atr * atr_value)
                    trailing_stop_price = min(trailing_stop_price, new_trailing)
                
                # Check trailing stop
                if current_price >= trailing_stop_price:
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    df.iloc[i, df.columns.get_loc('position_size')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'trailing_stop'
                    in_position = False
                    cooldown = min_cooldown_bars
                    continue
                
                # Check stop loss
                if current_price >= stop_loss_price:
                    df.iloc[i, df.columns.get_loc('position')] = 0
                    df.iloc[i, df.columns.get_loc('position_size')] = 0
                    df.iloc[i, df.columns.get_loc('exit_reason')] = 'stop_loss'
                    in_position = False
                    cooldown = min_cooldown_bars
                    continue
            
            # Momentum exit
            current_momentum = df[momentum_col].iloc[i]
            if position_type == 1 and current_momentum < exit_zscore:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('position_size')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown = min_cooldown_bars
                continue
            elif position_type == -1 and current_momentum > -exit_zscore:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('position_size')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'momentum_exit'
                in_position = False
                cooldown = min_cooldown_bars
                continue
            
            # Max hold time
            if bars_in_trade >= max_hold_bars:
                df.iloc[i, df.columns.get_loc('position')] = 0
                df.iloc[i, df.columns.get_loc('position_size')] = 0
                df.iloc[i, df.columns.get_loc('exit_reason')] = 'max_hold'
                in_position = False
                cooldown = min_cooldown_bars
                continue
            
            # Maintain position
            df.iloc[i, df.columns.get_loc('position')] = position_type
            df.iloc[i, df.columns.get_loc('position_size')] = position_size
            df.iloc[i, df.columns.get_loc('trailing_stop')] = trailing_stop_price
        
        # Check for new entry
        elif not in_position and df['signal'].iloc[i] != 0 and cooldown == 0:
            # Check drawdown limit before entering
            if current_drawdown > max_drawdown_limit * 1.5:  # Circuit breaker
                continue
            
            position_type = int(df['signal'].iloc[i])
            entry_idx = i
            entry_price = df['close'].iloc[i]
            
            # Calculate position size
            if current_drawdown > max_drawdown_limit:
                size_multiplier = max(0.3, 1.0 - (current_drawdown - max_drawdown_limit) / max_drawdown_limit)
            else:
                size_multiplier = 1.0
            
            # Volatility-based position sizing (vol_20 already exists from feature.py)
            if volatility_scaling:
                vol_factor = df['vol_20'].iloc[i]
                vol_median = df['vol_20'].rolling(60).median().iloc[i]
                if vol_factor > 0 and vol_median > 0:
                    vol_scaling = min(1.5, max(0.5, vol_median / vol_factor))
                else:
                    vol_scaling = 1.0
            else:
                vol_scaling = 1.0
            
            position_size = base_position_size * size_multiplier * vol_scaling
            position_size = min(position_size, max_position_size)
            
            # Set stop loss based on ATR (atr_14 already exists from features_2.py)
            atr_value = df['atr_14'].iloc[i]
            if position_type == 1:  # Long
                stop_loss_price = entry_price - (atr_stop_multiplier * atr_value)
                trailing_stop_price = entry_price - (trailing_stop_atr * atr_value)
            else:  # Short
                stop_loss_price = entry_price + (atr_stop_multiplier * atr_value)
                trailing_stop_price = entry_price + (trailing_stop_atr * atr_value)
            
            df.iloc[i, df.columns.get_loc('position')] = position_type
            df.iloc[i, df.columns.get_loc('position_size')] = position_size
            df.iloc[i, df.columns.get_loc('entry_price')] = entry_price
            df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
            df.iloc[i, df.columns.get_loc('trailing_stop')] = trailing_stop_price
            in_position = True
    
    # ============================================================
    # 9. CALCULATE RETURNS (with position sizing)
    # ============================================================
    # log_return already exists from feature.py
    
    # Strategy return = position * position_size * log_return
    df['strategy_return'] = df['position'] * df['position_size'] * df['log_return']
    
    # Transaction costs (only on position changes)
    df['position_change'] = (df['position'].diff().abs() > 0).astype(int)
    df['transaction_cost'] = df['position_change'] * cost_per_trade * df['position_size'].abs()
    
    # Net returns
    df['strategy_return_net'] = df['strategy_return'] - df['transaction_cost']
    
    # Cumulative returns
    df['cum_strategy'] = df['strategy_return'].cumsum()
    df['cum_strategy_net'] = df['strategy_return_net'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()
    
    return df


def analyze_momentum_robust(df: pd.DataFrame) -> dict:
    """
    Comprehensive analysis of robust momentum strategy.
    """
    # Count trades
    position_changes = df['position'].diff().abs()
    trades = (position_changes > 0).sum() // 2
    
    # Returns
    gross = df['cum_strategy'].iloc[-1] if len(df) > 0 else 0
    net = df['cum_strategy_net'].iloc[-1] if len(df) > 0 else 0
    market = df['cum_market'].iloc[-1] if len(df) > 0 else 0
    
    # Sharpe Ratio
    if 'strategy_return_net' in df.columns and len(df) > 1:
        returns = df['strategy_return_net']
        if returns.std() > 0:
            # Annualized Sharpe (assuming 1-minute bars, 375 bars/day, 252 trading days)
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 375)
        else:
            sharpe = 0
    else:
        sharpe = 0
    
    # Max Drawdown
    if 'cum_strategy_net' in df.columns and len(df) > 0:
        cumulative = df['cum_strategy_net']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max.replace(0, np.nan)
        max_dd = drawdown.min()
        max_dd_pct = max_dd * 100 if not np.isnan(max_dd) else 0
    else:
        max_dd = 0
        max_dd_pct = 0
    
    # Calmar Ratio (return / max drawdown)
    calmar = abs(net / max_dd) if max_dd < 0 else 0
    
    # Win Rate
    trades_list = []
    in_trade = False
    current_trade = {}
    
    for i in range(len(df)):
        if not in_trade and df['position'].iloc[i] != 0:
            in_trade = True
            current_trade = {
                'entry': i,
                'entry_price': df['close'].iloc[i],
                'position': df['position'].iloc[i]
            }
        elif in_trade and df['position'].iloc[i] == 0 and df['position'].iloc[i-1] != 0:
            current_trade['exit'] = i
            current_trade['exit_price'] = df['close'].iloc[i]
            if current_trade['position'] == 1:
                current_trade['return'] = np.log(current_trade['exit_price'] / current_trade['entry_price'])
            else:
                current_trade['return'] = np.log(current_trade['entry_price'] / current_trade['exit_price'])
            trades_list.append(current_trade.copy())
            in_trade = False
    
    if trades_list:
        trades_df = pd.DataFrame(trades_list)
        win_rate = (trades_df['return'] > 0).mean() * 100
        avg_win = trades_df[trades_df['return'] > 0]['return'].mean() if any(trades_df['return'] > 0) else 0
        avg_loss = trades_df[trades_df['return'] <= 0]['return'].mean() if any(trades_df['return'] <= 0) else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss < 0 else 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
    
    # Transaction costs
    total_costs = df['transaction_cost'].sum() if 'transaction_cost' in df.columns else 0
    
    # Exit reasons
    exit_reasons = {}
    if 'exit_reason' in df.columns:
        exit_reasons = df['exit_reason'].value_counts().to_dict()
    
    # Print summary
    print("\n" + "="*70)
    print("ROBUST MOMENTUM STRATEGY - PERFORMANCE SUMMARY")
    print("="*70)
    print(f"Total Trades:          {trades:,}")
    print(f"Win Rate:              {win_rate:.1f}%")
    print(f"Average Win:           {avg_win*100:.3f}%")
    print(f"Average Loss:          {avg_loss*100:.3f}%")
    print(f"Profit Factor:         {profit_factor:.2f}")
    print(f"\nGross Return:          {gross:.4f} ({gross*100:.2f}%)")
    print(f"Net Return:            {net:.4f} ({net*100:.2f}%)")
    print(f"Market Return:         {market:.4f} ({market*100:.2f}%)")
    print(f"Outperformance:        {(net - market)*100:.2f}%")
    print(f"\nSharpe Ratio:          {sharpe:.2f}")
    print(f"Calmar Ratio:          {calmar:.2f}")
    print(f"Max Drawdown:          {max_dd:.4f} ({max_dd_pct:.2f}%)")
    print(f"Total Costs:           {total_costs:.4f}")
    
    if exit_reasons:
        print(f"\nExit Reasons:")
        for reason, count in exit_reasons.items():
            if reason:
                pct = count / sum(exit_reasons.values()) * 100
                print(f"  {reason:15s}: {count:6d} ({pct:.1f}%)")
    
    print("="*70 + "\n")
    
    return {
        'trades': trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'gross_return': gross,
        'net_return': net,
        'market_return': market,
        'sharpe': sharpe,
        'calmar': calmar,
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd_pct,
        'total_costs': total_costs,
        'exit_reasons': exit_reasons
    }
