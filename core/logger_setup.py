import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_global_logging():
    """Thiết lập cấu hình Logging gốc cho toàn hệ thống."""
    # Tạo thư mục logs nếu chưa có
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Format chung: [YYYY-MM-DD HH:MM:SS] - [Tên module] - [LEVEL] - Message
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. Console Handler (In ra màn hình cho dễ theo dõi)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING) # Chỉ in WARN/ERR, giấu đi các INFO không cần thiết
    console_handler.setFormatter(formatter)
    
    # 2. File Handler - INFO (Lưu trữ lịch sử)
    # Xoay vòng mỗi ngày (midnight), lưu 30 ngày.
    info_log_path = os.path.join(logs_dir, "app_info.log")
    info_file_handler = TimedRotatingFileHandler(
        filename=info_log_path,
        when="midnight", 
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(formatter)
    
    # 3. File Handler - ERROR (Chỉ ghi các lỗi hệ thống để debug)
    error_log_path = os.path.join(logs_dir, "app_error.log")
    error_file_handler = TimedRotatingFileHandler(
        filename=error_log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    
    # Gắn handler vào Root Logger
    root_logger = logging.getLogger()
    
    # Chặn chạy add lại Handler nếu gõ command liên tục (tránh duplicate log line trong FastAPI reload)
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(info_file_handler)
        root_logger.addHandler(error_file_handler)
        
    # Tắt tiếng những thư viện spam log ngầm đi
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
