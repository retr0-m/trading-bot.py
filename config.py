LOG_FILE = "./log/log.txt"
UVICORN_LOG_FILE = "./log/uvicorn_log.txt"


# Paper trading mode
PAPER_TRADING = True

START_BALANCE = 50.0
FEE_RATE = 0.001  # 0.1% Binance spot fee


# Trading Configurations

# Tier 1: more frequent signals, less strict
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
]

# Tier 2: less frequent signals, more strict
# SYMBOLS = [
#     "BTCUSDT",
#     "ETHUSDT",
#     "BNBUSDT",
#     "SOLUSDT",
#     "XRPUSDT",
# ]


# Tier 3: high volume, more volatile, more strict
# SYMBOLS = [
#     "ADAUSDT",
#     "DOGEUSDT",
#     "AVAXUSDT",
#     "LINKUSDT",
#     "MATICUSDT",
# ]

# Tier 4: all 300+ symbols, very strict
# SYMBOLS = [
#     "BTCUSDT",
#     "ETHUSDT",
#     "BNBUSDT",
#     "SOLUSDT",
#     "XRPUSDT",
#     "ADAUSDT",
#     "DOGEUSDT",
#     "AVAXUSDT",
#     "LINKUSDT",
#     "MATICUSDT",
    
# ]


INTERVAL = "15s"

RISK_PER_TRADE = 0.01  # 1%
MAX_POSITION_USDT = 10  # cap position size


SLEEP_INTERVAL = 2 # seconds between each loop iteration

# less strict for testing ONlY
LESS_STRICT_SHOULD_LONG = True


# exits configuration
TAKE_PROFIT_MULTIPLIER = 2.0
STOP_LOSS_MULTIPLIER = 1.0