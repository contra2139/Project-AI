import os
from typing import Optional
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.telegram.handlers import (
    start_handler, status_handler, buy_handler, sell_handler,
    close_handler, ask_handler, callback_handler
)

logger = logging.getLogger(__name__)

# This will be initialized in main.py
telegram_app: Optional[Application] = None

def init_telegram_app() -> Application:
    """
    Initialize the Telegram Application using the modern v20 builder.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment.")
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    application = (
        Application.builder()
        .token(token)
        .build()
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("buy", buy_handler))
    application.add_handler(CommandHandler("sell", sell_handler))
    application.add_handler(CommandHandler("close", close_handler))
    application.add_handler(CommandHandler("ask", ask_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Telegram Application handlers registered successfully.")
    return application

async def process_telegram_update(application: Application, update_data: dict):
    """
    Process a single update received via webhook.
    """
    try:
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")
