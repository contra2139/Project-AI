import os
import logging
from typing import Set
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Load and parse allowed user IDs from environment
ALLOWED_IDS_STR = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
ALLOWED_IDS: Set[int] = {
    int(x.strip()) 
    for x in ALLOWED_IDS_STR.split(",") 
    if x.strip().isdigit()
}

ADMIN_USER_ID = int(os.getenv("TELEGRAM_ADMIN_USER_ID", "0"))

def require_auth(func):
    """
    Decorator to restrict access to whitelisted Telegram users.
    Implements 'Stealth Mode': No reply or logging for unauthorized users.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
            
        user_id = update.effective_user.id
        if user_id not in ALLOWED_IDS:
            # Silent return for unauthorized users (Stealth Mode)
            return
            
        return await func(update, context)
    return wrapper

def require_admin(func):
    """
    Decorator to restrict access to the Admin user only.
    Replies with a generic error message for non-admin whitelisted users.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        # First ensure they are at least authorized
        if user_id not in ALLOWED_IDS:
            return
            
        if user_id != ADMIN_USER_ID:
            if update.effective_message:
                await update.effective_message.reply_text("⛔ Lệnh này chỉ dành cho admin.")
            return
            
        return await func(update, context)
    return wrapper
