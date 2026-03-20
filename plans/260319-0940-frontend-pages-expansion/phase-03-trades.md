# Phase 03: Trades Page

## Objective
Triển khai trang lịch sử giao dịch và thống kê hiệu năng.

## Requirements
### Functional
- [ ] Bảng giao dịch: `Time | Symbol | Side | Entry | Stop | Exit | Hold(bars) | PnL(R) | Reason`.
- [ ] Styling: Win (Xanh), Loss (Đỏ), Open (Vàng).
- [ ] Thống kê (Aggregate Stats): Win Rate, Avg Win R, Avg Loss R, Profit Factor.
- [ ] Chức năng Export CSV từ data hiện tại.
- [ ] Filter: Symbol, Side, Status, Date Range.

## Implementation Steps
1. [ ] Implement `src/app/trades/page.tsx`.
2. [ ] Thêm logic tính toán stats từ dataset.
3. [ ] Viết hàm `exportToCSV`.

## Test Criteria
- [ ] Kiểm tra PnL(R) hiển thị chính xác format (VD: +1.5R).
- [ ] Kiểm tra file CSV tải xuống đúng định dạng.

---
Next Phase: [Phase 04: Symbols Page](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/plans/260319-0940-frontend-pages-expansion/phase-04-symbols.md)
