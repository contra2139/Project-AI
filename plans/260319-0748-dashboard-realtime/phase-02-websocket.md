# Phase 02: WebSocket Hook
Status: ✅ Complete
Dependencies: Phase 01

## Objective
Cập nhật Login Route và xây dựng hook `useWebSocket` để quản lý kết nối.

## Requirements
- [ ] Backend login route set thêm `ws_token` (httpOnly=false).
- [ ] `useWebSocket` kết nối tới `${process.env.NEXT_PUBLIC_WS_URL}/ws?token={ws_token}`.
- [ ] Hỗ trợ auto-reconnect sau 3 giây.
- [ ] Phương thức `on(event, callback)` và `off(event, callback)`.

## Implementation Steps
1. [x] Sửa `src/app/api/auth/login/route.ts` để set cookie `ws_token`.
2. [x] Tạo file `frontend/src/hooks/useWebSocket.ts`.
3. [x] Implement logic đọc cookie `ws_token` và connect WS.
4. [x] Implement logic auto-reconnect.

## Files to Create/Modify
- `frontend/src/hooks/useWebSocket.ts`

## Test Criteria
- [ ] Log "WebSocket Connected" xuất hiện trong console khi backend đang chạy.
- [ ] Hook tự động reconnect khi backend restart.
