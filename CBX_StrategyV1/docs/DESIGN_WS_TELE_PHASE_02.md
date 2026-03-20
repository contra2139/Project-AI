# 🎨 DESIGN: WebSocket Manager (Phase 2)

Ngày tạo: 2026-03-18
Dựa trên: `plans/260318-2145-ws-telegram-bot/phase-02-websocket.md`

---

## 1. Thành phần chính (Components)

### `ConnectionManager` (trong `backend/app/api/websocket.py`)
Quản lý vòng đời của các kết nối WebSocket.

- **Lưu trữ**: `dict[str, WebSocket]` trong đó key là `client_id` (UUID).
- **Tính năng**:
  - `connect(client_id, websocket)`: Lưu kết nối mới.
  - `disconnect(client_id)`: Xóa kết nối khi client rời đi.
  - `broadcast(message: dict)`: Gửi tin nhắn tới tất cả client đang kết nối.
  - `send_personal_message(message: dict, client_id: str)`: Gửi tới 1 client cụ thể.

---

## 2. Luồng Hoạt Động (Flows)

### 2.1. Kết nối & Xác thực (Handshake)
1. Client kết nối tới `ws://.../ws?token=<JWT>`.
2. Server lấy `token` từ query parameters.
3. Giải mã và kiểm tra tính hợp lệ của token qua `decode_token()`.
4. Nếu hợp lệ: `websocket.accept()`.
5. Nếu không hợp lệ: `websocket.close(code=4001)`.

### 2.2. Duy trì kết nối (Keep-alive)
- Sử dụng `asyncio.create_task` để chạy vòng lặp `_ping_loop`.
- Mỗi 30 giây: Gửi `{"type": "ping", "timestamp": "..."}`.
- Chờ phản hồi `pong` trong tối đa 10 giây.
- Nếu quá hạn: Tự động ngắt kết nối và dọn dẹp.

---

## 3. Định dạng Tin nhắn (Message Format)

Tất cả tin nhắn broadcast/send_to đều tuân thủ cấu trúc:
```json
{
  "type": "signal_detected" | "trade_opened" | "trade_closed" | "bot_status" | "price_update" | "regime_change" | "system_error" | "ping",
  "data": { ... },
  "timestamp": "ISO8601 string"
}
```

---

## 4. Tích hợp Hệ thống (Integration)

Dòng chảy dữ liệu được "kết nối" thông qua việc gán (injection) trong `main.py`:

```python
# Startup event
notification_service.ws_manager = connection_manager
```

---

## 5. Checklist Kiểm Tra (Acceptance Criteria)

✅ **Cơ bản:**
- [ ] Kết nối thành công với token hợp lệ.
- [ ] Bị từ chối với token sai/hết hạn.
- [ ] Gửi được tin nhắn tới tất cả client.
- [ ] Xóa client khỏi danh sách khi ngắt kết nối.

✅ **Nâng cao:**
- [ ] Vòng lặp Ping/Pong hoạt động ổn định.
- [ ] Handle được `WebSocketDisconnect` mà không làm sập server.
- [ ] `NotificationService` gọi được `ws_manager` sau khi inject.

---

## 6. Test Cases

### TC-01: WebSocket Auth
- **When**: Kết nối tới `/ws` không có token hoặc token sai.
- **Then**: Server đóng kết nối với code 4001.

### TC-02: Targeted Messaging
- **When**: Gọi `send_personal_message` tới 1 client_id.
- **Then**: Chỉ client đó nhận được tin nhắn, client khác thì không.

---
Next Phase: [Phase 03: Telegram Bot Base & Auth]
