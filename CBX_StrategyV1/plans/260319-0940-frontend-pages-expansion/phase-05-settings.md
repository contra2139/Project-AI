# Phase 05: Settings Page

## Objective
Cấu hình tổng thể bot, quản lý rủi ro và trạng thái kết nối.

## Requirements
### Functional
- [ ] Bot Mode Toggle: AUTO (Vàng) ↔ MANUAL (Xám).
- [ ] Risk Management: Inputs cho Risk per trade, Max positions, Daily stop.
- [ ] Notifications: Toggles cho Signal/Entry/Exit/Summary.
- [ ] Connection Status: Trạng thái Binance API (latency), Telegram, WebSocket.

## Implementation Steps
1. [ ] Implement `src/app/settings/page.tsx`.
2. [ ] Thêm logic Ping Test cho Binance connection.
3. [ ] Đồng bộ trạng thái từ `botStore`.

## Test Criteria
- [ ] Kiểm tra Toggle Bot Mode gửi PATCH request và cập nhật UI.
- [ ] Kiểm tra latency hiện thị sau khi bấm "Ping Test".

---
Next Phase: [Phase 06: Verification](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/plans/260319-0940-frontend-pages-expansion/phase-06-verification.md)
