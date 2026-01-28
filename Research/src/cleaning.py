import pandas as pd


MARKET_OPEN = "09:30"
MARKET_CLOSE = "15:30"


def load_raw_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return df


def standardize_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize the timestamp/index of the DataFrame.
    Handles 3 cases:
    1. Data already has DatetimeIndex (from loading with index_col=0)
    2. Data has 'timestamp' column
    3. Data has 'Datetime' column
    """
    # Case 1: Already has a DatetimeIndex (e.g., loaded with parse_dates=True, index_col=0)
    if isinstance(df.index, pd.DatetimeIndex):
        # Already good, just clean up
        pass
    # Case 2: Has 'timestamp' column
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.set_index("timestamp")
    # Case 3: Has 'Datetime' column  
    elif "Datetime" in df.columns:
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
        df = df.set_index("Datetime")
    else:
        # Try to convert existing index to datetime
        try:
            df.index = pd.to_datetime(df.index, errors="coerce")
        except Exception:
            raise ValueError("No timestamp column found and could not parse index as datetime")

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def drop_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["open", "high", "low", "close", "volume"]
    return df.dropna(subset=required_cols)


def build_continuous_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    trading_days = df.index.normalize().unique()

    all_minutes = []
    for day in trading_days:
        day_range = pd.date_range(
            start=f"{day.date()} {MARKET_OPEN}",
            end=f"{day.date()} {MARKET_CLOSE}",
            freq="1min",
        )
        all_minutes.extend(day_range)

    return pd.DatetimeIndex(all_minutes)


def enforce_continuity(df: pd.DataFrame) -> pd.DataFrame:
    continuous_index = build_continuous_index(df)
    df = df.reindex(continuous_index)

    ohlc = ["open", "high", "low", "close"]
    df[ohlc] = df[ohlc].apply(pd.to_numeric, errors='coerce')
    df[ohlc] = df[ohlc].replace(0, pd.NA)
    df[ohlc] = df[ohlc].ffill()
    df["volume"] = df["volume"].fillna(0)
    # df[ohlc] = df[ohlc].bfill() # REMOVED: Future bias
    df = df.dropna(subset=ohlc) # Remove initial rows that couldn't be ffilled

    return df



def clean_equity_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize equity data.
    Accepts a DataFrame (already loaded) instead of a path.
    """
    df = standardize_timestamp(df)
    df = drop_invalid_rows(df)
    df = enforce_continuity(df)
    return df
