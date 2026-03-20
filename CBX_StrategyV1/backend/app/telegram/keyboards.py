from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_signal_keyboard(signal_id: str) -> InlineKeyboardMarkup:
    """
    Keyboard for signal notifications.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Đặt lệnh ngay", callback_data=f"place_order:{signal_id}"),
            InlineKeyboardButton("❌ Bỏ qua", callback_data=f"dismiss:{signal_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_status_keyboard() -> InlineKeyboardMarkup:
    """
    General keyboard for bot management.
    """
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("🛡️ Mode", callback_data="change_mode")
        ],
        [
            InlineKeyboardButton("📉 Open Trades", callback_data="list_trades"),
            InlineKeyboardButton("📊 Stats", callback_data="show_stats")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
