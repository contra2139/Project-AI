# Phase 04: Symbols Page

## Objective
Quản lý danh sách symbols và cấu hình chiến thuật cho từng cặp.

## Requirements
### Functional
- [ ] Grid cards hiển thị thông tin Symbol.
- [ ] Toggle nhanh: `is_in_universe` và `is_active`.
- [ ] Hiển thị giá real-time từ WS `price_update`.
- [ ] Config Modal: Chỉnh sửa toàn bộ `SymbolStrategyConfig` (Compression, Breakout, Exit, Risk).
- [ ] Add Symbol button: Thêm symbol mới vào hệ thống.

## Implementation Steps
1. [ ] Implement `src/app/symbols/page.tsx` với grid layout.
2. [ ] Xây dựng Config Modal linh hoạt với nhiều section.
3. [ ] Kết nối các nút [⚙️ Edit Config] và [▶ Run Backtest].

## Test Criteria
- [ ] Kiểm tra PATCH request gửi đúng dữ liệu khi gạt toggle.
- [ ] Kiểm tra Modal config load đúng dữ liệu của symbol được chọn.

---
Next Phase: [Phase 05: Settings Page](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/plans/260319-0940-frontend-pages-expansion/phase-05-settings.md)
