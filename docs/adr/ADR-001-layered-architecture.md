# ADR-001: Lựa Chọn Mô Hình Kiến Trúc Đa Tầng (Python Core - Node.js Orchestrator - Modern Web UI)

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày:** 2026-11-08
- **Tác giả:** Trung (Core Architect), Khoa (Backend Lead), Chương (Frontend Lead)

## 1. Bối cảnh (Context)
Dự án `Multi_Emulator` hướng tới mục tiêu xây dựng một nền tảng giả lập Android siêu nhẹ (tương tự LDPlayer / Phone Farm Box) chuyên dụng để chạy các ứng dụng mạng xã hội (TikTok, Facebook, Instagram, YouTube) và treo game nhẹ đồng loạt trên nhiều máy ảo cùng lúc, đồng thời đóng vai trò là dự án học thuật minh họa kiến trúc phần mềm.

Hệ thống cần giải quyết 3 bài toán khác nhau:
1. Tương tác cấp thấp với hệ điều hành, QEMU/KVM/WHPX và giao thức ADB (Android Debug Bridge).
2. Điều phối bất đồng bộ (Asynchronous I/O), cung cấp RESTful API và truyền tải sự kiện thời gian thực (Real-time events/logs) lên giao diện điều khiển.
3. Hiển thị trực quan lưới hàng chục màn hình điện thoại (Phone Farm Matrix Grid), đồng bộ thao tác chạm/vuốt (Multi-Control Sync) mượt mà trên trình duyệt hoặc ứng dụng.

## 2. Quyết định (Decision)
Chúng tôi quyết định áp dụng mô hình **Kiến trúc 3 tầng phân tách rõ ràng (3-Tier Separation of Concerns)**:
- **Tầng 1 — Presentation Layer (`public/` & `index.html`, `css/main.css`, `js/`):** Giao diện Web Dashboard theo phong cách Phone Farm Control Center (không dùng framework nặng, viết bằng Vanilla HTML5/CSS3/ES6 Modules kết hợp HTML5 Canvas) để giảm thiểu RAM tiêu thụ của trình quản lý.
- **Tầng 2 — Orchestration Layer (`index.js`, `server/`):** Máy chủ Node.js đóng vai trò API Gateway, quản lý phiên, điều phối tiến trình con (IPC) và phát sự kiện thời gian thực (SSE/WebSocket).
- **Tầng 3 — Core Emulator Engine (`src/core/`, `main.py`):** Động cơ lõi viết bằng Python 3.10+ quản lý vòng đời máy ảo (`InstanceManager`), kết nối ADB (`ADBDeviceAdapter`) và tối ưu hóa tài nguyên (`AdbOptimizer`).

## 3. Lý do lựa chọn (Rationale)
- **Siêu nhẹ (Ultra-lightweight):** Khác với các trình quản lý ngốn hàng trăm MB RAM, giao diện Web thuần + Node.js HTTP server tốn chưa tới 40MB RAM, nhường toàn bộ tài nguyên CPU/RAM cho các máy ảo Android.
- **Tận dụng thế mạnh từng ngôn ngữ:** Python cực mạnh về tự động hóa hệ thống và xử lý tiến trình (`subprocess`, `ThreadPoolExecutor`), trong khi Node.js tối ưu cho Non-blocking I/O và real-time streaming.

## 4. Hệ quả (Consequences)
- **Tích cực:** Các thành viên (Trung, Khoa, Chương) có thể phát triển và kiểm thử độc lập từng tầng dựa trên JSON Contract đã thống nhất ở mục 4.2 của `PLAN.md`.
- **Tiêu cực / Đánh đổi:** Cần xây dựng lớp cầu nối IPC (`pythonBridge.js`) giữa Node.js và Python (được giải quyết chi tiết trong ADR-002).
