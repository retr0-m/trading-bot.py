# ! DEPRECATED

from log.logger import log

def position_size(
    balance: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float,
):
    """
    Futures-safe position sizing.
    Returns asset quantity (qty), NOT notional.
    Risk is controlled by stop-loss distance, independent of leverage.
    """

    log(
        f"position_size inputs -> "
        f"balance={balance:.2f}, "
        f"entry_price={entry_price:.2f}, "
        f"stop_price={stop_price:.2f}, "
        f"risk_pct={risk_pct}"
    )

    # Validation
    stop_distance = entry_price - stop_price
    if stop_distance <= 0:
        log("position_size -> invalid stop (stop >= entry), returning 0")
        return 0.0

    risk_amount = balance * risk_pct
    qty = risk_amount / stop_distance

    log(
        f"position_size result -> "
        f"qty={qty:.6f}, "
        f"risk_amount={risk_amount:.2f}, "
        f"stop_distance={stop_distance:.6f}"
    )

    return qty




