from log.logger import log

def should_exit(position, current_price, atr):
    stop_loss = position.entry_price - atr
    take_profit = position.entry_price + (1.5 * atr)
    log(f"should_exit -> stop_loss={stop_loss:.2f}, take_profit={take_profit:.2f}, current_price={current_price:.2f}")

    if current_price <= stop_loss:
        log("should_exit decision: stop")
        return "stop"
    if current_price >= take_profit:
        log("should_exit decision: take_profit")
        return "take_profit"

    log("should_exit decision: None")
    return None