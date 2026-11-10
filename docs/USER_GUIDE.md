# Hướng Dẫn Sử Dụng Giao Diện Multi_Emulator (Phone Farm Box Dashboard)

**Phụ trách phân hệ Frontend & Interactive Dashboard:** Chương (`feat/ui-dashboard-grid`, `feat/adr-interactive-viewer`)

---

## 1. Cấu Trúc Thư Mục Giao Diện (Deliverables của Chương)

Toàn bộ mã nguồn giao diện được tổ chức theo kiến trúc ES6 Modules gọn nhẹ, không phụ thuộc các thư viện nặng để tối ưu RAM cho máy chủ chạy giả lập:

- [`public/index.html`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/index.html) (đồng bộ với [`index.html`](file:///home/antigravity/TrungLegit/Multi_Emulator/index.html)): Khung HTML5 ngữ nghĩa gồm 4 phân hệ chính:
  1. **Phone Farm Matrix (7×3 Grid):** Lưới 21 màn hình điện thoại mô phỏng thiết bị thực tế giống hệt mẫu Phone Farm Box.
  2. **Table View:** Bảng quản lý chi tiết từng máy ảo (ID, Cổng ADB/TCP, Độ phân giải, CPU/RAM, Start/Stop/Optimize/Delete).
  3. **ADR Learning Portal:** Chuyên mục học tập Quyết định Kiến trúc (ADR-001 đến ADR-005).
  4. **Browser Profiles Sync Hub:** Tạo, chạy, dừng và điều khiển đồng bộ các profile Chromium qua CDP.
  5. **User Guide:** Hướng dẫn thao tác trực tiếp trên Web.
- [`public/css/main.css`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/css/main.css): Hệ thống biến màu CSS (`:root`), bố cục 2 cột (Sidebar điều khiển bên trái + Lưới 21 máy ảo bên phải), hiệu ứng sóng chạm (Tap Ripple) và quạt tản nhiệt Box.
- [`public/js/app.js`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/js/app.js): Quản lý trạng thái (`state`), gọi REST API, xử lý sự kiện chạm đồng bộ (`handlePhoneScreenTap`), chuyển đổi ứng dụng đồng loạt (TikTok, Facebook, Instagram, YouTube, Treo Game) và Modal tạo máy ảo.
- [`public/js/websocket.js`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/js/websocket.js): Kết nối kênh sự kiện thời gian thực (`/api/events`) để tự động cập nhật log và trạng thái mà không cần tải lại trang.
- [`public/js/adrViewer.js`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/js/adrViewer.js): Tải danh sách ADR từ `/api/adrs` và chuyển đổi định dạng Markdown sang HTML trực quan.

---

## 2. Cách Khởi Chạy & Kiểm Thử

1. **Khởi động máy chủ Node.js + Python Core:**
   ```bash
   npm start
   ```
2. **Truy cập giao diện Web Dashboard:**
   Mở trình duyệt tại địa chỉ `http://localhost:3000`.
3. **Chạy bộ kiểm thử tự động (Unit Tests):**
   ```bash
   npm test
   ```

## 3. Quản lý Browser Profiles

Mở tab **Browser Sync Hub** sau khi khởi chạy server:

1. Chọn số lượng (1–50) và loại trình duyệt, sau đó bấm **Tạo Profiles**. Trình duyệt cần được cài trên máy chạy server; có thể đặt `BROWSER_BIN` để chỉ định executable.
2. Bấm **Chạy tất cả** hoặc nút **Chạy** trên từng profile. Danh sách hiển thị trạng thái CDP và cổng gỡ lỗi của từng profile. **Dừng** đóng profile đã chọn; **Dừng tất cả** đóng toàn bộ.
3. Nhập URL rồi bấm **Mở trên profiles đang chạy**, hoặc dùng nút TikTok, Facebook, YouTube, Google. Các lệnh cuộn, tải lại, click CSS selector và nhập văn bản được gửi qua `/api/browser/sync`.
4. Danh sách trạng thái được tải lại sau thao tác và khi nhận sự kiện SSE từ `/api/events`. Nếu thay đổi trạng thái ngoài dashboard, bấm **Làm mới** để truy vấn lại.

Các thao tác đồng bộ chỉ chạy trên profile đang kết nối CDP. Trình duyệt có thể giới hạn thao tác DOM, và một số website có thể chặn tương tác tự động.
