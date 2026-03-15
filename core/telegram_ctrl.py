import re

# ==========================================
# REGEX PATTERNS CỦA 3 LUỒNG LỆNH
# ==========================================

# 1. ANALYZE PATTERN: Nhận diện /scan SYMBOL hoặc chỉ SYMBOL
# Format: /scan BTCUSDT hoặc BTCUSDT (không dấu cách)
ANALYZE_PATTERN = re.compile(r"^(?:/scan\s+)?(?P<symbol>[A-Za-z0-9]+)$", re.IGNORECASE)

# 2. IMMEDIATE TRADE PATTERN: /trade SYMBOL ACTION PRICE TP/SL TP/SL (hoặc không /trade)
# Format: /trade BTCUSDT Long 70000 75000/65000
IMMEDIATE_PATTERN = re.compile(
    r"^(?:/trade\s+)?(?P<symbol>[A-Za-z0-9]+)\s+(?P<action>long|short)\s+(?:price\s+)?(?P<price>[\d\.]+)\s+(?:tp/sl\s+)?(?P<tp>[\d\.]+)/(?P<sl>[\d\.]+)(?:\s+(?P<risk>[\d\.]+))?$", 
    re.IGNORECASE
)

# 3. CONDITIONAL PATTERN: /limit SYMBOL ACTION TRIGGER PRICE TP/SL TP/SL [RISK]
# Format: /limit BTCUSDT Long 68000 68500 75000/65000 50
CONDITIONAL_PATTERN = re.compile(
    r"^(?:/limit\s+)?(?P<symbol>[A-Za-z0-9]+)\s+(?P<action>long|short)\s+(?:if\s+)?(?P<condition_price>[\d\.]+)\s+(?:price\s+)?(?P<price>[\d\.]+)\s+(?:tp/sl\s+)?(?P<tp>[\d\.]+)/(?P<sl>[\d\.]+)(?:\s+(?P<risk>[\d\.]+))?$", 
    re.IGNORECASE
)

# 4. SHORTCUT PATTERNS: LLL SYMBOL PRICE / SSS SYMBOL PRICE
# LLL: Long, AI TP/SL, 10 Risk, 15 Leverage
# SSS: Short, AI TP/SL, 10 Risk, 15 Leverage
SHORTCUT_PATTERN = re.compile(r"^(?P<type>LLL|SSS)\s+(?P<symbol>[A-Za-z0-9]+)\s+(?P<price>[\d\.]+)$", re.IGNORECASE)

# 5. SIMPLE COMMANDS
STATUS_PATTERN = re.compile(r"^/status$", re.IGNORECASE)
HELP_PATTERN = re.compile(r"^/(?:help|start)$", re.IGNORECASE)
ORDERS_PATTERN = re.compile(r"^/orders$", re.IGNORECASE)

def parse_user_message(message: str) -> dict:
    """
    Phân tích cú pháp tin nhắn Telegram. Trả về Dictionary hành động.
    """
    msg = message.strip()
    
    # Simple Commands
    if HELP_PATTERN.match(msg): return {"type": "help"}
    if STATUS_PATTERN.match(msg): return {"type": "status"}
    if ORDERS_PATTERN.match(msg): return {"type": "orders"}

    # Shortcuts LLL/SSS
    match_short = SHORTCUT_PATTERN.match(msg)
    if match_short:
        return {
            "type": "shortcut_order",
            "cmd": match_short.group("type").upper(),
            "symbol": match_short.group("symbol").upper(),
            "price": float(match_short.group("price"))
        }

    # Lệnh Điều Kiện (Limit/Conditional)
    match_cond = CONDITIONAL_PATTERN.match(msg)
    if match_cond:
        return {
            "type": "conditional_order",
            "symbol": match_cond.group("symbol").upper(),
            "condition_price": float(match_cond.group("condition_price")),
            "action": match_cond.group("action").upper(),
            "price": float(match_cond.group("price")),
            "tp": float(match_cond.group("tp")),
            "sl": float(match_cond.group("sl")),
            "usdt_risk": float(match_cond.group("risk")) if match_cond.group("risk") else 20.0
        }

    # Lệnh Thị Trường (Immediate)
    match_imm = IMMEDIATE_PATTERN.match(msg)
    if match_imm:
        return {
            "type": "immediate_order",
            "symbol": match_imm.group("symbol").upper(),
            "action": match_imm.group("action").upper(),
            "price": float(match_imm.group("price")),
            "tp": float(match_imm.group("tp")),
            "sl": float(match_imm.group("sl")),
            "usdt_risk": float(match_imm.group("risk")) if match_imm.group("risk") else 20.0
        }

    # Tư Vấn Giao Dịch (Analyze)
    match_analyze = ANALYZE_PATTERN.match(msg)
    if match_analyze:
        return {
            "type": "analyze",
            "symbol": match_analyze.group("symbol").upper()
        }

    # Trường hợp không khớp Format nào
    return {"type": "unknown", "raw_message": msg}

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import config
from core.data_ingestion import get_multi_timeframe_data
from core.ta_calculator import calculate_ta
from core.ai_brain import generate_trading_decision
from core.binance_exec import execute_trade, execute_conditional_order, get_balance, get_open_orders
import logging
logger = logging.getLogger(__name__)

# Lưu trữ trạng thái hội thoại cho từng User (Chat ID)
# Format: { chat_id: { "state": "WAIT_CONFIRM", "data": {...} } }
USER_STATES = {}

def safe_extract_price(value):
    """Trích xuất con số từ chuỗi AI trả về (Xử lý dải giá '650-655' hoặc ký tự lạ)"""
    if not value: return 0.0
    if isinstance(value, (int, float)): return float(value)
    
    # Xử lý chuỗi
    try:
        s = str(value).replace("$", "").replace(",", "").strip()
        # Nếu là dải giá (VD: 651.60 - 646.50)
        if "-" in s:
            parts = s.split("-")
            # Lấy giá trị trung bình để an toàn
            v1 = float(parts[0].strip())
            v2 = float(parts[1].strip())
            return round((v1 + v2) / 2, 4)
        return float(s)
    except Exception as e:
        logger.error(f"Lỗi safe_extract_price cho '{value}': {e}")
        return 0.0

async def run_analysis(symbol: str, update: Update):
    """Hàm helper chạy phân tích AI và lưu kết quả"""
    try:
        # 1. Kéo mảng Data OHLCV
        raw_data = await get_multi_timeframe_data(symbol, limit=250)
        
        # 2. Xử lý TA
        clean_data = {}
        for tf, df in raw_data.items():
            if not df.empty:
                clean_data[tf] = calculate_ta(df)
        
        # 3. Yêu cầu AI Decision
        if clean_data:
            ai_result = await generate_trading_decision(symbol, clean_data)
            if isinstance(ai_result, list) and len(ai_result) > 0:
                ai_result = ai_result[0]
            elif not isinstance(ai_result, dict):
                ai_result = {}

            ai_result["symbol"] = symbol
            
            # Lưu vào AI Memory (Buffer cho nhiều mã)
            import json, os
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # 1. Update latest_ai.json (cho Dashboard)
            with open(os.path.join(log_dir, "latest_ai.json"), "w", encoding="utf-8") as f:
                json.dump(ai_result, f, ensure_ascii=False, indent=4)
            
            # 2. Update ai_memory.json (Buffer lâu dài cho nhiều mã)
            import time
            memory_file = os.path.join(log_dir, "ai_memory.json")
            memory = {}
            if os.path.exists(memory_file):
                try:
                    with open(memory_file, "r", encoding="utf-8") as f:
                        memory = json.load(f)
                except: pass
            
            # Lưu kèm timestamp
            ai_result["timestamp"] = time.time()
            memory[symbol.upper()] = ai_result
            
            # --- AUTO CLEANUP (GC) ---
            # Xóa mã đã cũ hơn 24h hoặc giới hạn 50 mã gần nhất
            current_t = time.time()
            clean_memory = {}
            # Lọc theo thời gian (dưới 24h)
            for sym, data in memory.items():
                if current_t - data.get("timestamp", 0) < 86400:
                    clean_memory[sym] = data
            
            # Giới hạn số lượng (giữ 50 mã mới nhất)
            if len(clean_memory) > 50:
                sorted_syms = sorted(clean_memory.keys(), key=lambda x: clean_memory[x].get("timestamp", 0), reverse=True)
                clean_memory = {s: clean_memory[s] for s in sorted_syms[:50]}

            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(clean_memory, f, ensure_ascii=False, indent=4)
            
            return ai_result
    except Exception as e:
        logger.error(f"Lỗi run_analysis: {e}")
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback khi nhận được tin nhắn từ User."""
    chat_id = str(update.message.chat_id)
    text = update.message.text.strip()

    # BẢO MẬT
    if chat_id != config.TELEGRAM_CHAT_ID: return

    # --- LUỒNG XỬ LÝ TRẠNG THÁI (STATE MACHINE) ---
    if chat_id in USER_STATES:
        state_info = USER_STATES[chat_id]
        state = state_info.get("state")
        
        # 1. Chờ xác nhận Y/N khi đánh ngược AI
        if state == "WAIT_STOP_CONFIRM":
            if text.upper() == "N":
                await update.message.reply_text("❌ Đã hủy lệnh theo yêu cầu của anh. Hãy cẩn thận với xu hướng AI nhé!")
                del USER_STATES[chat_id]
                return
            elif text.upper() == "Y":
                USER_STATES[chat_id]["state"] = "WAIT_TPSL_INPUT"
                await update.message.reply_text("👌 Anh đã chọn tiếp tục. Vui lòng nhập TP/SL thủ công theo format: `[Giá TP]/[Giá SL]`\nVí dụ: `700/600`", parse_mode='Markdown')
                return
            else:
                await update.message.reply_text("❓ Bot chưa hiểu. Vui lòng gõ **Y** (Tiếp tục) hoặc **N** (Hủy lệnh).", parse_mode='Markdown')
                return

        # 2. Chờ nhập TP/SL thủ công
        if state == "WAIT_TPSL_INPUT":
            try:
                parts = text.split("/")
                if len(parts) == 2:
                    tp = float(parts[0])
                    sl = float(parts[1])
                    data = state_info["data"]
                    
                    await update.message.reply_text(f"⏳ Đang thực thi lệnh {data['symbol']} {data['side']} với TP: {tp} | SL: {sl}...")
                    result = await execute_trade(
                        symbol=data['symbol'],
                        action=data['side'],
                        price=data['price'],
                        sl=sl,
                        tp=tp,
                        usdt_risk=10.0
                    )
                    if result["status"] == "success":
                        await update.message.reply_text(f"✅ Đã đặt lệnh thành công (Manual TP/SL)!")
                    else:
                        await update.message.reply_text(f"❌ Lỗi: {result['message']}")
                    
                    del USER_STATES[chat_id]
                    return
                else:
                    await update.message.reply_text("⚠️ Cú pháp sai. Hãy nhập dạng: `[TP]/[SL]`. VD: `700/600`")
                    return
            except Exception:
                await update.message.reply_text("⚠️ Giá trị không khớp. Hãy nhập số dạng: `[TP]/[SL]`")
                return

    # Phân tích cú pháp tin nhắn thường
    action = parse_user_message(text)
    
    if action["type"] == "analyze":
        symbol = action["symbol"]
        await update.message.reply_text(f"🔍 Đang thu thập dữ liệu và phân tích đa khung thời gian cho {symbol}...")
        ai_result = await run_analysis(symbol, update)
        
        if ai_result:
            decision = ai_result.get("decision", "UNKNOWN")
            reasoning = ai_result.get("reasoning", "Không có giải thích từ AI.")
            entry = ai_result.get("entry", "N/A")
            sl = ai_result.get("stop_loss", "N/A")
            tp = ai_result.get("take_profit", "N/A")
            
            logger.info(f"🚨 [TÍN HIỆU AI] Token: {symbol} | Action: {decision}")
            
            report = ai_result.get("report")
            if report:
                TELEGRAM_MAX_LENGTH = 4096
                sections = report.split("---")
                msg_buffer = ""
                for section in sections:
                    section = section.strip()
                    if not section: continue
                    candidate = (msg_buffer + "\n\n" + section).strip()
                    if len(candidate) > TELEGRAM_MAX_LENGTH:
                        if msg_buffer: await update.message.reply_text(msg_buffer, parse_mode=None)
                        msg_buffer = section
                    else:
                        msg_buffer = candidate
                if msg_buffer: await update.message.reply_text(msg_buffer, parse_mode=None)
            else:
                msg_reply = f"🤖 **AI TRADING BRAIN** 🤖\n\nTín hiệu: {decision}\n\n💡 Lý do: {reasoning}\n\n"
                if decision in ["LONG", "SHORT"]:
                    msg_reply += f"🎯 Entry: {entry}\n🛡️ SL: {sl}\n💰 TP: {tp}"
                await update.message.reply_text(msg_reply, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Phân tích thất bại cho mã {symbol}.")
        
    elif action["type"] == "immediate_order":
        symbol = action["symbol"]
        await update.message.reply_text(f"⏳ Đang xử lý lệnh thị trường cho {symbol} {action['action']} tại {action['price']}...")
        result = await execute_trade(
            symbol=symbol,
            action=action['action'],
            price=action['price'],
            sl=action['sl'],
            tp=action['tp'],
            usdt_risk=action.get('usdt_risk', 20.0)
        )
        if result["status"] == "success":
            await update.message.reply_text(f"✅ KHỚP LỆNH THÀNH CÔNG!\n🛒 Symbol: {symbol}\n🆔 ID: `{result['order']['orderId']}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ LỖI VÀO LỆNH: {result['message']}")
            
    elif action["type"] == "conditional_order":
        symbol = action["symbol"]
        await update.message.reply_text(f"⏳ Đang thiết lập bẫy giá {action['condition_price']} cho {symbol}...")
        result = await execute_conditional_order(
            symbol=symbol,
            action=action['action'],
            trigger_price=action['condition_price'],
            entry_price=action['price'],
            sl=action['sl'],
            tp=action['tp'],
            usdt_risk=action.get('usdt_risk', 20.0)
        )
        if result["status"] == "success":
            await update.message.reply_text(f"✅ GÀI BẪY THÀNH CÔNG!\n🛒 Symbol: {symbol}\n⏰ Khi giá chạm {action['condition_price']} sẽ kích hoạt.\n🆔 ID: `{result['order']['orderId']}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ LỖI CÀI BẪY: {result['message']}")

    elif action["type"] == "shortcut_order":
        symbol = action["symbol"]
        cmd = action["cmd"]
        entry_price = action["price"]
        side = "LONG" if cmd == "LLL" else "SHORT"
        
        await update.message.reply_text(f"🚀 Shortcut {cmd} {symbol} tại {entry_price}. Đang kiểm tra AI Brain...")
        
        # 1. Thử lấy dữ liệu từ AI Memory (Buffer)
        ai_data = None
        target_symbol = symbol.upper()
        try:
            import json, os
            memory_file = os.path.join(os.getcwd(), "logs", "ai_memory.json")
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                
                # Logic so khớp thông minh: BNB match BNBUSDC
                for m_symbol, m_data in memory.items():
                    if target_symbol == m_symbol or target_symbol in m_symbol or m_symbol in target_symbol:
                        ai_data = m_data
                        # Nếu khớp tương đối, cập nhật lại symbol chuẩn của sàn
                        symbol = m_symbol 
                        break
        except Exception: pass

        # 2. Kiểm tra độ tươi (Freshness) - 60 phút
        is_fresh = False
        if ai_data:
            import time
            last_time = ai_data.get("timestamp", 0)
            if time.time() - last_time < 3600: # 60 phút
                is_fresh = True
            else:
                await update.message.reply_text(f"⏳ Dữ liệu {symbol} đã cũ (>60p). Đang cập nhật phân tích mới...")

        # 3. Nếu thiếu hoặc cũ -> Chạy Auto-Scan
        if not ai_data or not is_fresh:
            ai_data = await run_analysis(symbol, update)
            if not ai_data:
                await update.message.reply_text("❌ Không thể phân tích tự động. Anh hãy thử lại sau nhé.")
                return

        # 3. Confluence Check (So sánh xu hướng)
        decision = ai_data.get("decision", "NEUTRAL").upper()
        sl = safe_extract_price(ai_data.get("stop_loss", 0))
        tp = safe_extract_price(ai_data.get("take_profit", 0))

        is_opposite = (side == "LONG" and decision == "SHORT") or (side == "SHORT" and decision == "LONG")
        
        if is_opposite:
            # Ngược hướng -> Hỏi ý kiến
            USER_STATES[chat_id] = {
                "state": "WAIT_STOP_CONFIRM",
                "data": {"symbol": symbol, "side": side, "price": entry_price}
            }
            await update.message.reply_text(
                f"⚠️ **CẢNH BÁO RỦI RO**\n\n"
                f"Anh đang đặt lệnh `{side}` nhưng AI báo xu hướng là `{decision}`.\n"
                f"Anh có muốn tiếp tục đánh ngược xu hướng AI không?\n\n"
                f"Gõ **Y** (có) hoặc **N** (không).",
                parse_mode='Markdown'
            )
            return
        
        # 4. Thực thi nếu khớp hướng hoặc Neutral
        if sl == 0 or tp == 0:
            # AI Neutral hoặc thiếu TP/SL -> Hỏi nhập thủ công
            USER_STATES[chat_id] = {
                "state": "WAIT_TPSL_INPUT",
                "data": {"symbol": symbol, "side": side, "price": entry_price}
            }
            await update.message.reply_text(f"💡 AI đang `{decision}` (không có TP/SL cụ thể). Vui lòng nhập TP/SL: `[TP]/[SL]`")
            return

        result = await execute_trade(symbol, side, entry_price, sl, tp, usdt_risk=10.0)
        if result["status"] == "success":
            await update.message.reply_text(
                f"✅ **LỆNH SHORTCUT THÀNH CÔNG**\n"
                f"🛒 `{symbol}` {side} | Giá: `{entry_price}`\n"
                f"🛡️ SL: `{sl}` | 💰 TP: `{tp}` (Theo AI)",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ LỖI: {result['message']}")

    elif action["type"] == "status":
        balance = await get_balance()
        mode = "LIVE Trading" if config.TRADE_MODE.lower() == "real" else "PAPER Trading (Testnet)"
        await update.message.reply_text(f"📊 **TRẠNG THÁI HỆ THỐNG**\n\n💰 Số dư ví Futures: `{balance} USDT`\n🚀 Chế độ: `{mode}`", parse_mode='Markdown')

    elif action["type"] == "orders":
        orders = await get_open_orders()
        if not orders:
            await update.message.reply_text("📭 Hiện không có lệnh nào đang chờ.")
            return
        
        msg_orders = "📝 **DANH SÁCH LỆNH CHỜ:**\n\n"
        for o in orders:
            msg_orders += f"🔸 `{o['symbol']}` | {o['side']} {o['type']}\n   Giá: {o['stopPrice'] if o['stopPrice'] != '0' else o['price']} | Qty: {o['origQty']}\n\n"
        await update.message.reply_text(msg_orders, parse_mode='Markdown')

    elif action["type"] == "help":
        help_text = (
            "🤖 **HƯỚNG DẪN LỆNH CRYPTO AI BOT**\n\n"
            "🔍 **Phân tích (AI Scan):**\n"
            "`/scan BNBUSDC` hoặc `BNBUSDC` \n"
            "➜ Bot sẽ phân tích đa khung thời gian & báo cáo AI.\n\n"
            "💹 **Giao dịch thị trường (Trade):**\n"
            "`/trade BTCUSDT LONG 70000 75000/65000 [RISK]` \n"
            "➜ Vào lệnh Long BTC mốc 70k, TP 75k, SL 65k, Risk [RISK] USDT (mặc định 20).\n\n"
            "⏰ **Giao dịch bẫy giá (Limit):**\n"
            "`/limit ETHUSDT SHORT 2500 2480 2300/2600 [RISK]` \n"
            "➜ Khi giá chạm 2500, kích hoạt lệnh Short 2480 với Risk [RISK] USDT.\n\n"
            "📊 **Tiện ích:**\n"
            "`/status` - Xem số dư & chế độ sàn\n"
            "`/orders` - Xem các lệnh đang chờ\n"
            "`/help` - Hiện hướng dẫn này"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    else:
        await update.message.reply_text(
            "⚠️ Cú pháp không xác định!\n"
            "Hệ thống khuyên dùng: `/scan BNBUSDC` để xem AI phân tích.\n"
            "Gõ `/help` để xem tất cả cú pháp lệnh."
        )

async def start_telegram_bot():
    """Khởi động Polling Telegram"""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Thiếu TELEGRAM_BOT_TOKEN trong file .env!")
        return

    from telegram.request import HTTPXRequest
    # Tăng timeout để tránh lỗi TimedOut khi mạng lag hoặc xử lý chậm
    t_request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).request(t_request).build()
    
    # Lắng nghe mọi text message, kể cả có dấu / hay không (Giúp nhận diện symbol không cần dấu /)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("🤖 Telegram Bot đã sẵn sàng nhận lệnh...")
    
    # Chạy Polling (phân rã drop_pending_updates để đảm bảo khởi động chuẩn)
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

