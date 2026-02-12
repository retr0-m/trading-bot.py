from numpy import take
from log.logger import log
from config import *

last_highest_price = 0.0

def should_exit(entry_price, position, current_price, atr):
    global last_highest_price
    if current_price > last_highest_price:
        last_highest_price = current_price
    stop_loss = position.entry_price - (STOP_LOSS_MULTIPLIER * atr) + (FEE_RATE * current_price) * 2
    take_profit = position.entry_price + (TAKE_PROFIT_MULTIPLIER * atr)
    log(f"should_exit -> stop_loss={stop_loss:.2f}, take_profit={take_profit:.2f}, current_price={current_price:.2f}")
    if current_price > entry_price + atr:
        stop_loss = entry_price
        
    if current_price <= stop_loss:
        log("should_exit decision: stop")
        return "stop"
    if current_price >= take_profit:
        log("should_exit decision: take_profit")
        return "take_profit"

    profit_pct = (last_highest_price - entry_price) / entry_price

    if profit_pct >= TRAIL_START_PCT:
        stop_loss = max(
            stop_loss,
            last_highest_price * (1 - TRAIL_DISTANCE_PCT)
        )

    log("should_exit decision: None")
    return None

def get_tp_sl(entry_price, atr):
    stop_loss = entry_price - (STOP_LOSS_MULTIPLIER * atr) + (FEE_RATE * entry_price) * 2
    take_profit = entry_price + (TAKE_PROFIT_MULTIPLIER * atr)
    return stop_loss, take_profit