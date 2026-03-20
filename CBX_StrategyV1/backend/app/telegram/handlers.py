import os
import logging
import re
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import google.generativeai as genai
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.telegram.auth import require_auth, require_admin
from app.telegram.keyboards import get_status_keyboard, get_signal_keyboard
from app.database import AsyncSessionLocal
from app.api.dependencies import get_redis
from app.models.trade import Trade
from app.models.events import BreakoutEvent
from app.models.symbol import SymbolRegistry

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

@require_auth
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    user = update.effective_user
    welcome_text = (
        f"👋 Chào mừng *{user.first_name}* đến với *CBX Trading Bot*!\n\n"
        "Em là trợ lý giao dịch của anh. Dưới đây là các lệnh anh có thể dùng:\n"
        "📊 /status - Xem trạng thái bot hiện tại\n"
        "📈 /signals - Xem các tín hiệu gần đây\n"
        "📉 /trades - Xem các lệnh đang mở\n"
        "🤖 /ask <câu hỏi> - Hỏi AI về thị trường\n\n"
        "💡 *Giao dịch thủ công (Admin):*\n"
        "buy/sell <SYMBOL> <SIZE%> <SL> <TP>\n"
        "Ví dụ: `/buy BTC 1.0 95000 98500`"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

@require_auth
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /status command."""
    redis = await get_redis()
    
    # 1. Fetch info from Redis
    mode = (await redis.get("bot:mode") or b"MANUAL").decode()
    regime = (await redis.get("bot:regime") or b"NORMAL").decode()
    session_state_raw = await redis.get("bot:session_state")
    
    equity = 0.0
    daily_pnl = 0.0
    daily_pnl_r = 0.0
    
    if session_state_raw:
        import json
        try:
            state = json.loads(session_state_raw)
            equity = state.get("equity", 0.0)
            daily_pnl = state.get("daily_pnl_usd", 0.0)
            daily_pnl_r = state.get("daily_pnl_r", 0.0)
        except:
            pass

    # 2. Fetch Open Positions count from DB
    open_count = 0
    async with AsyncSessionLocal() as db:
        query = select(func.count()).select_from(Trade).where(Trade.status == "OPEN")
        open_count = await db.scalar(query) or 0

    status_text = (
        "🤖 *CBX Bot Status*\n"
        "━━━━━━━━━━━━━━━\n"
        f"💰 Equity:    `${equity:,.2f}`\n"
        f"📈 Daily PnL: `{daily_pnl_r:+.1f}R` (`${daily_pnl:+.2f}`)\n"
        f"📊 Positions: `{open_count}` open\n"
        f"⚙️ Mode:      `{mode}`\n"
        f"🌡️ Regime:    `{regime}`"
    )
    
    await update.message.reply_text(
        status_text, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_status_keyboard()
    )

@require_auth
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /buy SYMBOL SIZE_PCT [SL] [TP]."""
    await _handle_manual_order(update, context, "LONG")

@require_auth
async def sell_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /sell SYMBOL SIZE_PCT [SL] [TP]."""
    await _handle_manual_order(update, context, "SHORT")

async def _handle_manual_order(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str):
    # Parse arguments
    text = update.message.text
    try:
        parsed = _parse_trade_command(text)
        symbol = parsed["symbol"]
        size_pct = parsed["size_pct"]
        sl = parsed["sl"]
        tp = parsed["tp"]
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {str(e)}")
        return
    except Exception:
        await update.message.reply_text("⚠️ Sai cú pháp. VD: `/buy BTC 1.0 [SL] [TP]`")
        return

    # Implementation of order execution would go here
    # For now, we mock the success
    emoji = "📈" if side == "LONG" else "📉"
    msg = (
        f"✅ *Lệnh {side} đã được ghi nhận*\n"
        f"Symbol: `{symbol}` {emoji}\n"
        f"Size:   `{size_pct}%` của Equity\n"
        f"SL:     `{sl or 'Auto'}`\n"
        f"TP:     `{tp or 'Auto'}`\n\n"
        "⚡ Đang gửi tới sàn..."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    # TODO: Call order_executor service

@require_auth
async def close_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /close SYMBOL."""
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Vui lòng nhập symbol. VD: `/close BTC`")
        return

    symbol_raw = args[0].upper()
    symbol = symbol_raw if "USDC" in symbol_raw else f"{symbol_raw}USDC"

    async with AsyncSessionLocal() as db:
        # Find the open trade for this symbol
        # Join with SymbolRegistry to find by symbol string
        query = (
            select(Trade)
            .join(SymbolRegistry)
            .where(SymbolRegistry.symbol == symbol)
            .where(Trade.status == "OPEN")
        )
        result = await db.execute(query)
        trade = result.scalars().first()
        
        if not trade:
            await update.message.reply_text(f"❌ Không tìm thấy lệnh đang mở cho `{symbol}`")
            return

        # Mock closing
        trade.status = "CLOSED"
        trade.exit_time = datetime.utcnow()
        await db.commit()
        
        await update.message.reply_text(
            f"✅ Đã đóng lệnh `{symbol}`\n"
            f"PnL: `+0.5R` (MOCK)", # In reality calculate from real PnL
            parse_mode=ParseMode.MARKDOWN
        )

@require_auth
async def ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /ask AI."""
    if not ai_model:
        await update.message.reply_text("❌ AI chưa được cấu hình (Thiếu GEMINI_API_KEY)")
        return

    prompt_text = " ".join(context.args)
    if not prompt_text:
        await update.message.reply_text("💬 Anh muốn hỏi gì về thị trường?")
        return

    # Gather context
    async with AsyncSessionLocal() as db:
        # 1. Recent signals
        signals_q = select(BreakoutEvent).order_by(desc(BreakoutEvent.time)).limit(3)
        signals = (await db.execute(signals_q)).scalars().all()
        
        # 2. Open positions
        pos_q = select(Trade).where(Trade.status == "OPEN").limit(5)
        positions = (await db.execute(pos_q)).scalars().all()

    # Build context string
    ctx = f"Context hệ thống:\n"
    ctx += f"Các tín hiệu gần đây: {[{'side': s.side, 'price': float(s.price)} for s in signals]}\n"
    ctx += f"Các vị thế đang mở: {[{'side': p.side, 'entry': float(p.entry_price)} for p in positions]}\n"
    ctx += f"Câu hỏi của người dùng: {prompt_text}\n\n"
    ctx += "Hãy trả lời bằng tiếng Việt, ngắn gọn, súc tích và có tính chuyên gia về trading."

    typing_task = asyncio.create_task(context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing"))
    
    try:
        response = await ai_model.generate_content_async(ctx)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        await update.message.reply_text("😅 Xin lỗi, AI đang bận. Anh thử lại sau nhé.")
    finally:
        typing_task.cancel()

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    data = query.data
    
    await query.answer()

    if data.startswith("place_order:"):
        signal_id = data.split(":")[1]
        await query.edit_message_text(text=f"✅ Đã xác nhận! Đang thực hiện đặt lệnh cho signal `{signal_id}`...")
        # TODO: Implement actual execution logic
    
    elif data.startswith("dismiss:"):
        await query.edit_message_text(text="❌ Đã bỏ qua signal này.")
    
    elif data == "refresh_status":
        # Simply re-call status handler logic or similar
        await status_handler(update, context)

def _parse_trade_command(text: str) -> Dict[str, Any]:
    """
    Parse /buy or /sell command text.
    Format: /command SYMBOL SIZE_PCT [SL] [TP]
    """
    parts = text.split()
    if len(parts) < 3:
        raise ValueError("Thiếu tham số. VD: `/buy BTC 1.0`")
    
    symbol_raw = parts[1].upper()
    symbol = symbol_raw if "USDC" in symbol_raw else f"{symbol_raw}USDC"
    
    try:
        size_pct = float(parts[2])
    except ValueError:
        raise ValueError("Size% không hợp lệ.")

    if not (0.1 <= size_pct <= 5.0):
        raise ValueError("Size% phải từ 0.1 đến 5.0")

    sl = Decimal(parts[3]) if len(parts) > 3 else None
    tp = Decimal(parts[4]) if len(parts) > 4 else None
    
    return {
        "symbol": symbol,
        "size_pct": size_pct,
        "sl": sl,
        "tp": tp
    }
