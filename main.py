from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import logging

from config import config
from core.logger_setup import setup_global_logging

# Thiết lập hệ thống log gốc
setup_global_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Crypto Quant AI Bot")

# Thư mục chứa giao diện Web
import os
os.makedirs("web/static", exist_ok=True)
os.makedirs("web/templates", exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
except RuntimeError:
    logger.warning("Thư mục web/static chưa sẵn sàng.")

from core.telegram_ctrl import start_telegram_bot

@app.on_event("startup")
async def startup_event():
    logger.info("⚡ Khởi động hệ thống FastAPI + Telegram Bot...")
    config.validate()
    # Khởi động Telegram Polling Background Task
    asyncio.create_task(start_telegram_bot())
    
@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("web/templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Dashboard đang được xây dựng...</h1>"

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
