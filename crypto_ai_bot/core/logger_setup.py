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
    
    # 合 nhất log vào file theo ngày: YYYY-MM-DD.log
    import datetime
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    log_filename = os.path.join(logs_dir, f"{current_date}.log")
    
    # Handler xoay vòng mỗi ngày, giữ tối đa 5 ngày
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when="midnight",
        interval=1,
        backupCount=5,
        encoding="utf-8"
    )
    
    # Custom namer để đổi tên file cũ đúng định dạng YYYY-MM-DD.log
    def namer(default_name):
        # default_name thường là path/to/log.YYYY-MM-DD
        # Ta muốn nó là path/to/YYYY-MM-DD.log
        base_dir = os.path.dirname(default_name)
        timestamp = default_name.split(".")[-1]
        return os.path.join(base_dir, f"{timestamp}.log")
    
    file_handler.namer = namer
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Gắn handler vào Root Logger
    root_logger = logging.getLogger()
    
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
    # Tắt tiếng những thư viện spam log ngầm đi
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
