from log.logger import log
from config import LESS_STRICT_SHOULD_LONG, FEE_RATE, MIN_EDGE_PCT

def should_long(df):
    row = df.iloc[-1]

    # Core conditions
    trend = row['ema50'] > row['ema200']
    rsi_ok = 30 < row['rsi'] < 70
    volume_ok = row['volume'] > row['vol_ma']

    # Debug metrics
    trend_progress = (row['ema50'] - row['ema200']) / row['ema200']
    volume_progress = row['volume'] / row['vol_ma']

    # === FIX #3: Minimum edge filter ===
    atr = row['atr']
    price = row['close']

    expected_move_pct = atr / price
    required_move_pct = (2 * FEE_RATE) + MIN_EDGE_PCT

    log(
        f"edge check -> expected_move={expected_move_pct:.4%}, "
        f"required_move={required_move_pct:.4%}"
    )
    

    # Decision logic
    if LESS_STRICT_SHOULD_LONG:    

        log("should long edge check skipped (LESS_STRICT_SHOULD_LONG)")

        decision = trend or rsi_ok or volume_ok
    else:
        decision = trend and rsi_ok and volume_ok 
        if (expected_move_pct < required_move_pct):
            log("should_long blocked: insufficient edge to cover fees")
            return False      

    log(f"should_long -> trend={trend} ({trend_progress:.2%})")
    log(f"should_long -> rsi_ok={rsi_ok} (RSI={row['rsi']:.2f})")
    log(f"should_long -> volume_ok={volume_ok} ({volume_progress:.2f}x)")
    log(f"should_long decision: {decision}")

    return decision