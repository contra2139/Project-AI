# Phase 03: Chart Components
Status: ✅ Complete
Dependencies: Phase 01

## Objective
Tạo các component biểu đồ TradingChart và EquityCurve.

## Implementation Steps
1. [x] Tạo `frontend/src/components/charts/TradingChart.tsx`.
2. [x] Tích hợp `lightweight-charts` với dark theme.
3. [x] Fetch klines từ Binance API với try/catch.
4. [x] Implement `generateMockKlines(200)` cho trường hợp fallback.
5. [x] Tạo `frontend/src/components/charts/EquityCurve.tsx`.
6. [x] Sử dụng `recharts` để vẽ đường equity.

## Files to Create/Modify
- `frontend/src/components/charts/TradingChart.tsx`
- `frontend/src/components/charts/EquityCurve.tsx`

## Test Criteria
- [ ] Chart hiển thị nến thật của BTC/USDC.
- [ ] EquityCurve render được (dùng mock data ban đầu nếu API chưa có).
