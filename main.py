import os
import uvicorn
import asyncio
import logging
import json

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import APIKeyHeader

from config import config
from core.logger_setup import setup_global_logging
from core.telegram_ctrl import start_telegram_bot
from core.data_ingestion import fetch_klines
from core.binance_exec import get_open_orders
from core.binance_client import BinanceClientManager

# ── Absolute base path ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Khởi động logger tại module level (bắt buộc)
setup_global_logging()
os.makedirs(os.path.join(BASE_DIR, "web", "static"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "web", "templates"), exist_ok=True)
logger = logging.getLogger(__name__)

# Security: Simple API Key for Dashboard
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != config.SHUTDOWN_PIN: 
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    return api_key

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Thay thế on_event - Chuẩn FastAPI mới nhất"""
    logger.info("⚡ Khởi động hệ thống FastAPI + Telegram Bot...")
    config.validate()
    asyncio.create_task(start_telegram_bot())
    yield
    logger.info("🛑 Đang tắt hệ thống...")
    await BinanceClientManager.close()

app = FastAPI(title="Crypto Quant AI Bot", lifespan=lifespan)


@app.get("/", response_class=FileResponse)
async def read_root():
    try:
        file_path = os.path.join(BASE_DIR, "web", "templates", "monitor.html")
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return HTMLResponse("<h1>Dashboard (monitor.html) không tìm thấy.</h1>")
    except Exception as e:
        logger.error(f"Lỗi load giao diện: {e}")
        return HTMLResponse(f"<h1>Lỗi: {e}</h1>")

@app.get("/api/chart/{symbol}")
async def get_chart_data(symbol: str, interval: str = "1h", limit: int = 150):
    """Trích xuất dữ liệu OHLCV trực tiếp từ Binance dùng để render Graphic Chart"""
    try:
        df = await fetch_klines(symbol=symbol, interval=interval, limit=limit)
        if df is None or df.empty:
            return JSONResponse(content=[])

        chart_data = []
        for index, row in df.iterrows():
            # Chuyển đổi pandas DateTimeIndex thành UNIX timestamp seconds
            chart_data.append({
                "time": int(index.timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low":  float(row["low"]),
                "close": float(row["close"])
            })
        return JSONResponse(content=chart_data)
    except Exception as e:
        logger.error(f"Lỗi khi kéo chart {symbol}: {e}")
        return JSONResponse(content=[])

@app.get("/api/logs", response_class=JSONResponse)
async def get_logs(lines: int = 50):
    """Lấy N dòng log cuối cùng từ app_info.log hiệu quả (không load cả file)"""
    try:
        log_path = os.path.join(BASE_DIR, "logs", "app_info.log")
        if not os.path.exists(log_path):
            return {"logs": [f"[System] Log file chưa có tại: {log_path}"]}

        # Đọc ngược N dòng cuối dùng seek (Tail implementation)
        def tail(f, n):
            assert n >= 0
            pos, lines = 0, []
            f.seek(0, os.SEEK_END)
            filesize = f.tell()
            while len(lines) <= n and pos < filesize:
                pos += 1024
                if pos > filesize: pos = filesize
                f.seek(filesize - pos, os.SEEK_SET)
                lines = f.readlines()
            return [line.strip() for line in lines[-n:] if line.strip()]

        with open(log_path, "rb") as f:
            recent_lines = tail(f, lines)
            recent_lines.reverse()
            # Decode bytes to string
            result = [line.decode('utf-8', errors='ignore') for line in recent_lines]
            return {"logs": result}
    except Exception as e:
        logger.error(f"Lỗi khi đọc file log: {e}")
        return {"logs": [f"[System Error] Không đọc được log: {e}"]}

@app.get("/api/ai_brain", response_class=JSONResponse)
async def get_ai_brain():
    """Lấy kết quả phân tích AI mới nhất"""
    try:
        data_path = os.path.join(BASE_DIR, "logs", "latest_ai.json")
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Lỗi đọc latest_ai.json: {e}")
        return {}

@app.get("/api/orders", response_class=JSONResponse)
async def get_orders():
    """Lấy danh sách lệnh chờ từ sàn"""
    try:
        orders = await get_open_orders()
        return {"orders": orders}
    except Exception as e:
        logger.error(f"Lỗi API lấy lệnh: {e}")
        return {"orders": []}

@app.post("/api/shutdown")
async def shutdown(api_key: str = Depends(verify_api_key)):
    """Tắt bot triệt để từ xa"""
    logger.info("🛑 Yêu cầu tắt bot từ Dashboard. Đang đóng kết nối và thoát...")
    
    # Đóng kết nối Binance
    await BinanceClientManager.close()
    
    # Thoát tiến trình ngay lập tức sau 1s để kịp trả về response
    def kill_self():
        import time
        import signal
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
    
    import threading
    threading.Thread(target=kill_self).start()
    
    return {"status": "success", "message": "Bot đang tắt..."}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="127.0.0.1",
        port=8000, 
        reload=False,
        workers=1
    )
