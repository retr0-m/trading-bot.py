# portfolio_db.py
import sqlite3
from pathlib import Path
from log.logger import log

DB_PATH = Path("log/db/portfolio.db")

class TempConnection:
    """Each method opens a new connection and closes it after execution to be thread-safe."""

    @staticmethod
    def get_all_trades():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, symbol, side, price, amount, fee, balance_after, sl, tp, timestamp
                FROM trades
                ORDER BY id ASC
            """)
            return cursor.fetchall()

    @staticmethod
    def get_last_trade(symbol: str):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT side, price, amount, balance_after, timestamp, sl, tp
                FROM trades
                WHERE symbol = ?
                ORDER BY id DESC
                LIMIT 1
            """, (symbol,))
            return cursor.fetchone()

    @staticmethod   #! not used currently, DEPRECATED
    def get_equity_curve():
        with sqlite3.connect(DB_PATH) as conn:
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, balance_after
                FROM trades
                ORDER BY id ASC
            """)
            return cursor.fetchall()


class PortfolioDB:
    """Main database class with persistent connection for writes."""
    
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)  # persistent connection for writes
        self._create_tables()
        self.temp_connection = TempConnection()  # attach temp connection
        log(f"Database initialized at {DB_PATH}")

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                balance_after REAL NOT NULL,
                sl REAL NOT NULL,
                tp REAL NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def log_trade(
        self,
        symbol: str,
        side: str,
        price: float,
        amount: float,
        fee: float,
        balance_after: float,
        sl: float = 0.0,
        tp: float = 0.0
    ):
        log(f"inserting query in db with following data: side={side}, price={price}, amount={amount}, fee={fee}, balance_after={balance_after} sl={sl} tp={tp}")
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trades (symbol, side, price, amount, fee, balance_after, sl, tp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, side, price, amount, fee, balance_after, sl, tp)) 
        self.conn.commit()
        log(
            f"DB | {side} | price={price:.2f} "
            f"amount={amount:.6f} fee={fee:.4f} "
            f"balance={balance_after:.2f}"
        )
        

    def close(self):
        self.conn.close()
        
