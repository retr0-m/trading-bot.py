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
                SELECT id, side, price, amount, fee, balance_after, timestamp
                FROM trades
                ORDER BY id ASC
            """)
            return cursor.fetchall()

    @staticmethod
    def get_last_trade():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT side, price, amount, balance_after, timestamp
                FROM trades
                ORDER BY id DESC
                LIMIT 1
            """)
            return cursor.fetchone()

    @staticmethod
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
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                balance_after REAL NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def log_trade(
        self,
        side: str,
        price: float,
        amount: float,
        fee: float,
        balance_after: float,
    ):
        log(f"inserting query in db with following data: side={side}, price={price}, amount={amount}, fee={fee}, balance_after={balance_after}")
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trades (side, price, amount, fee, balance_after)
            VALUES (?, ?, ?, ?, ?)
        """, (side, price, amount, fee, balance_after))
        self.conn.commit()
        log(
            f"DB | {side} | price={price:.2f} "
            f"amount={amount:.6f} fee={fee:.4f} "
            f"balance={balance_after:.2f}"
        )

    def close(self):
        self.conn.close()
        
