import os
import uvicorn
import asyncio
import logging
import json
import webbrowser

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import APIKeyHeader

from config import config
from core.logger_setup import setup_global_logging
from core.telegram_ctrl import start_telegram_bot, stop_telegram_bot
from core.data_ingestion import fetch_klines
from core.binance_exec import get_open_orders, get_open_positions, execute_trade
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
    
    # Tự động mở trình duyệt sau 1.5s (khi server đã sẵn sàng)
    async def open_browser():
        await asyncio.sleep(1.5)
        url = "http://127.0.0.1:8000"
        logger.info(f"🌐 Đang mở Dashboard: {url}...")
        try:
            # Ưu tiên Chrome trên Windows
            chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
            # Thử đăng ký chrome nếu tìm thấy path chuẩn
            if os.path.exists("C:/Program Files/Google/Chrome/Application/chrome.exe"):
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser("C:/Program Files/Google/Chrome/Application/chrome.exe"))
                webbrowser.get('chrome').open(url, new=0)
            else:
                webbrowser.open(url, new=0)
        except Exception as e:
            logger.warning(f"Không thể tự động mở trình duyệt: {e}")

    asyncio.create_task(open_browser())
    yield
    logger.info("🛑 Đang tắt hệ thống...")
    
    # 1. Dừng Telegram Bot trước
    await stop_telegram_bot()
    
    # 2. Đóng kết nối Binance
    await BinanceClientManager.close()
    
    # 3. Chờ thêm 0.5s để tất cả các sockets/connectors ngầm kịp đóng hẳn (Tránh lỗi Unclosed Connector trên Windows)
    await asyncio.sleep(0.5)
    logger.info("✨ Hệ thống đã dọn dẹp xong. Tạm biệt!")

app = FastAPI(title="Crypto Quant AI Bot", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "web", "static")), name="static")


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
        import datetime
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(BASE_DIR, "logs", f"{current_date}.log")
        
        if not os.path.exists(log_path):
            return {"logs": [f"[System] Log file hôm nay chưa có: {current_date}.log"]}

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

@app.get("/api/positions", response_class=JSONResponse)
async def get_positions_api():
    """Lấy danh sách vị thế đang mở và PnL"""
    try:
        positions = await get_open_positions()
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Lỗi API lấy vị thế: {e}")
        return {"positions": []}

@app.post("/api/close_position")
async def close_position_api(symbol: str, pin: str = Depends(verify_api_key)):
    """Đóng nhanh một vị thế cụ thể"""
    try:
        # Lấy thông tin vị thế trước
        positions = await get_open_positions()
        pos = next((p for p in positions if p['symbol'] == symbol), None)
        
        if not pos:
            raise HTTPException(status_code=404, detail="Không tìm thấy vị thế đang mở cho mã này")
            
        # Thực hiện lệnh ngược lại với giá Market để đóng vị thế
        action = "SHORT" if pos['side'] == "LONG" else "LONG"
        # Dùng execute_trade với các tham số ảo cho Entry/TP/SL vì ta sẽ đóng Market
        # Tuy nhiên execute_trade hiện tại đang đặt lệnh LIMIT. 
        # Cần một hàm close_market hoặc sửa execute_trade. 
        # Để an toàn, em sẽ dùng trực tiếp client trong binance_exec hoặc tạo helper mới.
        
        # Tạm thời dùng execute_trade với giá 0 (Market logic thường xử lý giá 0 là Market trong một số SDK, 
        # nhưng ở đây ta cần đóng thật sự). 
        # Để cho chuyên nghiệp, em sẽ thêm hàm close_all_positions_for_symbol vào binance_exec.
        
        from core.binance_exec import setup_margin_and_leverage
        client = await BinanceClientManager.get_client()
        side = SIDE_SELL if pos['side'] == "LONG" else SIDE_BUY
        
        await client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=abs(pos['positionAmt']),
            reduceOnly='true'
        )
        
        logger.info(f"🚀 Dashboard: Đã đóng vị thế {symbol} bằng lệnh MARKET.")
        return {"status": "success", "message": f"Đã đóng vị thế {symbol}"}
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
