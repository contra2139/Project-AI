# Phase 04: Telegram Handlers (Commands)
Status: ✅ Complete
Dependencies: [Phase 03: Telegram Bot Base & Auth](phase-03-telegram-base.md)

## Objective
Triển khai các xử lý lệnh (handlers) để người dùng có thể tương tác với bot: xem trạng thái, tín hiệu, danh sách lệnh và đặt lệnh thủ công.

## Requirements
### Functional
- [x] Implement `/start`, `/status`, `/buy`, `/sell`, `/close`, `/mode`, `/signals`, `/trades`, `/ask`.
- [x] Integrate with `@require_auth` and `@require_admin` decorators.
- [x] Implement CallbackQuery handler for inline buttons.
- [x] Support manual trading commands with argument parsing.
- [ ] Implement exit: `/close`, `/close all`.
- [ ] Implement AI query: `/ask` (Gemini integration with strategy context).
- [ ] Integrate Main Menu Keyboard.

### Non-Functional
- [ ] Proper error catching in handlers to prevent crashes.
- [ ] Clear, formatted Vietnamese responses.
- [ ] Validation of command arguments (symbol, size, price).

## Implementation Steps
1. [x] Create `backend/app/telegram/handlers.py`.
2. [x] Create `backend/app/telegram/keyboards.py`.
3. [x] Implement signal notification formatting in `backend/app/telegram/notifications.py`.
4. [x] Implement command logic (status, buy/sell parsing, AI ask).
5. [x] Register handlers in `backend/app/telegram/bot.py`.

## Files to Create/Modify
- `backend/app/telegram/handlers.py` [NEW]
- `backend/app/telegram/keyboards.py` [NEW]
- `backend/app/telegram/notifications.py` [NEW]

## Test Criteria
- [ ] `/status` returns accurate equity and position data.
- [ ] `/buy` correctly parses parameters and triggers entry logic.
- [ ] Inline buttons for signals correctly trigger order placement.
- [ ] `/ask` returns a relevant AI response in Vietnamese.

---
Next Phase: [Phase 05: Integration & Testing](phase-05-testing.md)
