# Phase 02: Signals Page

## Objective
Triển khai trang danh sách tín hiệu và Modal chi tiết tín hiệu.

## Requirements
### Functional
- [ ] Fetch signals từ `GET /api/v1/signals` sử dụng React Query.
- [ ] WebSocket integration để prepend tín hiệu mới.
- [ ] Filter bar: Lọc theo Symbol, Side, Status.
- [ ] Signal Card: Grid 2 columns trên desktop, 1 column trên mobile.
- [ ] Signal Detail Modal: 3 tabs: Event Chain, Chart, AI Analysis.

## Implementation Steps
1. [ ] Implement signal list và filters trong `src/app/signals/page.tsx`.
2. [ ] Thêm logic Modal cho Signal chi tiết.
3. [ ] Tích hợp `TradingChart` nhỏ tập trung vào signal timestamp.

## Test Criteria
- [ ] Kiểm tra tín hiệu mới hiện lên đầu danh sách qua WS.
- [ ] Kiểm tra chuyển tab trong Modal.

---
Next Phase: [Phase 03: Trades Page](file:///e:/Agent_AI_Antigravity/CBX_StrategyV1/plans/260319-0940-frontend-pages-expansion/phase-03-trades.md)
