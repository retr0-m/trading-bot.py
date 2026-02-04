from log.logger import log

def should_long(df):
    row = df.iloc[-1]

    # Example conditions (adapt to your actual logic)
    trend = row['ema50'] > row['ema200']
    rsi_ok = 30 < row['rsi'] < 70
    volume_ok = row['volume'] > row['vol_ma']

    # Debug with progress
    trend_progress = (row['ema50'] - row['ema200']) / row['ema200'] * 100  # % difference
    volume_progress = row['volume'] / row['vol_ma'] * 100                  # % of required volume

    print(f"should_long -> trend={trend} (EMA50-EMA200={trend_progress:.2f}%)")
    print(f"should_long -> rsi_ok={rsi_ok} (RSI={row['rsi']:.2f})")
    print(f"should_long -> volume_ok={volume_ok} (Vol progress={volume_progress:.2f}%)")

    decision = trend and rsi_ok and volume_ok
    print(f"should_long decision: {decision}")

    return decision