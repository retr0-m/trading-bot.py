import pandas as pd
import pandas_ta as ta
from log.logger import log

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["ema50"] = ta.ema(df["close"], length=50)
    df["ema200"] = ta.ema(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["vol_ma"] = df["volume"].rolling(20).mean()
    log("Added indicators: ema50, ema200, rsi, atr, vol_ma")
    return df