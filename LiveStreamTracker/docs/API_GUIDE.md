# Hướng dẫn lấy API Key cho Live Stream Tracker

## 1. TikTok Username (`TIKTOK_USERNAME`)

Cái này dễ nhất!

1.  Mở trình duyệt, vào trang profile TikTok của bạn hoặc người bạn muốn theo dõi.
2.  Nhìn lên thanh địa chỉ (URL).
3.  Username là phần chữ sau `@`.
    *   VD: Link là `https://www.tiktok.com/@halinh.official`
    *   Username là: `halinh.official`
4.  Copy và dán vào `.env`: `TIKTOK_USERNAME=halinh.official`

---

## 2. Facebook Page Token (`FACEBOOK_PAGE_TOKEN`) & Page ID (`FACEBOOK_PAGE_ID`)

Cái này hơi phức tạp xíu, làm theo từng bước nhé:

### Bước 1: Tạo App trên Facebook Developers
1.  Truy cập: [developers.facebook.com](https://developers.facebook.com/)
2.  Đăng nhập -> Chọn "My Apps" -> "Create App".
3.  Chọn loại App: **"Other"** (hoặc "Business").
4.  Điền tên App (VD: `StreamTracker`) -> Tạo App.

### Bước 2: Lấy Token (Dùng Graph API Explorer cho nhanh)
1.  Truy cập: [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2.  Ở phần **Meta App**, chọn App bạn vừa tạo.
3.  Ở phần **User or Page**, chọn **"Get Page Access Token"**.
4.  Nó sẽ hiện popup hỏi quyền, bạn chọn Page bạn muốn quản lý -> Đồng ý.
5.  Sau khi xong, trường **Access Token** sẽ hiện ra một chuỗi dài loằng ngoằng.
6.  Copy chuỗi đó dán vào `.env`: `FACEBOOK_PAGE_TOKEN=...`

### Bước 3: Lấy Page ID
1.  Vẫn ở trang Graph API Explorer.
2.  Ở ô nhập lệnh (chỗ có chữ `me?fields=id,name`), bạn đổi thành `me?fields=id,name`.
3.  Bấm nút **Submit**.
4.  Kết quả trả về sẽ có dòng `"id": "123456789..."`.
5.  Đó chính là Page ID. Copy và dán vào `.env`: `FACEBOOK_PAGE_ID=...`

### ⚠️ Khắc phục lỗi "Tính năng không khả dụng" (Feature Unavailable)
Nếu bạn gặp lỗi mặt buồn "Hiện không dùng được tính năng này" khi lấy Token:
1.  Truy cập **Facebook Developers** -> **My Apps**.
2.  Chọn App bạn vừa tạo.
3.  Nhìn lên thanh trên cùng, tìm nút gạt **App Mode**.
4.  Chuyển từ **Live** sang **Development** (Môi trường phát triển).
5.  Quay lại **Graph API Explorer** và thử lấy Token lại.
    *   *Lưu ý: Trong chế độ Development, chỉ có tài khoản Admin/Developer của App mới lấy được Token.*

---

## 3. Google Sheet ID

1.  Mở file Google Sheet bạn muốn lưu dữ liệu.
2.  Nhìn lên URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit`
3.  ID là chuỗi ký tự dài ở giữa `/d/` và `/edit`.
4.  Copy và dán vào `.env`.
