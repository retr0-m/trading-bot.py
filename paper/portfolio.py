from log.logger import log
from log.database import PortfolioDB


class PaperPortfolio:
    def __init__(self, symbol: str, starting_balance=50.0, db_obj: PortfolioDB | None = None, leverage: float = 1.0):
        self.symbol = symbol
        self.balance = starting_balance        # your margin / free balance
        self.position: float = 0                      # amount of asset held
        self.entry_price = 0.0
        self.db = db_obj
        self.leverage = leverage
        log(f"Created PaperPortfolio with starting balance: {self.balance:.2f}, leverage: {self.leverage}x")
        self.load_from_db()

    def in_position(self):
        return self.position > 0

    def load_from_db(self):
        """Recover last trade from DB to restore portfolio state"""
        if self.db is None:
            log("No database connection available, starting fresh")
            return
            
        last_trade = self.db.temp_connection.get_last_trade(self.symbol)
        if last_trade:
            side, price, amount, balance_after, timestamp = last_trade
            self.balance = balance_after
            if side == "BUY":
                self.position = amount
                self.entry_price = price
                log(f"Recovered open position from last BUY: amount={amount:.6f} at price={price:.2f}")
            else:
                self.position = 0
                self.entry_price = 0
                log("Recovered portfolio: no open position")
        else:
            log("No trades in DB, starting fresh")

    def buy(self, price: float, amount: float = 0, fee_rate: float = 0.01):
        if self.in_position():
            log("Already in position, cannot buy")
            return

        # If amount == 0, buy with 1/10 of margin
        if amount == 0:
            amount = ((self.balance * self.leverage) / 10) / price  # full leveraged amount

        # Position is leveraged
        position_value = amount * price
        fee = position_value * fee_rate

        # Deduct margin portion from balance
        margin_required = position_value / self.leverage
        if margin_required + fee > self.balance:
            log("Not enough balance to open leveraged position!")
            return

        self.balance -= margin_required + fee
        self.position = amount
        self.entry_price: float = price

        log(f"BUY executed at {price:.2f}, amount: {amount:.6f}, leveraged position: {position_value:.2f}, remaining balance: {self.balance:.2f}, fee: {fee:.4f}")
        if self.db:
            self.db.log_trade(
                symbol=self.symbol,
                side="BUY",
                price=price,
                amount=amount,
                fee=fee,
                balance_after=self.balance,
            )
        else:
            log("No database connection, trade not logged")

    def sell(self, price: float, fee_rate: float = 0.01):
        if not self.in_position():
            log("No position to sell")
            return

        # Leveraged position value
        position_value = self.position * price
        fee = position_value * fee_rate

        # Realized PnL
        profit = (price - self.entry_price) * self.position * self.leverage

        # Release margin + profit, minus fees
        self.balance += (self.position * price * self.leverage) / self.leverage + profit - fee

        log(
            f"SELL executed at {price:.2f}, amount: {self.position:.6f}, "
            f"leverage: {self.leverage}x, profit: {profit:.2f}, fee: {fee:.4f}, new balance: {self.balance:.2f}"
        )
        if self.db:
            self.db.log_trade(
                symbol=self.symbol,
                side="SELL",
                price=price,
                amount=self.position,
                fee=fee,
                balance_after=self.balance,
            )
        else:
            log("No database connection, trade not logged")

        # Reset position
        self.position = 0
        self.entry_price = 0

    def check_liquidation(self, price: float, liquidation_threshold: float = 0.8):
        """
        Check if position is close to liquidation.
        liquidation_threshold = % of margin loss before liquidation
        """
        if not self.in_position():
            return False
        # Loss on position relative to margin
        position_value = self.position * price
        margin = position_value / self.leverage
        loss = max(0, (self.entry_price - price) * self.position * self.leverage)  # only if price drops
        if loss >= margin * liquidation_threshold:
            log(f"WARNING: Position close to liquidation! unrealized loss: {loss:.2f}, margin: {margin:.2f}")
            return True
        return False