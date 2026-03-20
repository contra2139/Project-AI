import logging
import json
import os
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Central hub for dispatching system notifications via WebSocket and Telegram.
    Implements error isolation and lazy dependency injection.
    """
    
    def __init__(self):
        self.ws_manager: Optional[Any] = None
        self.bot: Optional[Any] = None
        self._redis: Optional[Any] = None
        
        # Admin settings from environment
        self.admin_user_id = os.getenv("TELEGRAM_ADMIN_USER_ID")

    def set_ws_manager(self, manager: Any):
        """Inject WebSocket ConnectionManager."""
        self.ws_manager = manager
        logger.debug("NotificationService: WebSocket manager injected.")

    def set_bot(self, bot: Any):
        """Inject Telegram Bot instance."""
        self.bot = bot
        logger.debug("NotificationService: Telegram bot injected.")

    def set_redis(self, redis_client: Any):
        """Inject Redis client for settings lookup."""
        self._redis = redis_client

    async def _get_settings(self) -> dict:
        """Fetch notification settings from Redis."""
        if self._redis is None:
            return {}
        try:
            settings_json = await self._redis.get("bot:notification_settings")
            if settings_json:
                return json.loads(settings_json)
        except Exception as e:
            logger.error(f"Error reading notification settings from Redis: {e}")
        return {}

    async def broadcast_price_update(self, prices: dict):
        """
        Broadcast price updates to all WebSocket clients. 
        Telegram is NOT used for price updates to avoid spam.
        """
        if self.ws_manager is None:
            logger.debug("WS Manager not initialized. Skipping price update broadcast.")
            return

        try:
            await self.ws_manager.broadcast({
                "type": "price_update",
                "data": prices,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error broadcasting price update via WebSocket: {e}")

    async def notify_signal(self, signal_data: dict):
        """Broadcast new trade signal to WS and Telegram."""
        settings = await self._get_settings()
        if not settings.get("notify_on_signal", True):
            return

        # 1. WebSocket Channel
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast({
                    "type": "signal_detected",
                    "data": signal_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error notifying signal via WS: {e}")

        # 2. Telegram Channel
        if self.bot:
            try:
                # Actual implementation in Phase 3/4
                # For now, we call the placeholder method that will be in Phase 6 requirements
                if hasattr(self.bot, "send_signal_notification"):
                    await self.bot.send_signal_notification(signal_data)
                else:
                    logger.debug("Bot.send_signal_notification not implemented yet.")
            except Exception as e:
                logger.error(f"Error notifying signal via Telegram: {e}")

    async def notify_trade_opened(self, trade_data: dict):
        """Notify when a new trade is opened."""
        settings = await self._get_settings()
        if not settings.get("notify_on_entry", True):
            return

        if self.ws_manager:
            try:
                await self.ws_manager.broadcast({
                    "type": "trade_opened",
                    "data": trade_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error notifying trade entry via WS: {e}")

        if self.bot:
            try:
                if hasattr(self.bot, "send_trade_opened"):
                    await self.bot.send_trade_opened(trade_data)
            except Exception as e:
                logger.error(f"Error notifying trade entry via Telegram: {e}")

    async def notify_trade_closed(self, trade_data: dict, pnl_r: float):
        """Notify when a trade is closed."""
        settings = await self._get_settings()
        if not settings.get("notify_on_exit", True):
            return

        if self.ws_manager:
            try:
                await self.ws_manager.broadcast({
                    "type": "trade_closed",
                    "data": {**trade_data, "pnl_r": pnl_r},
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error notifying trade exit via WS: {e}")

        if self.bot:
            try:
                if hasattr(self.bot, "send_trade_closed"):
                    await self.bot.send_trade_closed(trade_data, pnl_r)
            except Exception as e:
                logger.error(f"Error notifying trade exit via Telegram: {e}")

    async def notify_error(self, module: str, error: str, critical: bool = False):
        """
        Handle system errors.
        With critical=True: Broadcast to WS and notify Telegram Admin.
        With critical=False: Log only.
        """
        if not critical:
            logger.warning(f"System Error [{module}]: {error}")
            return

        logger.error(f"CRITICAL Error [{module}]: {error}")

        # Notify All via WebSocket
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast({
                    "type": "system_error",
                    "data": {"module": module, "error": error},
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error broadcasting error via WS: {e}")

        # Notify Admin via Telegram
        if self.bot and self.admin_user_id:
            try:
                if hasattr(self.bot, "send_admin_alert"):
                    await self.bot.send_admin_alert(f"⚠️ [SYSTEM ERROR] {module}: {error}")
            except Exception as e:
                logger.error(f"Error notifying admin via Telegram: {e}")

    async def send_daily_summary(self, summary_data: dict):
        """Send a daily performance summary via Telegram only."""
        if self.bot:
            try:
                if hasattr(self.bot, "send_daily_summary"):
                    await self.bot.send_daily_summary(summary_data)
            except Exception as e:
                logger.error(f"Error sending daily summary via Telegram: {e}")

# Global singleton or dependency-based instance
notification_service = NotificationService()
