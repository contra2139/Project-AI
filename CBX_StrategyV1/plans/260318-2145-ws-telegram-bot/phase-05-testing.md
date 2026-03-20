# Phase 05: Integration & Testing
Status: ✅ Complete
Dependencies: [Phase 04: Telegram Handlers](phase-04-handlers.md)

## Objective
Tích hợp tất cả các thành phần lại với nhau và thực hiện kiểm thử toàn diện để đảm bảo hệ thống hoạt động ổn định, bảo mật và chính xác.

## Requirements
### Functional
- [x] Ensure `NotificationService` correctly broadcasts to both WS and Telegram.
- [x] Verify message formatting for all event types.
- [x] Test end-to-end flow: Signal Trigger -> Notification -> UI Update & Telegram Alert.
- [x] Test manual order placement via Telegram buttons.

### Non-Functional
- [ ] Robustness under network failure (reconnect logic for WS).
- [x] No leaking of sensitive information in Telegram logs.
- [x] Verification of all 5 test cases in `backend/tests/test_telegram_handlers.py`.

## Implementation Steps
1. [x] Implement `backend/tests/test_telegram_handlers.py`.
2. [x] Conduct manual verification of WebSocket broadcast using a test client.
3. [x] Perform Telegram bot end-to-end smoke test (authorized vs unauthorized).
4. [x] Verify that Redis TTL and key management work as expected for signals.

## Files to Create/Modify
- `backend/tests/test_telegram_handlers.py` [NEW]

## Test Criteria (The 5 Mandatory Cases)
- [x] Case 1: Auth whitelist — Unauthorized user (Stealth mode).
- [x] Case 2: Auth whitelist — Authorized user.
- [x] Case 3: `/buy` command parameter parsing.
- [x] Case 4: `/buy` command with missing SL/TP (default to signal).
- [x] Case 5: WebSocket broadcast JSON format verification.

---
Next Step: Done!
