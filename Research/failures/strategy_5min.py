import numpy as np
import pandas as pd


def backtest_mean_reversion_5min(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # -------------------------------
    # Parameters
    # -------------------------------
    TREND_THRESHOLD = 0.03
    LARGE_BAR_MULT = 2.5
    ROLL_STD_WIN = 12
    MAX_HOLD = 12

    Z_LONG_ENTRY = -1.5
    Z_LONG_MAX = -2.5
    Z_SHORT_ENTRY = 1.5
    Z_SHORT_MAX = 2.5
    Z_EXIT = 0.3

    COST = 0.0005

    # -------------------------------
    # Filters
    # -------------------------------
    low_vol = df["vol_20"] < df["vol_60"]
    trend_strength = (df["sma_20"] - df["sma_60"]).abs() / df["close"]
    low_trend = trend_strength < TREND_THRESHOLD
    rolling_std = df["log_return"].rolling(ROLL_STD_WIN).std()
    no_large_bar = df["log_return"].abs() < LARGE_BAR_MULT * rolling_std

    trade_filter = low_vol & low_trend & no_large_bar

    # -------------------------------
    # Entry Signals (t-1 execution)
    # -------------------------------
    signal = np.zeros(len(df))

    signal[
        (df["zscore_20"] <= Z_LONG_ENTRY) &
        (df["zscore_20"] > Z_LONG_MAX) &
        trade_filter
    ] = 1

    signal[
        (df["zscore_20"] >= Z_SHORT_ENTRY) &
        (df["zscore_20"] < Z_SHORT_MAX) &
        trade_filter
    ] = -1

    df["signal"] = pd.Series(signal, index=df.index).shift(1).fillna(0)

    # -------------------------------
    # Position Construction (FAST)
    # -------------------------------
    df["position"] = df["signal"].replace(0, np.nan)
    df["position"] = df["position"].ffill().fillna(0)

    # -------------------------------
    # Exit Logic
    # -------------------------------
    exit_signal = df["zscore_20"].abs() < Z_EXIT
    df.loc[exit_signal.shift(1, fill_value=False), "position"] = 0

    # Enforce max holding time
    trade_id = (df["position"].diff() != 0).cumsum()
    holding_time = df.groupby(trade_id).cumcount()

    df.loc[holding_time > MAX_HOLD, "position"] = 0
    df["position"] = df["position"].ffill().fillna(0)

    # -------------------------------
    # Returns & Costs
    # -------------------------------
    df["strategy_return"] = df["position"] * df["log_return"]
    df["position_change"] = df["position"].diff().abs().fillna(0)
    df["transaction_cost"] = COST * df["position_change"]
    df["strategy_return_net"] = df["strategy_return"] - df["transaction_cost"]

    # -------------------------------
    # Equity Curves
    # -------------------------------
    df["cum_strategy"] = df["strategy_return"].cumsum()
    df["cum_strategy_net"] = df["strategy_return_net"].cumsum()
    df["cum_market"] = df["log_return"].cumsum()

    # -------------------------------
    # Trade Count (correct)
    # -------------------------------
    trades = (df["position_change"] > 0).sum() // 2

    print("\n========== STRATEGY SUMMARY ==========")
    print(f"Trades: {trades}")
    print(f"Filter pass rate: {trade_filter.mean():.2%}")
    print(f"Gross return: {df['cum_strategy'].iloc[-1]:.4f}")
    print(f"Net return:   {df['cum_strategy_net'].iloc[-1]:.4f}")
    print("====================================\n")

    return df
