import pandas as pd

def cash_signal(df: pd.DataFrame) -> pd.Series:
    return pd.Series(0, index=df.index)
