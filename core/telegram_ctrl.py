import re

# ==========================================
# REGEX PATTERNS CỦA 3 LUỒNG LỆNH
# ==========================================

# 1. TICKER PATTERN: Nhận diện mã token (VD: BNBUSDC, BTCUSDT) - Dùng để Tư Vấn
# Format: Chỉ gồm các chữ cái hoa/thường, có thể có chữ số (tên coin dài)
TICKER_PATTERN = re.compile(r"^[A-Za-z0-9]+$")

# 2. IMMEDIATE PATTERN: Lệnh khớp trực tiếp Market/Limit
# Format: Long/Short price {price} TP/SL {tp}/{sl}
# VD: "Long price 500 TP/SL 550/450" hoặc "Short price 500 tp/sl 450/550"
IMMEDIATE_PATTERN = re.compile(
    r"^(?P<action>long|short)\s+price\s+(?P<price>[\d\.]+)\s+tp/sl\s+(?P<tp>[\d\.]+)/(?P<sl>[\d\.]+)$", 
    re.IGNORECASE
)

# 3. CONDITIONAL PATTERN: Lệnh chờ kích hoạt theo giá (Stop-Loss Limit tự động của Binance)
# Format: if {condition_price} Long/Short price {price} TP/SL {tp}/{sl}
# VD: "if 480 Long price 490 TP/SL 550/450"
CONDITIONAL_PATTERN = re.compile(
    r"^if\s+(?P<condition_price>[\d\.]+)\s+(?P<action>long|short)\s+price\s+(?P<price>[\d\.]+)\s+tp/sl\s+(?P<tp>[\d\.]+)/(?P<sl>[\d\.]+)$", 
    re.IGNORECASE
)

def parse_user_message(message: str) -> dict:
    """
    Phân tích cú pháp tin nhắn Telegram. Trả về Dictionary hành động.
    """
    msg = message.strip()
    
    # Kịch bản 3: Lệnh Điều Kiện (Conditional)
    match_cond = CONDITIONAL_PATTERN.match(msg)
    if match_cond:
        return {
            "type": "conditional_order",
            "condition_price": float(match_cond.group("condition_price")),
            "action": match_cond.group("action").upper(),
            "price": float(match_cond.group("price")),
            "tp": float(match_cond.group("tp")),
            "sl": float(match_cond.group("sl"))
        }

    # Kịch bản 2: Lệnh Tức Thì (Immediate)
    match_imm = IMMEDIATE_PATTERN.match(msg)
    if match_imm:
        return {
            "type": "immediate_order",
            "action": match_imm.group("action").upper(),
            "price": float(match_imm.group("price")),
            "tp": float(match_imm.group("tp")),
            "sl": float(match_imm.group("sl"))
        }

    # Kịch bản 1: Tư Vấn Giao Dịch (Ticker)
    match_ticker = TICKER_PATTERN.match(msg)
    if match_ticker:
        return {
            "type": "analyze",
            "symbol": msg.upper()
        }

    # Trường hợp không khớp Format nào
    return {"type": "unknown", "raw_message": msg}

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import config
from core.data_ingestion import get_multi_timeframe_data
from core.ta_calculator import calculate_ta
from core.ai_brain import generate_trading_decision
from core.binance_exec import execute_trade, execute_conditional_order
import logging

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback khi nhận được tin nhắn từ User."""
    chat_id = str(update.message.chat_id)
    text = update.message.text

    # BẢO MẬT: Chỉ nhận lệnh từ Chat ID định trước
    if chat_id != config.TELEGRAM_CHAT_ID:
        logger.warning(f"Từ chối lệnh từ Chat ID lạ: {chat_id}")
        return

    # Phân tích cú pháp tin nhắn
    action = parse_user_message(text)
    
    if action["type"] == "analyze":
        symbol = action["symbol"]
        await update.message.reply_text(f"🔍 Đang thu thập dữ liệu và phân tích đa khung thời gian cho {symbol}...")
        
        try:
            # 1. Kéo mảng Data OHLCV
            raw_data = await get_multi_timeframe_data(symbol, limit=250)
            
            # 2. Xử lý TA (Lạm dụng vòng lặp trên mảng dictionary)
            clean_data = {}
            for tf, df in raw_data.items():
                if not df.empty:
                    clean_data[tf] = calculate_ta(df)
            
            # 3. Yêu cầu AI Decision
            if clean_data:
                ai_result = await generate_trading_decision(symbol, clean_data)
                
                # Trích xuất và in dữ liệu
                decision = ai_result.get("decision", "UNKNOWN")
                reasoning = ai_result.get("reasoning", "Không có giải thích từ AI.")
                entry = ai_result.get("entry", "N/A")
                sl = ai_result.get("stop_loss", "N/A")
                tp = ai_result.get("take_profit", "N/A")
                
                msg_reply = f"🤖 **AI TRADING BRAIN** 🤖\n\n"
                msg_reply += f"Tín hiệu: {decision}\n\n"
                msg_reply += f"💡 Lý do: {reasoning}\n\n"
                
                if decision in ["LONG", "SHORT"]:
                    msg_reply += f"🎯 Entry: {entry}\n"
                    msg_reply += f"🛡️ Stop-Loss (Động ATR): {sl}\n"
                    msg_reply += f"💰 Take-Profit: {tp}"
                    
                await update.message.reply_text(msg_reply, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Không tải được dữ liệu chuẩn cho mã {symbol}.")
                
        except Exception as e:
            logger.error(f"Lỗi AI Pipeline: {e}")
            await update.message.reply_text(f"⚠️ Đã có lỗi xảy ra trong quá trình AI phân tích. Kiểm tra log Hệ thống.")
        
    elif action["type"] == "immediate_order":
        await update.message.reply_text(f"⏳ Đang xử lý lệnh tức thì {action['action']} tại {action['price']}...")
        result = await execute_trade(
            symbol="BTCUSDT", # Tạm hardcode hoặc cần bắt user nhập Ticker chung lệnh
            action=action['action'],
            price=action['price'],
            sl=action['sl'],
            tp=action['tp']
        )
        if result["status"] == "success":
            await update.message.reply_text(f"✅ KHỚP LỆNH THÀNH CÔNG!\nID: `{result['order']['orderId']}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ LỖI VÀO LỆNH: {result['message']}")
            
    elif action["type"] == "conditional_order":
        await update.message.reply_text(f"⏳ Đang thiết lập bẫy giá {action['condition_price']}...")
        result = await execute_conditional_order(
            symbol="BTCUSDT",
            action=action['action'],
            trigger_price=action['condition_price'],
            entry_price=action['price'],
            sl=action['sl'],
            tp=action['tp']
        )
        if result["status"] == "success":
            await update.message.reply_text(f"✅ GÀI BẪY THÀNH CÔNG!\nKhi giá chạm {action['condition_price']} sẽ kích hoạt.\nID: `{result['order']['orderId']}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ LỖI CÀI BẪY: {result['message']}")
        
    else:
        await update.message.reply_text("❌ Cú pháp không hợp lệ. Vui lòng gửi:\n- Ticker (VD: BTCUSDT)\n- Lệnh: 'Long/Short price x TP/SL y/z'\n- Điều kiện: 'if w Long/Short price x TP/SL y/z'")

async def start_telegram_bot():
    """Khởi động Polling Telegram"""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Thiếu TELEGRAM_BOT_TOKEN trong file .env!")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Lắng nghe mọi text message chưa filter lệnh /
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Telegram Bot đã sẵn sàng nhận lệnh...")
    
    # Chạy Polling (phân rã drop_pending_updates để đảm bảo khởi động chuẩn)
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

