# Phase 02: WebSocket Manager
Status: ✅ Complete
Dependencies: [Phase 01: Setup & Notification Core](phase-01-setup.md)

## Objective
Xây dựng WebSocket endpoint (`/ws`) và trình quản lý kết nối (`ConnectionManager`) để đẩy dữ liệu realtime tới Frontend.

## Requirements
### Functional
- [x] Implement `ConnectionManager` (connect, disconnect, broadcast, send_to).
- [x] Add JWT authentication to WebSocket connection (via query param).
- [x] Support message types: `signal_detected`, `trade_opened`, `trade_closed`, `bot_status`, `price_update`, `regime_change`, `system_error`.
- [x] Implement 30s Ping/Pong keep-alive.

### Non-Functional
- [ ] Handle concurrent connections efficiently.
- [ ] Secure token validation.
- [ ] Clean up resources on disconnect.

## Implementation Steps
1. [x] Create `backend/app/api/websocket.py`.
2. [x] Define `ConnectionManager` class.
3. [x] Implement `ws_endpoint` with JWT validation logic.
4. [x] Register the WebSocket route in `backend/app/main.py`.

## Files to Create/Modify
- `backend/app/api/websocket.py` [NEW]
- `backend/app/main.py` [MODIFY]

## Test Criteria
- [ ] Connection with invalid token is rejected (code 4001).
- [ ] Connection with valid token is accepted.
- [ ] Broadcast message is received by all connected clients.
- [ ] Disconnect correctly removes client from manager.

---
Next Phase: [Phase 03: Telegram Bot Base & Auth](phase-03-telegram-base.md)
