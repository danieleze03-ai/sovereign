import os
from dotenv import load_dotenv

load_dotenv()

# Deriv
DERIV_APP_ID = os.getenv("DERIV_APP_ID")
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")
DERIV_WS_URL = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}"

# Telegram — one bot, two recipients
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = [
    os.getenv("TELEGRAM_CHAT_ID_1"),
    os.getenv("TELEGRAM_CHAT_ID_2")
]

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Trading pairs
PAIRS = [
    "CRASH_500",
    "BOOM_500",
    "CRASH_1000",
    "BOOM_1000"
]

# Pair symbol mapping for Deriv API — verified from active_symbols scan
PAIR_SYMBOLS = {
    "CRASH_500":  "CRASH500",
    "BOOM_500":   "BOOM500",
    "CRASH_1000": "CRASH1000",
    "BOOM_1000":  "BOOM1000"
}

# Risk settings
RISK_PER_TRADE_PCT = 0.02
DAILY_LOSS_LIMIT_PCT = 0.06
MIN_DAILY_TRADES = 20
MAX_DAILY_TRADES = 25

# ATR multipliers
ATR_STOP_MULTIPLIER = 1.5
ATR_TP_MULTIPLIER = 3.0

# Spike detection thresholds
SPIKE_THRESHOLDS = {
    "CRASH_500":  0.5,
    "BOOM_500":   0.5,
    "CRASH_1000": 0.8,
    "BOOM_1000":  0.8
}

# Tick zone activation
TICK_ZONE_PCT = 0.60

# Index averages
INDEX_AVERAGES = {
    "CRASH_500":  500,
    "BOOM_500":   500,
    "CRASH_1000": 1000,
    "BOOM_1000":  1000
}

# Phantom — daily trade limits
MIN_DAILY_TRADES = 20
MAX_DAILY_TRADES = 25