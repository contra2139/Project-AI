import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration loaded from .env file.
    """
    def __init__(self):
        load_dotenv()
        self._validate_config()

    def _validate_config(self):
        """Validates that essential config variables are present."""
        # Optional: Add validation logic here if needed
        pass

    @property
    def tiktok_username(self):
        return os.getenv("TIKTOK_USERNAME")

    @property
    def facebook_page_token(self):
        return os.getenv("FACEBOOK_PAGE_TOKEN")
    
    @property
    def facebook_page_id(self):
        return os.getenv("FACEBOOK_PAGE_ID")

    @property
    def google_credentials_file(self):
        return os.getenv("GOOGLE_CREDENTIALS_FILE", "service_account.json")

    @property
    def tiktok_sheet_id(self):
        return os.getenv("TIKTOK_SHEET_ID")

    @property
    def facebook_sheet_id(self):
        return os.getenv("FACEBOOK_SHEET_ID")

    @property
    def update_interval(self):
        return int(os.getenv("UPDATE_INTERVAL_SECONDS", 5))

    @property
    def log_level(self):
        return os.getenv("LOG_LEVEL", "INFO")

# Singleton instance
config = ConfigManager()
