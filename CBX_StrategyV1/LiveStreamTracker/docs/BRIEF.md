# 💡 BRIEF: Live Stream Tracker Pro

**Ngày tạo:** 2026-02-10
**Mục tiêu:** App Desktop quản lý Livestream đa nền tảng (TikTok, Facebook), tập trung vào dữ liệu và tương tác khán giả.

---

## 1. VẤN ĐỀ CẦN GIẢI QUYẾT
- Khó theo dõi comment, tương tác viewer realtime khi live trên nhiều nền tảng.
- Dữ liệu bị trôi mất sau khi live xong, không lưu trữ được.
- Thiếu công cụ tổng hợp, thống kê để tối ưu nội dung live.

## 2. GIẢI PHÁP ĐỀ XUẤT
- **Desktop App (Python/Flet):** Kết nối API Livestream -> Lấy dữ liệu Realtime -> Dashboard -> Google Sheets/Excel.
- **Tự động hóa:** Ghi nhận comment, like, share, gift, join/follow.

## 3. TÍNH NĂNG

### 🚀 MVP (Core Features - Bắt buộc có):
1.  **Kết nối Livestream:**
    - Input: Link Livestream (TikTok/Facebook Profile & Page).
    - Status: Check trạng thái live/offline.
2.  **Dashboard Điều khiển:**
    - Button **Start/Stop TikTok**.
    - Button **Start/Stop Facebook**.
    - Button **Snapshot Stats** (Thống kê tức thời).
    - Button **Exit** (Dừng app an toàn).
    - Khu vực **Log**: Hiển thị lỗi/trạng thái kết nối.
3.  **Thu thập Dữ liệu (Realtime):**
    - Viewers count.
    - Comments (Content, User info).
    - Likes/Reactions.
    - Gifts (TikTok)/Stars (Facebook - nếu có).
4.  **Lưu trữ & Báo cáo:**
    - Auto-push to **Google Sheets** (Mỗi nền tảng 1 sheet).
    - Xuất report sau phiên live.

### 🎁 Phase 2 (Nâng cao - Gợi ý thêm):
1.  **Alerts & Notifications:** Âm thanh khi có đơn/gift lớn.
2.  **Minigame:** Quay số trúng thưởng random comment.
3.  **Auto-Reply (Simple):** Trả lời câu hỏi thường gặp (như giá, ship).
4.  **Phân loại Khách hàng:** Tag khách quen/mới dựa trên lịch sử.
5.  **Biểu đồ Realtime:** Vẽ đồ thị tương tác ngay trên app.

## 4. YÊU CẦU KỸ THUẬT
- **OS:** Windows Desktop App.
- **Tech Stack:** Python, Flet (UI), Google Sheets API, TikTokLive lib, Facebook Graph API.
- **Config:** File `.env` để chỉnh các tham số (tần suất ghi log, ID sheet...).

## 5. BƯỚC TIẾP THEO
→ Chạy `/plan` để thiết kế chi tiết (Database, UI Mockup, Cấu trúc Code).
