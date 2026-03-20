Tạo WebSocket endpoint và Telegram Bot cho CBX Bot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 1: backend/app/api/websocket.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WebSocket endpoint: GET /ws?token={jwt}

Connection manager:
  Class ConnectionManager:
    connections: dict[str, WebSocket]  ← {client_id: ws}
    
    async connect(client_id, ws): accept + lưu vào dict
    disconnect(client_id): xóa khỏi dict
    async broadcast(event_type, data): gửi tới tất cả clients
    async send_to(client_id, event_type, data): gửi 1 client

Message format (JSON):
  {
    "type": "signal_detected" | "trade_opened" | "trade_closed"
           | "price_update" | "bot_status" | "regime_change",
    "data": {...},
    "timestamp": "ISO8601"
  }

Endpoint logic:
  1. Validate JWT token từ query param
  2. Nếu invalid → close với code 4001
  3. Nếu valid → connect + gửi "connection_established"
  4. Keep-alive: gửi ping mỗi 30 giây
  5. Khi disconnect: cleanup từ ConnectionManager

Route: app.add_api_websocket_route("/ws", ws_endpoint)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 2: backend/app/services/notification_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Class NotificationService:
Trung tâm gửi thông báo — cả WebSocket lẫn Telegram.

async notify_signal(signal):
  Đọc "bot:notification_settings" từ Redis
  Nếu notify_on_signal=True:
    → ws_manager.broadcast("signal_detected", signal_data)
    → telegram.send_signal_notification(signal)

async notify_trade_opened(trade):
  Nếu notify_on_entry=True:
    → ws_manager.broadcast("trade_opened", trade_data)
    → telegram.send_trade_opened(trade)

async notify_trade_closed(trade, pnl_r):
  Nếu notify_on_exit=True:
    → ws_manager.broadcast("trade_closed", {trade, pnl_r})
    → telegram.send_trade_closed(trade, pnl_r)

async broadcast_price_update(prices: dict):
  → ws_manager.broadcast("price_update", prices)
  Không gửi Telegram (quá nhiều)

async notify_error(module, error, critical=False):
  Log error
  Nếu critical=True: gửi Telegram tới ADMIN_USER_ID
  → ws_manager.broadcast("system_error", {module, error})

async send_daily_summary():
  Tính metrics ngày từ DB
  Format message đẹp
  Gửi Telegram tới tất cả ALLOWED_USER_IDS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 3: backend/app/telegram/bot.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Setup Telegram Application (python-telegram-bot v20):
  - Init với TELEGRAM_BOT_TOKEN
  - Register tất cả handlers
  - Webhook setup tại /tg/webhook

FastAPI route:
  POST /tg/webhook
  Header check: X-Telegram-Bot-Api-Secret-Token == TELEGRAM_WEBHOOK_SECRET
  Nếu không khớp → 403
  Nếu khớp → forward update tới Application

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 4: backend/app/telegram/auth.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Decorator require_auth:
  Đọc TELEGRAM_ALLOWED_USER_IDS từ Settings
  Nếu update.effective_user.id không trong list:
    → KHÔNG reply, KHÔNG log user info (stealth mode)
    → return sớm
  Nếu có → tiếp tục handler

Decorator require_admin:
  Kiểm tra user.id == TELEGRAM_ADMIN_USER_ID
  Nếu không phải admin → reply "Lệnh này chỉ dành cho admin"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 5: backend/app/telegram/handlers.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tất cả handlers dùng @require_auth

/start:
  Reply: Welcome message + hướng dẫn lệnh cơ bản
  Show main keyboard

/status:
  Query: equity, daily PnL R, open positions, bot mode, regime
  Format:

🤖 CBX Bot Status
━━━━━━━━━━━━━━━
💰 Equity:    $10,250.00
📈 Daily PnL: +1.2R (+$30.6)
📊 Positions: 1 open
⚙️ Mode:      MANUAL
🌡️ Regime:   NORMAL

/signals:
  Load 5 signals gần nhất từ Redis
  Mỗi signal: symbol, side, quality, entry/SL/TP

/trades:
  Load 5 trades gần nhất từ DB
  Format bảng: symbol | side | PnL | exit reason

/mode auto | /mode manual:
  @require_admin
  Gọi PATCH /api/v1/settings/mode (internal service call)
  Reply: "✅ Mode đã đổi sang: AUTO"

/pause | /resume:
  @require_admin
  Set scanner running state trong Redis

/buy SYMBOL SIZE_PCT [SL] [TP]:
  Parse command từ TELEGRAM_CMD_BUY setting
  Validate: symbol active, size 0.1-5.0, SL/TP hợp lý
  Nếu thiếu SL/TP: lấy từ signal gần nhất của symbol đó
  Tạo EntryOrder và gọi _execute_entry()
  Reply: "✅ Đặt lệnh LONG BTCUSDC thành công\nEntry: $95,420"

/sell SYMBOL SIZE_PCT [SL] [TP]:
  Tương tự /buy nhưng SHORT

/close SYMBOL:
  Tìm open trade của symbol đó
  Gọi POST /api/v1/trades/{trade_id}/close
  Reply: "✅ Đã đóng lệnh BTCUSDC\nPnL: +1.2R (+$30.6)"

/close all:
  Đóng tất cả open trades
  Reply summary

/ask [question]:
  Gọi Gemini AI với context: signal hiện tại + portfolio state
  Reply câu trả lời tiếng Việt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 6: backend/app/telegram/notifications.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

send_signal_notification(bot, signal):
  Format message:
🔥 CBX SIGNAL
Symbol: BTCUSDC
Side:   LONG 📈
Entry:  ~95,420
SL:     94,890 (-0.56%)
TP1:    95,950 (+0.56%)
Quality:  ████████░░ 8.2/10
Regime:   NORMAL | EMA50 ↗
⏱ Valid: 15 phút

InlineKeyboard:
    [✅ Đặt lệnh ngay] callback: place_order:{signal_id}
    [❌ Bỏ qua]       callback: dismiss:{signal_id}

send_trade_opened(bot, trade):
  "✅ Vào lệnh {LONG/SHORT} {symbol}\n
   Entry: {price} | SL: {sl} | TP1: {tp1}"

send_trade_closed(bot, trade, pnl_r):
  Emoji: ✅ nếu lãi, ❌ nếu lỗ
  "{emoji} Đóng {symbol}\n
   PnL: {pnl_r:+.2f}R | Lý do: {exit_reason}"

send_admin_alert(bot, message):
  Gửi tới TELEGRAM_ADMIN_USER_ID
  Prefix: "⚠️ [SYSTEM ALERT]\n"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 7: backend/app/telegram/keyboards.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main_menu_keyboard():
  ReplyKeyboardMarkup:
    Row 1: ["📊 Status", "📡 Signals"]
    Row 2: ["💼 Trades", "⚙️ Settings"]

signal_action_keyboard(signal_id):
  InlineKeyboardMarkup:
    [✅ Đặt lệnh ngay | ❌ Bỏ qua]

confirm_order_keyboard(order_preview):
  InlineKeyboardMarkup:
    [✅ Xác nhận | ❌ Hủy]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: backend/tests/test_telegram_handlers.py (5 cases)
Dùng python-telegram-bot test utilities (mock Update)

Test 1: Auth whitelist — user không được phép
  Mock Update với user_id không trong ALLOWED_USER_IDS
  Gọi /start handler
  Assert: bot.send_message KHÔNG được gọi (stealth mode)

Test 2: Auth whitelist — user được phép
  Mock Update với user_id hợp lệ
  Gọi /start handler
  Assert: bot.send_message được gọi 1 lần

Test 3: /buy command parse đúng
  Message text: "/buy BTC 1.0 95000 98500"
  Assert: symbol="BTCUSDC", size_pct=1.0,
          sl=Decimal("95000"), tp=Decimal("98500")

Test 4: /buy command thiếu SL/TP
  Message text: "/buy BTC 0.5"
  Assert: parser không raise exception
  Assert: sl=None, tp=None (sẽ lấy từ signal)

Test 5: WebSocket broadcast format
  Gọi ws_manager.broadcast("signal_detected", mock_signal)
  Assert: message JSON có đủ fields: type, data, timestamp
  Assert: type == "signal_detected"

Chạy: python -m pytest backend/tests/test_telegram_handlers.py -v
Expected: 5/5 PASSED