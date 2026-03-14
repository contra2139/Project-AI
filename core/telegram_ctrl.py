# Telegram Controller Module
# Phân tích cú pháp (Router) cho các loại lệnh: Tư vấn, Giao dịch tức thì, Giao dịch chờ

import re

# TODO: Regex patterns
# 1. TICKER_PATTERN (Ví dụ: BNBUSDC)
# 2. IMMEDIATE_PATTERN (Ví dụ: Long price 500 TP/SL 550/450)
# 3. CONDITIONAL_PATTERN (Ví dụ: if 480 Long price 490 TP/SL 550/450)

def parse_user_message(message: str) -> dict:
    # Router quyết định sẽ thực thi module nào
    # Trả về dict action {'type': 'analyze', 'symbol': 'BNBUSDC'}
    pass

async def start_telegram_bot():
    # Khởi động python-telegram-bot Updater/Application
    pass
