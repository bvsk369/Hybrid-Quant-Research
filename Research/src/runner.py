import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
try:
    from features import generate_features
    from cleaning import clean_equity_data
    from regimes import detect_regime
    from allocator import allocate_signal
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
    print("Ensure cleaning.py, features.py, regimes.py, and allocator.py are in the same folder.")
    exit()

# ---------------------------------------------------------
# 1. DATA LOADING
# ---------------------------------------------------------
def load_data(path: str) -> pd.DataFrame:
    """
    Loads raw market data and standardizes columns.
    """
    try:
        df = pd.read_csv(path, parse_dates=True, index_col=0)
        
        # Standardize columns to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        required_raw = ['open', 'high', 'low', 'close']
        missing = set(required_raw) - set(df.columns)
        
        if missing:
            raise ValueError(f"CSV is missing raw columns: {missing}")
            
        print(f"✅ Data Loaded: {len(df)} rows")
        return df
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        exit()

# ---------------------------------------------------------
# 2. ENHANCED BACKTEST ENGINE (with stop-loss & position sizing)
# ---------------------------------------------------------
def run_enhanced_backtest(df: pd.DataFrame, signals_df: pd.DataFrame, 
                          cost_per_trade: float = 0.0001) -> pd.DataFrame:
    """
    Run backtest with proper stop-loss enforcement, trailing stops, and position sizing.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Data with OHLC and features
    signals_df : pd.DataFrame
        Output from allocate_signal(df, use_enhanced=True)
        Contains: signal, stop_loss, take_profit, trailing_stop, position_size
    cost_per_trade : float
        Transaction cost as fraction (0.0001 = 0.01%)
    """
    df = df.copy()
    
    # Ensure log_return exists
    if 'log_return' not in df.columns:
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    # Initialize tracking columns
    n = len(df)
    position = np.zeros(n)           # Actual position held
    position_size = np.zeros(n)      # Position size (0 to 1)
    entry_price = np.zeros(n)        # Entry price for current position
    stop_price = np.zeros(n)         # Current stop loss
    trailing_stop = np.zeros(n)      # Trailing stop
    trade_pnl = np.zeros(n)          # P&L from trades
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    signal = signals_df['signal'].values
    sig_stop_loss = signals_df['stop_loss'].values
    sig_trailing = signals_df['trailing_stop'].values if 'trailing_stop' in signals_df.columns else np.full(n, np.nan)
    sig_take_profit = signals_df['take_profit'].values if 'take_profit' in signals_df.columns else np.full(n, np.nan)
    sig_position_size = signals_df['position_size'].values
    
    current_position = 0
    current_entry = 0.0
    current_stop = 0.0
    current_trailing = 0.0
    current_take_profit = 0.0
    current_size = 0.0
    highest_since_entry = 0.0
    lowest_since_entry = float('inf')
    
    trade_count = 0
    winning_trades = 0
    losing_trades = 0
    
    for i in range(1, n):
        # Check for stop-loss / take-profit hits FIRST (before new signals)
        if current_position != 0:
            hit_stop = False
            hit_take_profit = False
            exit_price = close[i]
            
            if current_position == 1:  # Long position
                # Update trailing stop (move up as price rises)
                if high[i] > highest_since_entry:
                    highest_since_entry = high[i]
                    # Trailing stop moved up
                    if not np.isnan(current_trailing) and current_trailing > 0:
                        new_trail = highest_since_entry - (current_entry - current_trailing)
                        current_stop = max(current_stop, new_trail)
                
                # Check stop hit
                if low[i] <= current_stop:
                    hit_stop = True
                    exit_price = current_stop
                # Check take profit
                elif not np.isnan(current_take_profit) and high[i] >= current_take_profit:
                    hit_take_profit = True
                    exit_price = current_take_profit
                    
            elif current_position == -1:  # Short position
                # Update trailing stop (move down as price falls)
                if low[i] < lowest_since_entry:
                    lowest_since_entry = low[i]
                    if not np.isnan(current_trailing) and current_trailing > 0:
                        new_trail = lowest_since_entry + (current_trailing - current_entry)
                        current_stop = min(current_stop, new_trail)
                
                # Check stop hit
                if high[i] >= current_stop:
                    hit_stop = True
                    exit_price = current_stop
                # Check take profit
                elif not np.isnan(current_take_profit) and low[i] <= current_take_profit:
                    hit_take_profit = True
                    exit_price = current_take_profit
            
            # Exit on stop or take profit
            if hit_stop or hit_take_profit:
                # Calculate P&L
                if current_position == 1:
                    pnl = (exit_price - current_entry) / current_entry * current_size
                else:
                    pnl = (current_entry - exit_price) / current_entry * current_size
                
                trade_pnl[i] = pnl
                trade_count += 1
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                
                # Reset position
                current_position = 0
                current_entry = 0.0
                current_stop = 0.0
                current_size = 0.0
        
        # Process new signals (only if not already in position)
        new_signal = signal[i]
        
        if current_position == 0 and new_signal != 0:
            # Enter new position
            current_position = int(new_signal)
            current_entry = close[i]
            current_stop = sig_stop_loss[i] if not np.isnan(sig_stop_loss[i]) else 0
            current_trailing = sig_trailing[i] if not np.isnan(sig_trailing[i]) else 0
            current_take_profit = sig_take_profit[i] if not np.isnan(sig_take_profit[i]) else np.nan
            current_size = sig_position_size[i]
            highest_since_entry = high[i]
            lowest_since_entry = low[i]
            
        elif current_position != 0 and new_signal == 0:
            # Exit signal (momentum weakened)
            pnl = 0
            if current_position == 1:
                pnl = (close[i] - current_entry) / current_entry * current_size
            else:
                pnl = (current_entry - close[i]) / current_entry * current_size
            
            trade_pnl[i] = pnl
            trade_count += 1
            if pnl > 0:
                winning_trades += 1
            else:
                losing_trades += 1
            
            current_position = 0
            current_entry = 0.0
            current_size = 0.0
        
        # Record current state
        position[i] = current_position * current_size
        position_size[i] = current_size
        entry_price[i] = current_entry
        stop_price[i] = current_stop
    
    # Store results in DataFrame
    df['position'] = position
    df['position_size'] = position_size
    df['entry_price'] = entry_price
    df['stop_price'] = stop_price
    df['trade_pnl'] = trade_pnl
    
    # Calculate cumulative returns
    df['cum_pnl'] = df['trade_pnl'].cumsum()
    df['equity'] = 1 + df['cum_pnl']
    
    # Market returns for comparison
    df['cum_market'] = df['log_return'].cumsum()
    
    return df, trade_count, winning_trades, losing_trades

# ---------------------------------------------------------
# 3. PERFORMANCE ANALYSIS
# ---------------------------------------------------------
def calculate_enhanced_performance(df: pd.DataFrame, trade_count: int, 
                                   winning_trades: int, losing_trades: int):
    """
    Calculate and print performance metrics for enhanced backtest.
    """
    # Total Return
    total_ret = (df['equity'].iloc[-1] - 1) * 100
    market_ret = (np.exp(df['cum_market'].iloc[-1]) - 1) * 100
    
    # Max Drawdown
    running_max = df['equity'].cummax()
    drawdown = (df['equity'] - running_max) / running_max
    max_dd = drawdown.min() * 100
    
    # Win Rate
    win_rate = (winning_trades / trade_count * 100) if trade_count > 0 else 0
    
    # Sharpe Ratio (using trade P&Ls, not position returns)
    trade_returns = df['trade_pnl'][df['trade_pnl'] != 0]
    sharpe = 0
    if len(trade_returns) > 1 and trade_returns.std() > 0:
        # Annualize based on average trade frequency
        trades_per_year = len(trade_returns) / (len(df) / (252 * 75))  # Assume 5-min bars, 75 per day
        sharpe = (trade_returns.mean() / trade_returns.std()) * np.sqrt(max(trades_per_year, 1))
    
    # Profit Factor
    gross_profit = df['trade_pnl'][df['trade_pnl'] > 0].sum()
    gross_loss = abs(df['trade_pnl'][df['trade_pnl'] < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Average Win/Loss
    avg_win = trade_returns[trade_returns > 0].mean() * 100 if winning_trades > 0 else 0
    avg_loss = trade_returns[trade_returns < 0].mean() * 100 if losing_trades > 0 else 0
    
    print("\n" + "="*50)
    print("📊 ENHANCED STRATEGY PERFORMANCE REPORT")
    print("="*50)
    print(f"Strategy Return:   {total_ret:8.2f}%")
    print(f"Market Return:     {market_ret:8.2f}%")
    print(f"Max Drawdown:      {max_dd:8.2f}%")
    print(f"Sharpe Ratio:      {sharpe:8.2f}")
    print("-"*50)
    print(f"Total Trades:      {trade_count:8d}")
    print(f"Win Rate:          {win_rate:8.2f}%")
    print(f"Profit Factor:     {profit_factor:8.2f}")
    print(f"Avg Win:           {avg_win:8.2f}%")
    print(f"Avg Loss:          {avg_loss:8.2f}%")
    
    # Regime-wise Performance
    print("\n📌 Regime-wise Returns:")
    if 'regime' in df.columns:
        for r in sorted(df['regime'].unique()):
            sub = df[df['regime'] == r]
            regime_ret = sub['trade_pnl'].sum() * 100
            regime_trades = (sub['trade_pnl'] != 0).sum()
            print(f"  {r:10s}: {regime_ret:7.2f}%  (trades={regime_trades})")
    
    print("="*50)
    
    return {
        'total_return': total_ret,
        'market_return': market_ret,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': trade_count
    }

# ---------------------------------------------------------
# 4. VISUALIZATION
# ---------------------------------------------------------
def plot_enhanced_results(df: pd.DataFrame):
    """
    Visualizes Enhanced Strategy Results.
    """
    # Downsample for plotting
    if len(df) > 100000:
        plot_df = df.iloc[::10]
    else:
        plot_df = df

    plt.figure(figsize=(14, 12))
    
    # Plot 1: Equity Curve
    plt.subplot(4, 1, 1)
    plt.plot(plot_df['equity'], label='Enhanced Strategy', color='green', linewidth=1.5)
    plt.plot(np.exp(plot_df['cum_market']), label='Buy & Hold', color='gray', alpha=0.5)
    plt.axhline(y=1, color='black', linestyle='--', alpha=0.3)
    plt.title('Equity Curve (Enhanced Strategy with Risk Management)')
    plt.ylabel('Equity')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Drawdown
    plt.subplot(4, 1, 2)
    running_max = plot_df['equity'].cummax()
    dd = (plot_df['equity'] - running_max) / running_max * 100
    plt.fill_between(plot_df.index, dd, 0, color='red', alpha=0.3)
    plt.title('Drawdown Profile')
    plt.ylabel('Drawdown %')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Trade P&L Distribution
    plt.subplot(4, 1, 3)
    trade_pnls = df['trade_pnl'][df['trade_pnl'] != 0] * 100
    if len(trade_pnls) > 0:
        plt.hist(trade_pnls, bins=50, color='blue', alpha=0.7, edgecolor='black')
        plt.axvline(x=0, color='red', linestyle='--')
        plt.axvline(x=trade_pnls.mean(), color='green', linestyle='--', label=f'Mean: {trade_pnls.mean():.2f}%')
    plt.title('Trade P&L Distribution')
    plt.xlabel('P&L %')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Regime Map
    plt.subplot(4, 1, 4)
    plt.plot(plot_df['close'], color='black', linewidth=1)
    plt.title('Market Regimes & Price')
    
    y_min, y_max = plot_df['close'].min(), plot_df['close'].max()
    colors = {
        'LV_TREND': 'lightgreen', 
        'HV_TREND': 'orange', 
        'LV_RANGE': 'lightblue', 
        'HV_RANGE': 'pink',
        'UNDEFINED': 'white'
    }
    
    for regime, color in colors.items():
        mask = plot_df['regime'] == regime
        if mask.any():
            plt.fill_between(plot_df.index, y_min, y_max, where=mask, 
                           color=color, alpha=0.3, label=regime)
    
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper left')
    
    plt.tight_layout()
    plt.show()

# ---------------------------------------------------------
# 5. MAIN PIPELINE (ENHANCED)
# ---------------------------------------------------------
def run_pipeline_enhanced(data_path: str):
    """
    Run the full pipeline with enhanced strategies.
    """
    # 1. Load and clean data
    df = load_data(data_path)
    
    print("Cleaning Data...")
    df = clean_equity_data(df)
    
    # 2. Feature Generation
    print("Generating Features...")
    df = generate_features(df)
    
    # 3. Regime Detection
    print("Detecting Regimes...")
    df['regime'] = detect_regime(df)
    
    print("\nRegime Distribution:")
    print(df['regime'].value_counts())
    
    # 4. Enhanced Signal Allocation (with stop-loss, position sizing)
    print("\nAllocating Enhanced Signals...")
    signals_df = allocate_signal(df, use_enhanced=True)
    
    total_signals = (signals_df['signal'] != 0).sum()
    print(f"Total Signals Generated: {total_signals}")
    
    # 5. Run Enhanced Backtest (with stop-loss enforcement)
    print("\nRunning Enhanced Backtest...")
    df, trade_count, winning_trades, losing_trades = run_enhanced_backtest(df, signals_df)
    
    # 6. Calculate Performance
    metrics = calculate_enhanced_performance(df, trade_count, winning_trades, losing_trades)
    
    # 7. Visualize
    plot_enhanced_results(df)
    
    return df, metrics

# ---------------------------------------------------------
# 6. LEGACY PIPELINE (for comparison)
# ---------------------------------------------------------
def run_pipeline_legacy(data_path: str):
    """
    Original pipeline without risk management (for comparison).
    """
    df = load_data(data_path)
    
    print("Cleaning Data...")
    df = clean_equity_data(df)
    
    print("Generating Features...")
    df = generate_features(df)
    
    print("Detecting Regimes...")
    df['regime'] = detect_regime(df)
    
    print("Allocating Signals (Legacy)...")
    df['signal'] = allocate_signal(df, use_enhanced=False)
    
    # Simple performance calculation
    if 'log_return' not in df.columns:
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    df['position'] = df['signal'].shift(1).fillna(0)
    df['strategy_ret'] = df['position'] * df['log_return']
    df['cum_strategy'] = df['strategy_ret'].cumsum()
    df['cum_market'] = df['log_return'].cumsum()
    
    total_ret = (np.exp(df['cum_strategy'].iloc[-1]) - 1) * 100
    market_ret = (np.exp(df['cum_market'].iloc[-1]) - 1) * 100
    
    cum_equity = np.exp(df['cum_strategy'])
    max_dd = ((cum_equity - cum_equity.cummax()) / cum_equity.cummax()).min() * 100
    
    print("\n" + "="*50)
    print("📊 LEGACY STRATEGY PERFORMANCE")
    print("="*50)
    print(f"Strategy Return:   {total_ret:8.2f}%")
    print(f"Market Return:     {market_ret:8.2f}%")
    print(f"Max Drawdown:      {max_dd:8.2f}%")
    print("="*50)
    
    return df

# ---------------------------------------------------------
# 7. ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    # Change this to your file path
    DATA_PATH = "../Data/ICICIBANK_Features2.csv"
    
    try:
        print("="*60)
        print("🚀 RUNNING ENHANCED STRATEGY WITH RISK MANAGEMENT")
        print("="*60)
        
        final_df, metrics = run_pipeline_enhanced(DATA_PATH)
        
        # Show sample of results
        print("\n📋 Sample Trade Data:")
        trade_rows = final_df[final_df['trade_pnl'] != 0][['close', 'regime', 'position', 'trade_pnl']].head(10)
        print(trade_rows)
        
    except Exception as e:
    
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()