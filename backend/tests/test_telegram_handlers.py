import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Import the handlers and parsing logic
from app.telegram.handlers import start_handler, _parse_trade_command
from app.api.websocket import ConnectionManager

@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 123456789
    update.message.text = "/start"
    update.message.reply_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    return context

# Test 1: Unauthorized user — stealth mode
@pytest.mark.asyncio
async def test_unauthorized_user_stealth_mode(mock_context):
    update = MagicMock()
    update.effective_user.id = 111222333 # Unauthorized
    update.message.reply_text = AsyncMock()
    
    with patch("app.telegram.auth.ALLOWED_IDS", {987654321}):
        await start_handler(update, mock_context)
    
    # Assert: context.bot.send_message KHÔNG được gọi lần nào
    update.message.reply_text.assert_not_called()
    mock_context.bot.send_message.assert_not_called()

# Test 2: Authorized user — handler chạy
@pytest.mark.asyncio
async def test_authorized_user_handler_runs(mock_update, mock_context):
    with patch("app.telegram.auth.ALLOWED_IDS", {123456789, 987654321}):
        await start_handler(mock_update, mock_context)
    
    # Assert: update.message.reply_text được gọi ít nhất 1 lần
    mock_update.message.reply_text.assert_called()

# Test 3: /buy parse đủ tham số
def test_buy_parse_full_args():
    text = "/buy BTC 1.0 95000 98500"
    parsed = _parse_trade_command(text)
    
    assert parsed["symbol"] == "BTCUSDC"
    assert parsed["size_pct"] == 1.0
    assert parsed["sl"] == Decimal("95000")
    assert parsed["tp"] == Decimal("98500")

# Test 4: /buy parse thiếu SL/TP
def test_buy_parse_missing_sl_tp():
    text = "/buy BTC 0.5"
    parsed = _parse_trade_command(text)
    
    assert parsed["symbol"] == "BTCUSDC"
    assert parsed["size_pct"] == 0.5
    assert parsed["sl"] is None
    assert parsed["tp"] is None
    # No exception should be raised

# Test 5: WebSocket broadcast format
@pytest.mark.asyncio
async def test_websocket_broadcast_format():
    manager = ConnectionManager()
    
    # Mocking WebSocket
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    
    # Connect a fake client
    manager.active_connections["client_1"] = websocket
    
    payload = {"symbol": "BTCUSDC"}
    await manager.broadcast({
        "type": "signal_detected",
        "data": payload,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Capture the argument passed to send_json
    # broadcast calls send_json for each connection
    args, kwargs = websocket.send_json.call_args
    message = args[0]
    
    assert message["type"] == "signal_detected"
    assert message["data"] == payload
    assert "timestamp" in message
    # Validate timestamp is ISO format
    try:
        datetime.fromisoformat(message["timestamp"])
    except ValueError:
        pytest.fail("Timestamp is not in ISO format")
