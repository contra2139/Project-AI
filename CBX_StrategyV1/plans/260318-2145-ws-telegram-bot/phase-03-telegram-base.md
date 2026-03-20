# Phase 03: Telegram Bot Base & Auth
Status: ✅ Complete
Dependencies: [Phase 01: Setup & Notification Core](phase-01-setup.md)

## Objective
Khởi tạo Telegram Bot, thiết lập Webhook và cơ chế bảo mật Whitelist để chỉ phản hồi người dùng được phép.

## Requirements
### Functional
- [x] Initialize `python-telegram-bot` Application.
- [x] Implement Webhook endpoint (`POST /tg/webhook`) with secret token verification.
- [x] Implement `@require_auth` decorator (Whitelist check).
- [x] Implement `@require_admin` decorator (Admin check).
- [x] Support stealth mode (no reply to unauthorized users).

### Non-Functional
- [ ] Secure webhook secret handling.
- [ ] Admin-only access for sensitive commands.
- [ ] Robust error handling for webhook payload.

## Implementation Steps
1. [x] Create `backend/app/telegram/bot.py`.
2. [x] Create `backend/app/telegram/auth.py`.
3. [x] Implement webhook route in `backend/app/main.py`.
4. [x] Define decorators for auth and admin checks.
5. [x] Configure `TELEGRAM_ALLOWED_USER_IDS` and `TELEGRAM_BOT_TOKEN` in `.env`.

## Files to Create/Modify
- `backend/app/telegram/bot.py` [NEW]
- `backend/app/telegram/auth.py` [NEW]
- `backend/app/main.py` [MODIFY]
- `backend/.env` [MODIFY]

## Test Criteria
- [ ] Webhook rejects invalid secret token (403).
- [ ] Bot ignores messages from users NOT in whitelist.
- [ ] Bot responds to authorized users.
- [ ] Admin commands are restricted to `TELEGRAM_ADMIN_USER_ID`.

---
Next Phase: [Phase 04: Telegram Handlers](phase-04-handlers.md)
