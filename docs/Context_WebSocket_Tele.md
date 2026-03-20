CBX Trading Bot — Python FastAPI, PostgreSQL, Redis.
python-telegram-bot v20 (async).

Giai đoạn 4 REST API hoàn thành.
Redis đang dùng fakeredis cho dev — production dùng Redis thật.

Scanner đã có signal_manager.py gửi signal vào Redis
với key pattern "signal:{symbol}:{timestamp}" TTL=15 phút.

Settings trong Redis:
  "bot:mode" → "auto" hoặc "manual"
  "bot:risk_settings" → JSON
  "bot:notification_settings" → JSON

Settings trong .env:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_WEBHOOK_SECRET
  TELEGRAM_ALLOWED_USER_IDS  (comma-separated)
  TELEGRAM_ADMIN_USER_ID
  TELEGRAM_CMD_BUY, SELL, CLOSE, STATUS, MODE, SIGNALS, TRADES

Yêu cầu bắt buộc:
1. Async/await toàn bộ
2. Whitelist user_id — không reply user không được phép
3. KHÔNG gọi Binance API trực tiếp từ Telegram handlers
   — handlers chỉ gọi các service đã có
4. Mọi lỗi trong handler phải được catch, không crash bot