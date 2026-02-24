from config import DCA_SYMBOLS, DCA_COOLDOWN_SECONDS
from log.logger import log, log_position
from log.database import PortfolioDB
from time import time

class PaperPortfolio:
    def __init__(self, starting_balance: float = 100.0, db_obj: PortfolioDB | None = None, leverage: float = 1.0):
        self.balance     = starting_balance
        self.used_margin = 0.0
        self.db          = db_obj
        self.leverage    = leverage

        self.symbols = {
            symbol: DCASymbol(symbol, self, leverage, db_obj)
            for symbol in DCA_SYMBOLS
        }
        log(f"[DCA] PaperPortfolio created — balance={self.balance:.2f}, symbols={list(self.symbols.keys())}")


class DCASymbol:
    """
    Tracks a DCA position for a single symbol.
    Supports multiple buy entries and computes a true weighted average entry price.

    Bugs fixed:
      - buy() is now the single place that updates dca_state["last_trigger_pct"]
      - sell() resets all state correctly (was already correct, confirmed)
      - log_position.buy/sell now log avg_entry which is always the weighted average
    """

    def __init__(self, symbol: str, portfolio: PaperPortfolio, leverage: float, db_obj: PortfolioDB | None = None):
        self.name      = symbol
        self.symbol    = symbol
        self.portfolio = portfolio
        self.leverage  = leverage
        self.db        = db_obj

        self._last_high: float = 0.0  # set by main loop each tick

        self._reset_position()

    def _reset_position(self):
        """Reset all position state. Called on init and after full sell."""
        self.position: float            = 0.0
        self.total_cost: float          = 0.0   # cumulative net USDT spent (excl. fee)
        self.average_entry_price: float = 0.0
        self.entry_price: float         = 0.0   # first entry price (for exits.py compat)
        self.dca_levels: int            = 0
        self.dca_state: dict            = {"last_trigger_pct": 0.0}
        self.cooldown_until: float      = 0.0   # timestamp until which new entries are blocked after a sell

    # ------------------------------------------------------------------ #
    #  Queries                                                             #
    # ------------------------------------------------------------------ #

    def in_position(self) -> bool:
        return self.position > 0

    def unrealized_pnl(self, current_price: float) -> float:
        if not self.in_position():
            return 0.0
        return (current_price - self.average_entry_price) * self.position

    # ------------------------------------------------------------------ #
    #  DCA Buy                                                             #
    # ------------------------------------------------------------------ #

    def buy(self, price: float, spend_usd: float, high_24h: float, fee_rate: float = 0.001) -> bool:
        """
        Buy `spend_usd` worth of the asset at `price`.
        Updates the weighted average entry price across all DCA levels.
        Updates dca_state so the next level is tracked correctly.
        """
        free_balance = self.portfolio.balance - self.portfolio.used_margin

        if spend_usd > free_balance:
            spend_usd = free_balance
            if spend_usd < 0.5:
                log(f"[DCA] {self.symbol} — not enough free balance ({free_balance:.2f}), skipping")
                return False

        fee = spend_usd * fee_rate
        qty = (spend_usd - fee) / price  # units received after fee

        # Deduct from portfolio
        self.portfolio.balance -= spend_usd

        # ✅ Accumulate cost and units for correct weighted average
        self.total_cost          += spend_usd - fee   # net cost (what we'd recover at avg_entry)
        self.position            += qty
        self.average_entry_price  = self.total_cost / self.position
        self.dca_levels          += 1

        if self.dca_levels == 1:
            self.entry_price = price  # first entry — used by exits.py

        # ✅ FIX 2: update dca_state here only (main.py no longer touches it)
        if high_24h > 0:
            drop_pct = (high_24h - price) / high_24h * 100
            self.dca_state["last_trigger_pct"] = drop_pct
            self._last_high = high_24h

        log(
            f"[DCA BUY #{self.dca_levels}] {self.symbol} | "
            f"price={price:.4f} spend=${spend_usd:.2f} qty={qty:.6f} fee={fee:.4f} | "
            f"avg_entry={self.average_entry_price:.4f} total_pos={self.position:.6f} | "
            f"balance={self.portfolio.balance:.2f}"
        )
        log_position.buy(self.symbol, price, qty, self.average_entry_price, self.portfolio.balance)

        if self.db:
            self.db.log_trade(
                symbol=self.symbol,
                side="BUY",
                price=price,
                amount=qty,
                fee=fee,
                balance_after=self.portfolio.balance,
                sl=0.0,
                tp=0.0,
            )
        return True

    # ------------------------------------------------------------------ #
    #  Sell (full position)                                                #
    # ------------------------------------------------------------------ #

    def sell(self, price: float, fee_rate: float = 0.001):
        if not self.in_position():
            log(f"[DCA] {self.symbol} — no position to sell")
            return

        qty_sold       = self.position
        avg_entry_sold = self.average_entry_price
        position_value = qty_sold * price
        fee            = position_value * fee_rate
        profit         = (price - avg_entry_sold) * qty_sold

        self.portfolio.balance += position_value - fee

        log(
            f"[DCA SELL] {self.symbol} | "
            f"price={price:.4f} qty={qty_sold:.6f} avg_entry={avg_entry_sold:.4f} | "
            f"profit={profit:.2f} fee={fee:.4f} dca_levels={self.dca_levels} | "
            f"balance={self.portfolio.balance:.2f}"
        )
        # ✅ Log before reset so values are correct
        log_position.sell(self.symbol, price, qty_sold, avg_entry_sold, self.portfolio.balance)

        if self.db:
            self.db.log_trade(
                symbol=self.symbol,
                side="SELL",
                price=price,
                amount=qty_sold,
                fee=fee,
                balance_after=self.portfolio.balance,
                sl=0.0,
                tp=0.0,
            )
        cooldown_seconds = DCA_COOLDOWN_SECONDS   # sit out 5 minutes after any exit
        cooldown_ts = time() + cooldown_seconds
        # Reset everything
        self._reset_position()
        self.cooldown_until = cooldown_ts
        log(f"[DCA] {self.symbol} — entered cooldown until {cooldown_ts:.0f}")

    # ------------------------------------------------------------------ #
    #  Liquidation check                                                   #
    # ------------------------------------------------------------------ #

    def check_liquidation(self, price: float, liquidation_threshold: float = 0.8) -> bool:
        if not self.in_position():
            return False
        loss   = max(0.0, (self.average_entry_price - price) * self.position)
        margin = self.total_cost / self.leverage
        if loss >= margin * liquidation_threshold:
            log(f"[DCA] {self.symbol} — WARNING: near liquidation! loss={loss:.2f}, margin={margin:.2f}")
            return True
        return False
