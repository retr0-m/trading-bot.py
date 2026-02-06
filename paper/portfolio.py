from log.logger import log
from log.database import PortfolioDB





class PaperPortfolio:
    def __init__(self, starting_balance=50.0, db_obj: PortfolioDB = PortfolioDB()):
        self.balance = starting_balance
        self.position = 0  # amount of asset
        self.entry_price = None
        self.db = db_obj
        log(f"Created PaperPortfolio with starting balance: {self.balance:.2f}")

    def in_position(self):
        return self.position > 0

    def buy(self, price: float, amount: float | None = None, fee_rate: float = 0.01):
        if self.in_position():
            log("Already in position, cannot buy")
            return

        # If amount not specified, buy with full balance
        if amount is None:
            amount = self.balance / price

        self.position = amount
        self.entry_price = price
        self.balance -= amount * price
        self.balance -= (amount * price) * fee_rate  # Deduct fees
        log(f"BUY executed at {price:.2f}, amount: {amount:.6f}, remaining balance: {self.balance:.2f}")
        
        fee = (amount * price) * fee_rate
        self.db.log_trade(
            side="BUY",
            price=price,
            amount=amount,
            fee=fee,
            balance_after=self.balance,
        )

    def sell(self, price, fee_rate: float = 0.01):
        if not self.in_position():
            log("No position to sell")
            return

        self.balance += self.position * price
        self.balance -= (self.position * price) * fee_rate  # Deduct fees
        profit = (price - self.entry_price) * self.position
        log(f"SELL executed at {price:.2f}, amount: {self.position:.6f}, profit: {profit:.2f}, new balance: {self.balance:.2f}")

        
        fee = (self.position * price) * fee_rate
        self.db.log_trade(
            side="SELL",
            price=price,
            amount=self.position,
            fee=fee,
            balance_after=self.balance,
        )
        
        self.position = 0
        self.entry_price = None
        