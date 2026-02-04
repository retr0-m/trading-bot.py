from log.logger import log



class PaperPortfolio:
    def __init__(self, starting_balance=50.0):
        self.balance = starting_balance
        self.position = 0  # amount of asset
        self.entry_price = None
        log(f"Created PaperPortfolio with starting balance: {self.balance:.2f}")

    def in_position(self):
        return self.position > 0

    def buy(self, price, amount=None):
        if self.in_position():
            log("Already in position, cannot buy")
            return

        # If amount not specified, buy with full balance
        if amount is None:
            amount = self.balance / price

        self.position = amount
        self.entry_price = price
        self.balance -= amount * price
        log(f"BUY executed at {price:.2f}, amount: {amount:.6f}, remaining balance: {self.balance:.2f}")

    def sell(self, price):
        if not self.in_position():
            log("No position to sell")
            return

        self.balance += self.position * price
        profit = (price - self.entry_price) * self.position
        log(f"SELL executed at {price:.2f}, amount: {self.position:.6f}, profit: {profit:.2f}, new balance: {self.balance:.2f}")
        self.position = 0
        self.entry_price = None