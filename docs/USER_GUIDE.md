# Hướng Dẫn Sử Dụng Giao Diện Multi_Emulator (Phone Farm Box Dashboard)

**Phụ trách phân hệ Frontend & Interactive Dashboard:** Chương (`feat/ui-dashboard-grid`, `feat/adr-interactive-viewer`)

---

## 1. Cấu Trúc Thư Mục Giao Diện (Deliverables của Chương)

Toàn bộ mã nguồn giao diện được tổ chức theo kiến trúc ES6 Modules gọn nhẹ, không phụ thuộc các thư viện nặng để tối ưu RAM cho máy chủ chạy giả lập:

- [`public/index.html`](file:///home/antigravity/TrungLegit/Multi_Emulator/public/index.html) (đồng bộ với [`index.html`](file:///home/antigravity/TrungLegit/Multi_Emulator/index.html)): Khung HTML5 ngữ nghĩa gồm 4 phân hệ chính:
  1. **Phone Farm Matrix (7×3 Grid):** Lưới 21 màn hình điện thoại mô phỏng thiết bị thực tế giống hệt mẫu Phone Farm Box.
  2. **Table View:** Bảng quản lý chi tiết từng máy ảo (ID, Cổng ADB/TCP, Độ phân giải, CPU/RAM, Start/Stop/Optimize/Delete).
  3. **ADR Learning Portal:** Chuyên mục học tập Quyết định Kiến trúc (ADR-001 đến ADR-005).
  4. **Browser Profiles Sync Hub:** Điều khiển đồng bộ đa profile trình duyệt (Chrome, Edge, Brave) chống lag, cache 32MB và giao thức CDP.
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
