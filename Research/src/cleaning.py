import pandas as pd


MARKET_OPEN = "09:30"
MARKET_CLOSE = "15:30"


def load_raw_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return df


def standardize_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.set_index("timestamp")
    elif "Datetime" in df.columns:
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
        df = df.set_index("Datetime")
    else:
        raise ValueError("No timestamp column found")

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
    df[ohlc] = df[ohlc].bfill()

    return df



def clean_equity_data(csv_path: str) -> pd.DataFrame:
    df = load_raw_data(csv_path)
    df = standardize_timestamp(df)
    df = drop_invalid_rows(df)
    df = enforce_continuity(df)
    return df
