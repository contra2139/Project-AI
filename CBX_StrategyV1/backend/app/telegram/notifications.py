import logging
from telegram import Bot
from app.telegram.keyboards import get_signal_keyboard

logger = logging.getLogger(__name__)

async def send_signal_notification(bot: Bot, chat_id: int, signal_data: dict):
    """
    Send a formatted signal notification to a user.
    """
    symbol = signal_data.get("symbol", "UNKNOWN")
    side = signal_data.get("side", "UNKNOWN")
    entry = signal_data.get("entry_price", 0)
    sl = signal_data.get("sl", 0)
    tp1 = signal_data.get("tp1", 0)
    quality = signal_data.get("quality_score", 0)
    regime = signal_data.get("market_regime", "UNKNOWN")
    ema_slope = signal_data.get("ema_slope_trend", "RANGE")
    valid_minutes = signal_data.get("validity_minutes", 15)
    signal_id = signal_data.get("signal_id", "none")

    # Format quality bar
    filled_bars = int(quality)
    bar_str = "█" * filled_bars + "░" * (10 - filled_bars)

    side_emoji = "📈" if side.upper() == "LONG" else "📉"
    
    message = (
        f"🔥 *CBX SIGNAL*\n"
        f"Symbol: `{symbol}`\n"
        f"Side:   *{side.upper()}* {side_emoji}\n"
        f"Entry:  ~{entry:,.2f}\n"
        f"SL:     {sl:,.2f} ({((sl/entry - 1)*100):.2f}%)\n"
        f"TP1:    {tp1:,.2f} ({((tp1/entry - 1)*100):.2f}%)\n"
        f"Quality:  `{bar_str}` {quality}/10\n"
        f"Regime:   {regime} | EMA50 {ema_slope}\n"
        f"⏱ Valid: {valid_minutes} phút"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=get_signal_keyboard(signal_id)
        )
    except Exception as e:
        logger.error(f"Failed to send signal notification: {e}")
