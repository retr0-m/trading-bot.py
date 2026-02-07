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
    positions = []
    trade_history = []

    for t in trades:
        trade_id, symbol, side, price, amount, fee, balance_after, timestamp = t

        balance = balance_after
        equity = balance_after  # for now: no unrealized PnL

        trade_history.append({
            "id":trade_id,
            "time": timestamp,
            "type": side,
            "symbol": symbol,
            "qty": amount,
            "price": price,
            "expense": price*amount if side == "BUY" else -price*amount,
            "balance after": balance_after
        })

    # If last trade is BUY for each symbol → open position
    trades_by_symbol = {sym: [] for sym in SYMBOLS}
    for t in trades:
        trade_id, symbol, side, price, amount, fee, balance_after, timestamp = t
        for sym in SYMBOLS:
            if symbol == sym:
                trades_by_symbol[sym].append(t)
    open_positions = []
    for sym, last_trades in trades_by_symbol.items():
        buy_number = 0
        sell_number = 0
        for trade in last_trades:
            if trade[2] == "BUY":  # side == "BUY"
                buy_number += 1
            elif trade[2] == "SELL":  # side == "SELL"
                sell_number += 1
        if buy_number > sell_number:  # odd number of BUYs → open position
            open_positions.append(sym)
            
    
    for symbol in open_positions:
        positions.append(
            f"{symbol}: OPEN"
        )

    return {
        "balance": balance,
        "equity": equity,
        "positions": positions,
        "trade_history": trade_history[::-1]  # newest first
    }
    
    
@app.get("/")
def read_dashboard(request: Request):
    log("\t[GET] dashboard")
    trades = db.temp_connection.get_all_trades()
    portfolio = build_portfolio_from_trades(trades)

    log("\t[GET] -> rendering template with portfolio data")
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "portfolio": portfolio,
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