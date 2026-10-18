import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))
DB_PATH     = os.getenv("DB_PATH", "./storage/bot.db")
HEADLESS    = os.getenv("HEADLESS", "true").lower() == "true"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "3"))
SCRAPE_TIMEOUT   = int(os.getenv("SCRAPE_TIMEOUT", "30"))
CACHE_TTL_HOURS  = int(os.getenv("CACHE_TTL_HOURS", "24"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
CAPTCHAAI_API_KEY     = os.getenv("CAPTCHAAI_API_KEY", "")
DAPACHECKER_COOKIES_PATH = os.getenv("DAPACHECKER_COOKIES_PATH", "./cookies/dapachecker.json")

PAKET = {
    "starter": {"kredit": 50,    "harga": 15000,  "label": "Starter — 50 kredit — Rp15.000",    "btn": "🥉 Starter  · 50 kredit · Rp15.000"},
    "basic":   {"kredit": 200,   "harga": 40000,  "label": "Basic — 200 kredit — Rp40.000",      "btn": "🥈 Basic    · 200 kredit · Rp40.000"},
    "pro":     {"kredit": 500,   "harga": 75000,  "label": "Pro — 500 kredit — Rp75.000",        "btn": "🥇 Pro      · 500 kredit · Rp75.000"},
    "bulk":    {"kredit": 1000,  "harga": 120000, "label": "Bulk — 1.000 kredit — Rp120.000",    "btn": "💎 Bulk    · 1.000 kredit · Rp120.000"},
}

REKENING = """
  Bank BCA
  No Rek : 1234567890
  Atas Nama : Nama Anda
"""

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0")) if os.getenv("LOG_CHANNEL_ID") else 0

ADMIN_USERNAME = "adminusername"  # ganti dengan username Telegram admin
