LOG_FILE = "./log/log.txt"
UVICORN_LOG_FILE = "./log/uvicorn_log.txt"


# Paper trading mode
PAPER_TRADING = True

START_BALANCE = 100.0 
FEE_RATE = 0.001  # 0.1% Binance spot fee


# Trading Configurations

# Tier 1: more frequent signals, less strict
SYMBOLS = [
    "BTCUSDT",
#    "ETHUSDT",
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


INTERVAL = "5m"  # candlestick interval for indicators and signals
SLEEP_INTERVAL = 5 # seconds between each loop iteration

RISK_PER_TRADE = 0.03  # 3%
MAX_POSITION_USDT = 50  # cap position size - divide by leverage in paper portfolio to get actual max position size in USDT



# less strict for testing ONlY
LESS_STRICT_SHOULD_LONG = False


# exits configuration
TAKE_PROFIT_MULTIPLIER = 4.0
STOP_LOSS_MULTIPLIER = 1.8

# or use these for calmer
# TAKE_PROFIT_MULTIPLIER = 5.0
# STOP_LOSS_MULTIPLIER = 2.0