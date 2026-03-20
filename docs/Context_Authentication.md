CBX Trading Bot — Python FastAPI, PostgreSQL, Redis.

Giai đoạn 2 và 3 hoàn thành. Toàn bộ strategy + backtest
engine hoạt động và đã verified 78 unit tests.

Settings (từ .env) có:
  ADMIN_USERNAME: str
  ADMIN_PASSWORD_HASH: str  (bcrypt hashed)
  JWT_SECRET_KEY: str
  JWT_ALGORITHM: str        (default "HS256")
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int   (default 60)
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: int     (default 30)
  REDIS_URL: str

Yêu cầu bắt buộc:
1. Async/await cho DB và Redis
2. Không hardcode — đọc từ Settings
3. Log structured JSON
4. httpOnly cookie cho refresh token (không localStorage)