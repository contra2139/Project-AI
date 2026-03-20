Tạo production deployment configuration cho CBX Bot.

━━━ FILE 1: nginx/nginx.conf ━━━

Reverse proxy configuration:
  HTTP (port 80)  → redirect toàn bộ về HTTPS
  HTTPS (port 443) → serve application

Routing:
  /           → frontend:3000 (Next.js)
  /api/       → backend:8000 (FastAPI)
  /ws         → backend:8000 (WebSocket upgrade)
  /tg/        → backend:8000 (Telegram webhook)
  /docs       → backend:8000 (Swagger, chỉ dev)

WebSocket proxy headers (bắt buộc):
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";

SSL configuration:
  ssl_certificate     /etc/letsencrypt/live/domain/fullchain.pem
  ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem
  ssl_protocols TLSv1.2 TLSv1.3;

Rate limiting:
  limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
  limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
  /api/v1/auth/login → zone=login
  /api/             → zone=api

Security headers:
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: strict-origin-when-cross-origin

Gzip compression:
  gzip on cho text/html, application/json, text/css, application/javascript

━━━ FILE 2: docker-compose.yml (production) ━━━

Services:

postgres:
  image: postgres:15-alpine
  restart: always
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: pg_isready -U ${DB_USER} -d ${DB_NAME}
    interval: 10s
    retries: 5
  environment: từ .env

redis:
  image: redis:7-alpine
  restart: always
  command: redis-server --requirepass ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
  healthcheck:
    test: redis-cli ping
    interval: 10s
    retries: 3

backend:
  build: ./backend
  restart: always
  depends_on:
    postgres: { condition: service_healthy }
    redis:    { condition: service_healthy }
  environment: từ .env
  healthcheck:
    test: curl -f http://localhost:8000/health
    interval: 30s
    retries: 3

frontend:
  build: ./frontend
  restart: always
  depends_on:
    - backend
  environment:
    NEXT_PUBLIC_API_URL: https://${DOMAIN}/api
    NEXT_PUBLIC_WS_URL: wss://${DOMAIN}

nginx:
  image: nginx:alpine
  restart: always
  ports:
    - "80:80"
    - "443:443"
  depends_on:
    - frontend
    - backend
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/ssl:/etc/letsencrypt:ro
    - nginx_logs:/var/log/nginx

volumes:
  postgres_data:
  redis_data:
  nginx_logs:

━━━ FILE 3: backend/app/main.py (startup hoàn chỉnh) ━━━

Startup sequence đúng thứ tự:
  1. Validate tất cả Settings — fail fast nếu thiếu
  2. Test database connection
  3. Test Redis connection
  4. Run Alembic migrations (chỉ dev mode)
  5. Test Binance connection + clock sync
  6. Load active symbols từ DB
  7. Position reconciliation:
     So sánh open trades trong DB vs Binance API
     Nếu discrepancy → log CRITICAL + không trade
  8. Setup Telegram webhook
  9. Start APScheduler jobs:
     - price_broadcast: mỗi 5 giây
     - daily_summary: 23:00 UTC
     - binance_clock_sync: mỗi 60 giây
  10. Start CBXScanner
  11. Log "CBX Bot ready. Mode: {mode}. Symbols: {list}"

━━━ FILE 4: backend/Dockerfile (production) ━━━

Multi-stage build:
  Stage 1 (builder):
    python:3.11-slim
    Copy requirements.txt
    pip install --no-cache-dir

  Stage 2 (runtime):
    python:3.11-slim
    Copy từ builder: /usr/local/lib/python/site-packages
    Copy app code
    Non-root user: useradd -m appuser
    EXPOSE 8000
    CMD uvicorn app.main:app --host 0.0.0.0 --port 8000

━━━ FILE 5: frontend/Dockerfile (production) ━━━

Multi-stage build:
  Stage 1 (deps):
    node:20-alpine
    npm ci --only=production

  Stage 2 (builder):
    node:20-alpine
    Copy deps
    npm run build

  Stage 3 (runner):
    node:20-alpine
    Non-root user: nextjs
    COPY --from=builder --chown=nextjs:nodejs .next/standalone
    COPY --from=builder --chown=nextjs:nodejs .next/static
    EXPOSE 3000
    CMD node server.js

  next.config.ts phải có: output: 'standalone'

━━━ FILE 6: scripts/setup.sh ━━━

Script setup lần đầu:
  #!/bin/bash
  set -e

  # Check .env tồn tại
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from example. Please fill in values."
    exit 1
  fi

  # Generate secrets nếu chưa có
  if grep -q "your-secret-key" .env; then
    APP_SECRET=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 64)
    sed -i "s/your-secret-key-min-32-chars/$APP_SECRET/" .env
    sed -i "s/your-jwt-secret-key-min-64-chars/$JWT_SECRET/" .env
    echo "Generated APP_SECRET_KEY and JWT_SECRET_KEY"
  fi

  # Validate required vars
  required_vars=(BINANCE_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_ADMIN_USER_ID)
  for var in "${required_vars[@]}"; do
    if grep -q "your-$var" .env 2>/dev/null; then
      echo "ERROR: Please set $var in .env"
      exit 1
    fi
  done

  echo "Setup complete. Run: docker-compose up -d"

━━━ FILE 7: GET /health endpoint hoàn chỉnh ━━━

Response format:
{
  "status": "ok" | "degraded" | "error",
  "timestamp": "ISO8601",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "services": {
    "database": {
      "status": "ok" | "error",
      "latency_ms": 5
    },
    "redis": {
      "status": "ok" | "error",
      "latency_ms": 1
    },
    "binance": {
      "status": "ok" | "error",
      "latency_ms": 120,
      "testnet": false
    },
    "telegram": {
      "status": "ok" | "error",
      "webhook_active": true
    },
    "scanner": {
      "status": "running" | "stopped" | "error",
      "last_scan": "ISO8601",
      "symbols_active": 3
    }
  }
}

Overall status:
  "ok" nếu tất cả services ok
  "degraded" nếu binance hoặc telegram lỗi
  "error" nếu database hoặc redis lỗi

━━━ VERIFICATION ━━━

Sau khi tạo xong tất cả files:

1. docker-compose -f docker-compose.yml build
   → Tất cả images build thành công

2. docker-compose up -d
   → 5 containers up (postgres, redis, backend, frontend, nginx)

3. curl http://localhost/health
   → Response JSON đúng format

4. curl http://localhost/api/v1/auth/login
   → 200 hoặc 422 (không phải 502 Bad Gateway)

5. Mở http://localhost
   → Redirect https (nếu có SSL)
   → Hoặc login page nếu local

Paste kết quả 5 lệnh curl vào chat để confirm.