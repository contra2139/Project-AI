import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    TRADE_MODE = os.getenv("TRADE_MODE", "paper_trading")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.BINANCE_API_KEY: missing.append("BINANCE_API_KEY")
        if not cls.BINANCE_API_SECRET: missing.append("BINANCE_API_SECRET")
        if not cls.TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
        
        if missing:
            print(f"⚠️ WARNING: Missing environment variables: {', '.join(missing)}")
            print("Please configure them in the .env file.")
            
config = Config()
