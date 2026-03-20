Tạo Authentication system và REST API endpoints cho CBX Bot.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 1: backend/app/utils/security.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Functions:

hash_password(password: str) -> str
  dùng bcrypt với rounds=12

verify_password(plain: str, hashed: str) -> bool
  bcrypt verify

create_access_token(data: dict, expires_delta: timedelta) -> str
  JWT encode với SECRET_KEY và ALGORITHM từ Settings
  payload: {sub, exp, iat, type="access"}

create_refresh_token(user_id: str) -> str
  JWT encode với expires = JWT_REFRESH_TOKEN_EXPIRE_DAYS
  payload: {sub, exp, type="refresh"}

decode_token(token: str) -> dict
  JWT decode, raise HTTPException 401 nếu:
  - expired
  - invalid signature
  - missing fields

store_refresh_token(token: str, user_id: str, redis) -> None
  Lưu vào Redis: key="refresh:{token_hash}", value=user_id
  TTL = JWT_REFRESH_TOKEN_EXPIRE_DAYS × 86400 seconds
  Lưu hash của token (không lưu token raw)

revoke_refresh_token(token: str, redis) -> None
  Xóa key "refresh:{token_hash}" khỏi Redis

verify_refresh_token(token: str, redis) -> Optional[str]
  Decode JWT → lấy user_id
  Kiểm tra key "refresh:{token_hash}" tồn tại trong Redis
  Return user_id nếu valid, None nếu không

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 2: backend/app/api/dependencies.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

get_current_user() → FastAPI Depends
  Đọc Authorization header: "Bearer <token>"
  Decode access token
  Kiểm tra type=="access"
  Return user_id (string)
  Raise HTTPException 401 nếu bất kỳ bước nào fail

Dùng dependency này ở TẤT CẢ route cần auth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 3: backend/app/api/v1/auth.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST /api/v1/auth/login
  Body: {username: str, password: str}
  Rate limit: 5 attempts/minute per IP (dùng Redis counter)
  Verify username == Settings.ADMIN_USERNAME
  Verify password với Settings.ADMIN_PASSWORD_HASH
  Tạo access_token và refresh_token
  Lưu refresh_token vào Redis
  Response:
  {
    success: true,
    data: {
      access_token: str,
      token_type: "bearer",
      expires_in: 3600
    }
  }
  Set refresh_token trong httpOnly cookie:
    name="refresh_token", httpOnly=True, secure=True,
    samesite="lax", max_age=30×86400

POST /api/v1/auth/refresh
  Đọc refresh_token từ cookie (không phải body)
  verify_refresh_token() với Redis
  Nếu valid → tạo access_token mới
  Response: {success: true, data: {access_token, expires_in}}

POST /api/v1/auth/logout
  Đọc refresh_token từ cookie
  revoke_refresh_token() xóa khỏi Redis
  Xóa cookie
  Response: {success: true, message: "Logged out"}

GET /api/v1/auth/me
  Requires: get_current_user()
  Response: {success: true, data: {user_id, username, role: "admin"}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 4: backend/app/api/v1/symbols.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tất cả routes require get_current_user()
Response format: {success, data, message, timestamp}

GET /api/v1/symbols
  Query params: is_active (bool), is_in_universe (bool)
  Return: List[SymbolRegistryRead]

POST /api/v1/symbols
  Body: SymbolRegistryCreate
  Insert SYMBOL_REGISTRY
  Trigger fetch_and_save_exchange_config() async
  Return: SymbolRegistryRead

GET /api/v1/symbols/{symbol_id}
  Return: SymbolRegistryRead + current SymbolStrategyConfig

PATCH /api/v1/symbols/{symbol_id}
  Body: {is_active: bool} hoặc {is_in_universe: bool}
  Return: SymbolRegistryRead updated

GET /api/v1/symbols/{symbol_id}/config
  Return: List[SymbolStrategyConfigRead] (lịch sử tất cả versions)

PUT /api/v1/symbols/{symbol_id}/config
  Body: SymbolStrategyConfigCreate
  Tạo version mới, set is_current=True cho version mới
  Set is_current=False cho version cũ
  Ghi STRATEGY_VERSION_HISTORY
  Return: SymbolStrategyConfigRead

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 5: backend/app/api/v1/settings.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET /api/v1/settings
  Return current bot settings từ Redis (mode, risk, notifications)

PATCH /api/v1/settings/mode
  Body: {mode: "auto" | "manual"}
  Validate mode value
  Lưu vào Redis key "bot:mode"
  Return: {mode, updated_at}

PATCH /api/v1/settings/risk
  Body: {risk_per_trade_pct, max_positions_portfolio, daily_stop_r}
  Validate: risk_per_trade_pct trong range 0.001 đến 0.05
  Lưu vào Redis key "bot:risk_settings"
  Return: updated settings

PATCH /api/v1/settings/notifications
  Body: {notify_on_signal, notify_on_entry, notify_on_exit, notify_daily_summary}
  Lưu vào Redis key "bot:notification_settings"
  Return: updated settings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 6: backend/app/api/v1/signals.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET /api/v1/signals
  Query params: symbol (str), side (LONG/SHORT), limit (default 20)
  Load từ Redis (active signals) + DB (historical)
  Merge, dedup, sort by time desc
  Return: List[SignalNotification]

GET /api/v1/signals/{signal_id}
  Return signal detail với full event chain:
    CompressionEvent → BreakoutEvent → ExpansionEvent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 7: backend/app/api/v1/trades.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET /api/v1/trades
  Query params: symbol, side, status, date_from, date_to, limit, offset
  Return: {trades: List[TradeRead], total: int, page_info}

GET /api/v1/trades/open
  Return: List[TradeRead] với status=OPEN
  Thêm unrealized_pnl_r (tính real-time từ giá hiện tại trong Redis)

GET /api/v1/trades/{trade_id}
  Return: TradeRead + List[ExitEventRead] + List[OrderLogRead]

POST /api/v1/trades/{trade_id}/close
  Force close một trade đang OPEN
  Gọi order_executor.place_market_order() để đóng
  Update trade.status = CLOSED
  Return: TradeRead updated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 8: backend/app/api/v1/risk.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET /api/v1/risk/session
  Return: List[SessionState] cho tất cả active symbols

GET /api/v1/risk/equity
  Query params: run_id (optional), limit (default 100)
  Return: List[EquitySnapshot] sorted by time asc
  (dùng để vẽ equity curve trên frontend)

POST /api/v1/risk/reset-halt
  Body: {symbol_id: UUID (optional)}
  Nếu có symbol_id: reset halt cho symbol đó
  Nếu không: reset halt cho tất cả symbols
  Set trading_halted=False, consecutive_failures=0
  Return: {reset_count: int, symbols_reset: List[str]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE 9: backend/app/api/v1/runs.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GET /api/v1/runs
  Query params: symbol_id, mode, status, limit
  Return: List[ResearchRunRead]

POST /api/v1/runs
  Body: BacktestConfig
  Chạy backtest async (asyncio.create_task)
  Return ngay: {run_id, status: "RUNNING", message: "Backtest started"}

GET /api/v1/runs/{run_id}
  Return: ResearchRunRead + BacktestSummary

GET /api/v1/runs/{run_id}/trades
  Return: List[TradeRead] của run đó

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: backend/tests/test_auth_api.py (6 cases)
Dùng FastAPI TestClient (httpx)

Test 1: Login success
  POST /api/v1/auth/login với đúng credentials
  Assert: 200, có access_token, có Set-Cookie refresh_token

Test 2: Login fail — sai password
  POST với sai password
  Assert: 401, message chứa "Invalid credentials"

Test 3: Login rate limit
  POST 6 lần liên tiếp cùng IP
  Assert: lần thứ 6 trả về 429

Test 4: Refresh token success
  Login trước → lấy cookie
  POST /api/v1/auth/refresh với cookie đó
  Assert: 200, có access_token mới

Test 5: Protected route — không có token
  GET /api/v1/symbols không có Authorization header
  Assert: 401

Test 6: Protected route — có token
  Login → lấy access_token
  GET /api/v1/symbols với header Authorization: Bearer {token}
  Assert: 200

Chạy: python -m pytest backend/tests/test_auth_api.py -v
Expected: 6/6 PASSED