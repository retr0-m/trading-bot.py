# main.py

# .env support
from dotenv import load_dotenv
import os

from log.database import PortfolioDB

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

import time
import pandas as pd
from binance.client import Client

from config import *
from strategy.indicators import add_indicators
from strategy.logic import should_long
from strategy.exits import should_exit
from risk.position import position_size
from paper.portfolio import PaperPortfolio
from log.logger import log
from app.dashboard import start_server_in_thread
log("Starting bot...")

# Paper trading does not require API keys, but can be set up if needed
binance = Client(API_KEY, API_SECRET)

# inizialize database
portfolioDB= PortfolioDB()
log("Initialized DB")


# Initialize paper portfolio
portfolio = PaperPortfolio(START_BALANCE, portfolioDB)
log(f"Initialized PaperPortfolio with starting balance: {portfolio.balance:.2f}")
log("Entering main loop")

# starting dashboard
start_server_in_thread(portfolioDB)


# banner
banner = r"""
███╗   ███╗ █████╗ ██╗  ██╗██╗███╗   ██╗ ██████╗ ██████╗  █████╗ ██████╗ ███████╗██████╗ 
████╗ ████║██╔══██╗██║ ██╔╝██║████╗  ██║██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
██╔████╔██║███████║█████╔╝ ██║██╔██╗ ██║██║  ███╗██████╔╝███████║██████╔╝█████╗  ██████╔╝
██║╚██╔╝██║██╔══██║██╔═██╗ ██║██║╚██╗██║██║   ██║██╔═══╝ ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║██║  ██║██║  ██╗██║██║ ╚████║╚██████╔╝██║     ██║  ██║██║     ███████╗██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
"""
print(banner)


# Main loop
while True:
    try:
        log("Fetching klines")
        klines = binance.get_klines(
            symbol=SYMBOL,
            interval=Client.KLINE_INTERVAL_1MINUTE,
            limit=300
        )
        log(f"Fetched {len(klines)} klines")
        # Construct DataFrame
        df = pd.DataFrame(klines, columns=[
            "time","open","high","low","close","volume",
            "_","_","_","_","_","_"
        ])
        df = df.astype({
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float
        })
        log("Constructed DataFrame and applied dtypes")

        # Add indicators
        df = add_indicators(df)
        log("Indicators added to DataFrame")
        last = df.iloc[-1]
        log(f"Last row - close: {last.close:.2f}, atr: {last.atr:.6f}")

        # EXIT LOGIC
        log("Checking exit logic")
        if portfolio.in_position():
            exit_reason = should_exit(portfolio, last.close, last.atr)
            if exit_reason:
                log(f"Exit triggered: {exit_reason}")
                portfolio.sell(last.close, fee_rate = FEE_RATE)
                log(f"[PAPER SELL] {exit_reason.upper()} @ {last.close:.2f}")
                log(f"Balance after sell: {portfolio.balance:.2f} USDT")
                print(f"[PAPER SELL] {exit_reason.upper()} @ {last.close:.2f}")
                print(f"Balance: {portfolio.balance:.2f} USDT")

        # ENTRY LOGIC
        log("Checking entry logic")
        if not portfolio.in_position() and should_long(df):
            stop = last.close - last.atr
            log(f"Calculated stop: {stop:.2f}")
            qty = position_size(
                portfolio.balance,
                last.close,
                stop,
                RISK_PER_TRADE
            )
            log(f"Raw position size (units): {qty:.6f}")

            # Cap max position
            qty = min(qty * last.close, MAX_POSITION_USDT) / last.close
            log(f"Adjusted qty after max position cap: {qty:.6f}")

            if portfolio.buy(last.close, qty, FEE_RATE):
                log(f"[PAPER BUY] {qty:.6f} BTC @ {last.close:.2f}")
                log(f"Balance after buy: {portfolio.balance:.2f} USDT")
                print(f"[PAPER BUY] {qty:.6f} BTC @ {last.close:.2f}")
                print(f"Balance: {portfolio.balance:.2f} USDT")

        log(f"Sleeping for {SLEEP_INTERVAL} seconds")
        time.sleep(SLEEP_INTERVAL)

    except Exception as e:
        log(f"Error in main loop: {e}")
        print(f"Error: {e}")
        time.sleep(5)