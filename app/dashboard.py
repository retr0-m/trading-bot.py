import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from log.database import PortfolioDB
from datetime import datetime
import uvicorn
from log.logger import log_uvicorn as log
from config import SYMBOLS

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

db : PortfolioDB  # global variable to hold the database connection


def build_portfolio_from_trades(trades):
    balance = 0.0
    equity = 0.0
    trade_history = []

    # Track net position per symbol
    position_count = {sym: 0 for sym in SYMBOLS}

    for t in trades:
        trade_id, symbol, side, price, amount, fee, balance_after, timestamp = t

        balance = balance_after
        equity = balance  # unrealized PnL later

        if side == "BUY":
            position_count[symbol] += 1
        elif side == "SELL":
            position_count[symbol] -= 1

        trade_history.append({
            "id": trade_id,
            "time": timestamp,
            "type": side,
            "symbol": symbol,
            "qty": amount,
            "price": price,
            "expense": (price * amount) / 5, # approximate, since we don't track leverage here
            "fee": fee,
            "balance_after": balance_after
        })

    # Open positions = symbols with net BUYs
    positions = [
        f"{sym}: OPEN"
        for sym, count in position_count.items()
        if count > 0
    ]

    return {
        "balance": balance,
        "equity": equity,
        "positions": positions,
        "trade_history": trade_history[::-1]
    }
    
    
    
from collections import Counter

def build_charts(trade_history):
    """
    Build chart data arrays from trade_history.
    Charts are chronological: oldest trades first.
    """
    labels = []
    equity_curve = []
    drawdown_curve = []
    pnl_per_trade = []
    
    peak = 0.0

    for trade in reversed(trade_history):  # oldest first
        labels.append(trade["time"])
        equity_curve.append(trade["balance_after"])

        # Drawdown % relative to peak
        peak = max(peak, trade["balance_after"])
        drawdown_curve.append((trade["balance_after"] - peak) / peak * 100)

        # PnL per trade: approximate using SELL trades
        if trade["type"] == "SELL":
            pnl_per_trade.append(trade["balance_after"] - trade["expense"] - trade["fee"])

    # Trade frequency per minute
    minutes = [t["time"][:16] for t in reversed(trade_history)]  # oldest first
    counter = Counter(minutes)
    freq_labels = sorted(counter.keys())
    freq_data = [counter[m] for m in freq_labels]

    return {
        "chart_labels": labels,
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "pnl_per_trade": pnl_per_trade,
        "trade_freq_labels": freq_labels,
        "trade_freq": freq_data,
    }



@app.get("/")
def read_dashboard(request: Request):
    log("\t[GET] dashboard")
    trades = db.temp_connection.get_all_trades()
    portfolio = build_portfolio_from_trades(trades)
    chart_data = build_charts(portfolio["trade_history"])  # <-- new

    log("\t[GET] -> rendering template with portfolio data + chart data")
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "portfolio": portfolio,
            **chart_data  # unpack chart arrays for Jinja
        }
    )
    
def start_server(db_obj: PortfolioDB):
    global db
    db = db_obj
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
def start_server_in_thread(db_obj: PortfolioDB):
    server_thread = threading.Thread(target=start_server, args=(db_obj,), daemon=True)
    server_thread.start()


if __name__ == "__main__":
    
    db = PortfolioDB()
    start_server_in_thread(db)