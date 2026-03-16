# 📖 HƯỚNG DẪN GIT TERMINAL (QUICK REF)

Tài liệu tóm tắt các lệnh Git cơ bản để quản lý dự án **Binance Price AI**.

---

### 📥 1. TẢI DỰ ÁN (CLONE)
Sử dụng khi bắt đầu ở một máy tính mới:
```bash
git clone https://github.com/contra2139/Project-AI.git
```

### 🆙 2. CẬP NHẬT (PULL)
Lấy bản code mới nhất từ GitHub về máy:
```bash
git pull origin master
```

### 💾 3. LƯU THAY ĐỔI (COMMIT & PUSH)
Lưu lại thành quả anh vừa sửa và đẩy lên GitHub:
1. **Kiểm tra trạng thái:** `git status`
2. **Chọn file lưu:** `git add .` (hoặc `git add <tên_file>`)
3. **Lưu (Commit):** `git commit -m "Nội dung thay đổi"`
4. **Đẩy lên (Push):** `git push origin master`

---

### 🛠️ 4. XỬ LÝ LỖI THƯỜNG GẶP
* **Trùng lặp (Conflict):** Khi `git pull` báo lỗi conflict, anh cần mở file bị lỗi, chọn giữ lại đoạn code đúng và commit lại.
* **Sai Remote:** Nếu muốn xem đang kết nối với GitHub nào: `git remote -v`
* **Quay lại bản cũ:** `git log --oneline` (xem mã commit) rồi `git checkout <mã_commit>`

---
*Ghi chú: Luôn đảm bảo đã tạo file `.env` thủ công sau khi clone.*
