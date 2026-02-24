"""
DCA Branch — main.py
────────────────────
Strategy:
  - Track the 24h high for each symbol every loop.
  - Every time price drops another DCA_DROP_STEP_PCT% from the 24h high,
    buy $drop_pct worth (e.g. 3% drop → $3, 4% drop → $4).
  - Exit logic: trailing stop from exits.py (applied to avg entry price).
  - No leverage. Spot only. 3 symbols. $100 balance.

Bugs fixed vs previous version:
  1. After a SELL, entry check now skips via `continue` — no same-tick rebuy.
  2. dca_state is reset inside sell() already; main.py no longer double-updates it.
  3. dca_state["last_trigger_pct"] is updated inside buy() only — single source of truth.
"""

from dotenv import load_dotenv
import os, time
import pandas as pd
from binance.client import Client

load_dotenv()
API_KEY    = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

from config import *
from strategy.indicators import add_indicators
from strategy.logic import should_long_dca
from strategy.exits import should_exit, reset_symbol
from paper.portfolio import PaperPortfolio
from log.logger import log
from log.database import PortfolioDB
from app.dashboard import start_server_in_thread
from analysis.price_recorder import start_price_recorder

log("Starting DCA bot...")

binance     = Client(API_KEY, API_SECRET)
portfolioDB = PortfolioDB()
portfolio   = PaperPortfolio(starting_balance=START_BALANCE, db_obj=portfolioDB, leverage=LEVERAGE)

log(f"DCA Portfolio ready — balance={portfolio.balance:.2f}, symbols={list(portfolio.symbols.keys())}")

start_server_in_thread(portfolioDB)

banner = r"""
██████╗  ██████╗ █████╗     ██████╗  ██████╗ ████████╗
██╔══██╗██╔════╝██╔══██╗    ██╔══██╗██╔═══██╗╚══██╔══╝
██║  ██║██║     ███████║    ██████╔╝██║   ██║   ██║   
██║  ██║██║     ██╔══██║    ██╔══██╗██║   ██║   ██║   
██████╔╝╚██████╗██║  ██║    ██████╔╝╚██████╔╝   ██║   
╚═════╝  ╚═════╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   
"""
print(banner)

# Price recorder thread — records 1m candles for all symbols to a local SQLite DB for later analysis and dashboard display
log("Starting price recorder thread...")
start_price_recorder(binance, DCA_SYMBOLS)

if LESS_STRICT_SHOULD_LONG: #! FOR TESTING ONLY: skips all gates except, and ignores HTF bias even if required. Use to generate more trades and test exit logic.
    log("WARNING: LESS_STRICT_SHOULD_LONG is ENABLED — this is for testing only and will generate more trades by skipping all gates except DCA level, and ignoring HTF bias even if required.")
    print("WARNING: LESS_STRICT_SHOULD_LONG is ENABLED — this is for testing only and will generate more trades by skipping all gates except DCA level, and ignoring HTF bias even if required.")

# ─────────────────────────────────────────────────────────────────────── #
#  Main loop                                                               #
# ─────────────────────────────────────────────────────────────────────── #
while True:
    try:
        for symbol_name, symbol in portfolio.symbols.items():
            log(f"── Processing {symbol_name} ──")

            # ── 1. Fetch klines (5m, 300 candles = ~25h) ──────────────── #
            klines = binance.get_klines(
                symbol=symbol_name,
                interval=Client.KLINE_INTERVAL_5MINUTE,
                limit=300
            )
            df = pd.DataFrame(klines, columns=[
                "time","open","high","low","close","volume",
                "_","_","_","_","_","_"
            ]).astype({"open": float,"high": float,"low": float,"close": float,"volume": float})

            df = add_indicators(df)
            last = df.iloc[-1]

            # ── 2. 24h high from fetched data ──────────────────────────── #
            high_24h = df["high"].max()
            symbol._last_high = high_24h
            current_price = last.close

            log(f"{symbol_name} — price={current_price:.4f}, 24h_high={high_24h:.4f}, atr={last.atr:.6f}")

            # ── 3. Exit logic ──────────────────────────────────────────── #
            if symbol.in_position():
                if symbol.check_liquidation(current_price):
                    log(f"[LIQUIDATION] {symbol_name} @ {current_price:.4f}")
                    symbol.sell(current_price, FEE_RATE)
                    reset_symbol(symbol_name)
                    continue  # skip entry check this tick

                exit_reason = should_exit(
                    symbol.entry_price,
                    symbol,
                    current_price,
                    last.atr,
                    symbol_name
                )
                if exit_reason:
                    log(f"[EXIT {exit_reason.upper()}] {symbol_name} @ {current_price:.4f}")
                    symbol.sell(current_price, FEE_RATE)
                    reset_symbol(symbol_name)
                    print(f"[SELL {exit_reason.upper()}] {symbol_name} @ {current_price:.4f} | Balance: {portfolio.balance:.2f}")
                    continue

            # ── 4. DCA Entry logic ─────────────────────────────────────── #
            free_balance = portfolio.balance - portfolio.used_margin
            if free_balance < 0.5:
                log(f"{symbol_name} — no free balance ({free_balance:.2f}), skipping entry")
                continue

            # Cooldown after exit — don't rebuy immediately
            if time.time() < symbol.cooldown_until:
                remaining = symbol.cooldown_until - time.time()
                log(f"{symbol_name} — cooldown active ({remaining:.0f}s remaining), skipping entry")
                continue

            should_buy, spend_usd = should_long_dca(
                current_price=current_price,
                high_24h=high_24h,
                symbol_state=symbol.dca_state,
                df = df
            )

            if should_buy:
                ok = symbol.buy(current_price, spend_usd, high_24h, FEE_RATE)
                if ok:
                    print(
                        f"[DCA BUY #{symbol.dca_levels}] {symbol_name} @ {current_price:.4f} | "
                        f"Spent ${spend_usd:.2f} | Avg entry={symbol.average_entry_price:.4f} | "
                        f"Total pos={symbol.position:.6f} | Balance: {portfolio.balance:.2f}"
                    )

        log(f"── Sleeping {SLEEP_INTERVAL}s ──")
        time.sleep(SLEEP_INTERVAL)

    except Exception as e:
        log(f"Error in main loop: {e}")
        import traceback
        log(traceback.format_exc())
        print(f"Error: {e}")
        time.sleep(5)
