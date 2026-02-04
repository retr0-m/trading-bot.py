from log.logger import log

def position_size(balance, entry_price, stop_price, risk_pct):
    log(f"position_size inputs -> balance={balance:.2f}, entry_price={entry_price:.2f}, stop_price={stop_price:.2f}, risk_pct={risk_pct}")
    risk_amount = balance * risk_pct
    stop_distance = abs(entry_price - stop_price)
    size = risk_amount / stop_distance
    log(f"position_size result -> size={size:.6f} (risk_amount={risk_amount:.2f}, stop_distance={stop_distance:.6f})")
    return size