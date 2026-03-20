# 🚀 CBX TRADING BOT

Bot giao dịch Crypto Futures dựa trên chiến lược **Compression-Breakout-Expansion (CBX)**.

## 🛠️ Stack Công Nghệ
- **Backend:** Python 3.11 + FastAPI (Secured & Audited)
- **Frontend:** Next.js 14 + TailwindCSS + Recharts
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Container:** Docker & Docker Compose (Python 3.11-slim)

## 📚 Documentation
- [User Guide V7](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/docs/user_guide_v7.md) - Comprehensive instructions for Strategy V7.
- [API Documentation](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/docs/api/endpoints.md) - Endpoint details and security requirements.
- [Backtest Summary V7](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/backtest_results_v7/walkforward_v7_revised.txt) - Detailed 2024-2026 performance results.

## 🚀 Getting Started
1. **Setup Environment**: Copy `.env.example` to `.env` and fill in secrets (JWT secret must be 32+ chars).
2. **Installation**: `pip install -r backend/requirements.txt`
3. **Database**: Migration is automated via `run_comprehensive_backtest.py`.
4. **Run Bot**: `uvicorn backend.app.main:app --reload`

## ⚙️ Hướng dẫn Setup

### 1. Cấu hình Môi trường
Copy file mẫu và điền thông tin:
```bash
cp .env.example .env
```
*Lưu ý: Bạn cần điền Binance API Key và Postgres Password.*

### 2. Chạy ứng dụng (Development)
Sử dụng hot-reload cho cả backend và frontend:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### 3. Ports
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Database:** localhost:5432
- **Redis:** localhost:6379

## 📂 Cấu trúc dự án
- `/backend`: Mã nguồn xử lý logic trading, API, và Database.
- `/frontend`: Giao diện người dùng Dashboard.
- `/docs`: Tài liệu thiết kế và đặc tả chiến lược.

---
*Created by Antigravity Workflow Framework*
