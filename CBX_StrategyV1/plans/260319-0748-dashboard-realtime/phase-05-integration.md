# Phase 05: Dashboard Integration
Status: ✅ Complete
Dependencies: Phase 02, 03, 04

## Objective
Tích hợp các thành phần vào trang Dashboard chính and kết nối dữ liệu thật.

## Implementation Steps
1. [x] Cập nhật `frontend/src/app/dashboard/page.tsx`.
2. [x] Sử dụng React Query để fetch metrics.
3. [x] Tích hợp `useWebSocket` để nhận signal live.
4. [x] Implement Tab switching giữa BTC/BNB/SOL.

## Files to Create/Modify
- `frontend/src/app/dashboard/page.tsx`

## Test Criteria
- [ ] Dashboard không còn dùng mock data cứng.
- [ ] Biểu đồ đổi symbol khi Tab chuyển đổi.
