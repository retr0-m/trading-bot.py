LOG_FILE = "./log/log.txt"
UVICORN_LOG_FILE = "./log/uvicorn_log.txt"


# Paper trading mode
PAPER_TRADING = True

START_BALANCE = 50.0
FEE_RATE = 0.001  # 0.1% Binance spot fee


# Trading Configurations

SYMBOL = "BTCUSDT"
INTERVAL = "15s"

RISK_PER_TRADE = 0.01  # 1%
MAX_POSITION_USDT = 10  # cap position size


SLEEP_INTERVAL = 2 # seconds between each loop iteration

# less strict for testing ONlY
LESS_STRICT = True