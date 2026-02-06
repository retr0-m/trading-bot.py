from log.logger import log
from config import TAKE_PROFIT_MULTIPLIER, STOP_LOSS_MULTIPLIER

def should_exit(entry_price, position, current_price, atr):
    stop_loss = position.entry_price - (STOP_LOSS_MULTIPLIER * atr)
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

    log("should_exit decision: None")
    return None