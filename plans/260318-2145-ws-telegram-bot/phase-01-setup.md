# Phase 01: Setup & Notification Core
Status: ✅ Complete
Dependencies: None

## Objective
Thiết lập dịch vụ thông báo trung tâm (`NotificationService`) để điều phối các sự kiện từ hệ thống (Signal, Trade, Error) tới các kênh đầu ra (WebSocket, Telegram).

## Requirements
### Functional
- [x] Implement `NotificationService` class.
- [x] Support `notify_signal`, `notify_trade_opened`, `notify_trade_closed`.
- [x] Implement `broadcast_price_update(prices)` (WebSocket only).
- [x] Implement `send_daily_summary()` (Telegram only, cron-like logic).
- [x] Implement `notify_error(module, error, critical)` (Log + Telegram Admin if critical).
- [x] Fetch notification settings from Redis (`bot:notification_settings`).

### Non-Functional
- [ ] Async/await compliant.
- [ ] Low latency dispatch.
- [ ] Error isolation (one channel failure shouldn't block others).

## Implementation Steps
1. [x] Install `python-telegram-bot` and `websockets` dependencies.
2. [x] Create `backend/app/services/notification_service.py`.
3. [x] Implement logic to check Redis settings before dispatching.
4. [ ] Integrate `NotificationService` into the main `TradeManager` or `Scanner` loop.

## Files to Create/Modify
- `backend/app/services/notification_service.py` [NEW]
- `backend/requirements.txt` [MODIFY]
- `backend/.env` [MODIFY]

## Test Criteria
- [ ] Service correctly reads settings from Redis.
- [ ] Critical errors trigger an internal log (and later Telegram).
- [ ] Signal notification logic branch is covered.

---
Next Phase: [Phase 02: WebSocket Manager](phase-02-websocket.md)
