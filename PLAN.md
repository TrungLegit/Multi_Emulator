# KẾ HOẠCH PHÁT TRIỂN DỰ ÁN MULTI_EMULATOR
**Phiên bản Giáo dục & Tài liệu Quyết định Kiến trúc (Educational ADR Edition)**

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

### 1.1. Bối cảnh & Mục tiêu
- **Tên dự án:** `Multi_Emulator`
- **Định hướng:** Xây dựng hệ thống quản lý, điều phối và giám sát đa giả lập (Multi-Emulator Platform) với mục tiêu giáo dục. Dự án làm nổi bật cả 2 khía cạnh:
  1. **Kỹ thuật hệ thống:** Tích hợp đa ngôn ngữ (Python Core Engine + Node.js API Orchestrator + Modern Web UI Frontend).
  2. **Kỹ thuật phần mềm:** Áp dụng phương pháp ghi nhận quyết định kiến trúc thông qua **ADR (Architecture Decision Records)**, giúp sinh viên và người học nắm vững lý do đằng sau từng lựa chọn công nghệ.

### 1.2. Kiến trúc tổng thể (High-Level Architecture)
Hệ thống được thiết kế theo mô hình 3 tầng phân tách rõ ràng (Separation of Concerns):

```
+-----------------------------------------------------------------------+
|                    TẦNG 1: TRÌNH DIỄN & GIAO DIỆN                     |
|           Frontend Web Dashboard (HTML5, CSS3, JavaScript)             |
|   - Grid View giám sát đa máy ảo       - Bảng điều khiển tác vụ       |
|   - Console Log Viewer thời gian thực  - Trình duyệt ADR giáo dục     |
+-----------------------------------^-----------------------------------+
                                    | (HTTP REST / WebSocket)
+-----------------------------------v-----------------------------------+
|               TẦNG 2: ĐIỀU PHỐI & TRUYỀN THÔNG DỊCH VỤ                |
|                    Backend Orchestrator (Node.js)                     |
|   - RESTful API & WebSocket Server    - Quản lý phiên & Instance Pool  |
|   - IPC Gateway sang Python Core      - Monitoring & Event Hub        |
+-----------------------------------^-----------------------------------+
                                    | (IPC: Subprocess / Socket / JSON)
+-----------------------------------v-----------------------------------+
|                     TẦNG 3: ĐỘNG CƠ LÕI & ĐIỀU KHIỂN                  |
|                   Core Emulator Engine (Python 3.10+)                 |
|   - Instance Lifecycle (Start/Stop)   - Device Controller (ADB/CLI)   |
|   - Virtual Hardware State Machine    - Resource Monitor (CPU/RAM)    |
|   - Hồ sơ kiến trúc mẫu (ADRs)        - Automated Test Suite          |
+-----------------------------------------------------------------------+
```

---

## 2. PHÂN CHIA NHÂN SỰ & TRÁCH NHIỆM CHI TIẾT (3 THÀNH VIÊN)

Dự án được phân chia thành 3 mảng chuyên trách độc lập nhưng liên kết chặt chẽ cho **Trung**, **Khoa**, và **Chương**:

---

### PHẦN 1: TRUNG — CORE ARCHITECT & PYTHON ENGINE LEAD
*Phụ trách: Kiến trúc hệ thống tổng thể, Hồ sơ ADR, Động cơ lõi Python & Tự động hóa giả lập.*

#### A. Trách nhiệm chính:
1. **Kiến trúc sư trưởng & Quản lý ADR:**
   - Xây dựng thư mục `docs/adr/` và viết các tài liệu kiến trúc mẫu (ADR-001 đến ADR-006).
   - Thiết lập quy chuẩn mã nguồn, quy chuẩn Git flow, quy tắc đóng góp mã nguồn (`CONTRIBUTING.md`).
2. **Phát triển Core Engine (`main.py` & module Python):**
   - Thiết kế mô hình hướng đối tượng quản lý vòng đời giả lập (`EmulatorInstance`, `InstanceManager`, `DeviceConfig`).
   - Xây dựng bộ điều khiển giao tiếp với thiết bị ảo (tích hợp ADB - Android Debug Bridge hoặc mock emulator adapter cho mục đích giáo dục).
   - Quản lý cấu hình thông qua biến môi trường (`python-dotenv`) và file JSON/YAML.
   - Xây dựng cơ chế thu thập tài nguyên máy chủ/máy ảo (CPU, RAM, FPS, trạng thái kết nối).
3. **Cơ chế IPC / CLI:**
   - Xây dựng giao diện dòng lệnh (CLI Interface) mạnh mẽ cho Core Engine bằng `argparse` hoặc `click`.
   - Cung cấp cổng IPC (giao thức JSON qua `sys.stdin`/`sys.stdout` hoặc Unix/TCP Socket) để Node.js gọi xuống.
4. **Kiểm thử & Chất lượng mã nguồn:**
   - Viết Unit Tests với `pytest` đạt độ bao phủ kiểm thử (coverage) tối thiểu 80%.
   - Cấu hình linter và formatter với `ruff`.

#### B. Sản phẩm bàn giao (Deliverables):
- Thư mục `docs/adr/` với đầy đủ các bản ghi quyết định kiến trúc:
  - `ADR-001: Lựa chọn mô hình đa tầng Python-Node-Web`.
  - `ADR-002: Cơ chế IPC giữa Node.js và Python Core`.
  - `ADR-003: Chiến lược trừu tượng hóa bộ điều khiển giả lập (Adapter Pattern)`.
  - `ADR-004: Quản lý trạng thái đa tiến trình giả lập`.
- Gói module Python hoàn chỉnh (`src/core/`):
  - `instance_manager.py`: Khởi động, dừng, restart, nhân bản (clone) giả lập.
  - `device_adapter.py`: Adapter tương tác với thiết bị ảo / ADB.
  - `metrics_collector.py`: Đo đạc tài nguyên.
  - `cli.py`: Giao diện CLI.
- Bộ test suite `tests/` chạy thông qua `pytest`.

#### C. Nguồn tài liệu tham khảo cho Trung:
1. **Kiến trúc ADR (Architecture Decision Records):**
   - *ADR Organization GitHub*: [https://adr.github.io/](https://adr.github.io/)
   - *Michael Nygard ADR Template*: [https://github.com/joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)
   - *Martin Fowler - Architecture Decision Records*: [https://martinfowler.com/articles/scaling-architecture-conversationally.html](https://martinfowler.com/articles/scaling-architecture-conversationally.html)
2. **Python System Programming & Process Automation:**
   - *Python Subprocess & Multiprocessing Official Docs*: [https://docs.python.org/3/library/subprocess.html](https://docs.python.org/3/library/subprocess.html)
   - *Python Asyncio & IPC*: [https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
   - *Ruff Linter & Formatter*: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
   - *Pytest Framework*: [https://docs.pytest.org/en/stable/](https://docs.pytest.org/en/stable/)
3. **Android Emulator & ADB Automation:**
   - *Android Debug Bridge (ADB) Official Guide*: [https://developer.android.com/tools/adb](https://developer.android.com/tools/adb)
   - *Pure-Python-ADB Library (Tham khảo mô hình)*: [https://github.com/swind/pure-python-adb](https://github.com/swind/pure-python-adb)
   - *Android Emulator Command-line Tool*: [https://developer.android.com/studio/run/emulator-commandline](https://developer.android.com/studio/run/emulator-commandline)

---

### PHẦN 2: KHOA — BACKEND ORCHESTRATOR & API INTEGRATION LEAD
*Phụ trách: Máy chủ Node.js, RESTful API, WebSocket thời gian thực, Cầu nối IPC & CI/CD Pipeline.*

#### A. Trách nhiệm chính:
1. **Thiết kế & Nâng cấp Máy chủ Node.js (`index.js` & `server/`):**
   - Chuyển đổi từ HTTP server cơ bản sang kiến trúc module hóa (Express.js hoặc Fastify).
   - Thiết kế hệ thống định tuyến (Routing) cho RESTful API:
     - `GET /api/instances`: Lấy danh sách toàn bộ các emulator đang chạy và trạng thái.
     - `POST /api/instances`: Tạo hoặc đăng ký một máy ảo mới.
     - `POST /api/instances/:id/start`: Khởi chạy instance cụ thể.
     - `POST /api/instances/:id/stop`: Dừng instance.
     - `POST /api/instances/:id/restart`: Khởi động lại instance.
     - `GET /api/instances/:id/metrics`: Lấy thông số CPU/RAM tức thời.
     - `GET /api/adrs`: Trả về danh sách và nội dung các file ADR để phục vụ học tập trên UI.
2. **WebSocket & Cập nhật thời gian thực:**
   - Cài đặt WebSocket Server (dùng thư viện `ws` hoặc `socket.io`).
   - Lắng nghe sự kiện từ Python Core Engine và broadcast trạng thái (trạng thái giả lập thay đổi, log console mới, cảnh báo tài nguyên) tới các client đang kết nối.
3. **Bộ điều phối tiến trình (Process Orchestrator & IPC):**
   - Sử dụng `child_process` (spawn/exec) hoặc Unix Socket để gọi các tác vụ Python Core một cách bất đồng bộ không gây nghẽn Event Loop.
   - Xử lý cơ chế tự phục hồi (Auto-restart khi tiến trình con bị lỗi đột ngột).
   - Quản lý hàng đợi tác vụ (Job queue / Task manager) cho các thao tác tốn thời gian như tạo máy ảo hàng loạt hoặc khởi động đồng loạt.
4. **CI/CD & DevOps:**
   - Xây dựng GitHub Actions workflow (`.github/workflows/ci.yml`) tự động chạy test Python (`pytest`), test Node.js, và kiểm tra lint khi có Pull Request.

#### B. Sản phẩm bàn giao (Deliverables):
- Thư mục mã nguồn backend Node.js (`server/`):
  - `app.js` / `index.js`: Điểm vào của server với cấu trúc middleware tiêu chuẩn.
  - `routes/instances.js`, `routes/adrs.js`: API endpoints.
  - `services/pythonBridge.js`: Xử lý giao tiếp 2 chiều với Python Core qua IPC.
  - `services/websocketHub.js`: Quản lý kết nối và phát tin WebSocket.
- Cập nhật `package.json` với scripts: `npm start`, `npm run dev`, `npm test`.
- File cấu hình CI/CD `.github/workflows/ci.yml`.
- Tài liệu tài liệu hóa API (Postman Collection hoặc OpenAPI/Swagger spec).

#### C. Nguồn tài liệu tham khảo cho Khoa:
1. **Node.js & Xử lý Tiến trình Con (Child Processes):**
   - *Node.js Child Process Official Docs*: [https://nodejs.org/api/child_process.html](https://nodejs.org/api/child_process.html)
   - *Node.js IPC Communication Techniques*: [https://nodejs.org/api/net.html](https://nodejs.org/api/net.html)
   - *Node.js Best Practices Repository*: [https://github.com/goldbergyoni/nodebestpractices](https://github.com/goldbergyoni/nodebestpractices)
2. **WebSocket & Real-time Communication:**
   - *WS: A fast WebSocket client & server library*: [https://github.com/websockets/ws](https://github.com/websockets/ws)
   - *Socket.IO Documentation*: [https://socket.io/docs/v4/](https://socket.io/docs/v4/)
   - *RFC 6455 - The WebSocket Protocol*: [https://datatracker.ietf.org/doc/html/rfc6455](https://datatracker.ietf.org/doc/html/rfc6455)
3. **CI/CD & Testing:**
   - *GitHub Actions Documentation*: [https://docs.github.com/en/actions](https://docs.github.com/en/actions)
   - *Supertest (HTTP Assertions)*: [https://github.com/ladjs/supertest](https://github.com/ladjs/supertest)

---

### PHẦN 3: CHƯƠNG — FRONTEND ENGINEER & INTERACTIVE DASHBOARD LEAD
*Phụ trách: Giao diện Web Dashboard, Trực quan hóa dữ liệu thời gian thực, Tương tác người dùng & Chuyên mục Giáo dục ADR.*

#### A. Trách nhiệm chính:
1. **Nâng cấp Giao diện Web (`index.html`, `css/`, `js/`):**
   - Tái cấu trúc file `index.html` hiện tại thành một ứng dụng quản lý giả lập hiện đại (Modern Multi-Emulator Dashboard).
   - Thiết kế giao diện theo phong cách Dark Mode chuyên nghiệp (phù hợp với các công cụ phát triển phần mềm và giả lập), đảm bảo tính phản hồi (Responsive design).
2. **Phát triển các phân hệ giao diện chính:**
   - **Bảng điều khiển tổng quan (Overview Metric Cards):** Hiển thị số lượng giả lập đang chạy / dừng / lỗi, tổng CPU/RAM sử dụng.
   - **Lưới quản lý giả lập (Emulator Grid Cards / Table View):**
     - Hiển thị từng instance (Tên, ID, Cổng/Port, Độ phân giải, Trạng thái: Idle, Running, Starting, Error).
     - Nút thao tác nhanh trên từng instance: Start, Stop, Reboot, Snapshot, Delete.
     - Khung thao tác hàng loạt: "Khởi động tất cả", "Dừng tất cả", "Đồng bộ hóa thao tác".
   - **Cửa sổ tương tác màn hình & Log (Live Stream / Mock Screen & Terminal Viewer):**
     - Vùng hiển thị mô phỏng màn hình thiết bị (khung canvas hoặc hình ảnh trực tiếp từ giả lập).
     - Hộp thoại hiển thị log thời gian thực (Console log viewer) có chức năng lọc log theo instance.
   - **Chuyên mục Giáo dục ADR (Interactive ADR Learning Portal):**
     - Tab riêng biệt trên giao diện liệt kê danh sách các ADR của dự án.
     - Hiển thị trực quan nội dung quyết định kiến trúc, lý do chọn giải pháp, ưu/nhược điểm để người dùng học tập ngay trên web.
3. **Tích hợp phía Client (Client-Side Logic):**
   - Viết module JavaScript (`dashboard.js`, `socketClient.js`, `adrViewer.js`) theo chuẩn ES6 Modules.
   - Kết nối với REST API của Khoa để lấy dữ liệu ban đầu.
   - Lắng nghe WebSocket để cập nhật giao diện mượt mà không cần reload trang.
4. **Trải nghiệm người dùng (UX):**
   - Xử lý thông báo Toast thông tin/lỗi (Toast Notifications).
   - Modal popup cấu hình giả lập (Resolution, DPI, RAM allocation).

#### B. Sản phẩm bàn giao (Deliverables):
- Bộ file giao diện người dùng hoàn thiện (`public/` hoặc `frontend/`):
  - `index.html`: Cấu trúc semantic HTML5 chuẩn accessibility.
  - `css/main.css`: Thiết kế hệ thống biến màu sắc, flexbox/grid layout, animation.
  - `js/app.js`: Quản lý state của frontend.
  - `js/websocket.js`: Xử lý kết nối và cập nhật DOM theo thời gian thực.
  - `js/adrViewer.js`: Render markdown / format của các tài liệu ADR.
- Tài liệu Hướng dẫn Sử dụng Giao diện (User Guide) tích hợp ngay trên Web hoặc file markdown kèm ảnh chụp minh họa.

#### C. Nguồn tài liệu tham khảo cho Chương:
1. **Thiết kế UI/UX Dashboard:**
   - *Dashboard Design Patterns & Guidelines*: [https://www.nngroup.com/articles/dashboards-preattentive/](https://www.nngroup.com/articles/dashboards-preattentive/)
   - *TailwindCSS / Modern CSS Grid & Flexbox Guide (CSS-Tricks)*: [https://css-tricks.com/snippets/css/complete-guide-grid/](https://css-tricks.com/snippets/css/complete-guide-grid/)
   - *Lucide Icons / Heroicons (Icon set cho dashboard)*: [https://lucide.dev/](https://lucide.dev/)
2. **HTML5 Canvas, WebSockets & UI Streaming:**
   - *MDN WebSocket API Client Guide*: [https://developer.mozilla.org/en-US/docs/Web/API/WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
   - *HTML5 Canvas Optimization & Rendering*: [https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
   - *Marked.js (Thư viện nhẹ parse Markdown ADR hiển thị trên web)*: [https://marked.js.org/](https://marked.js.org/)
3. **Web GUI for Devices / Remote Screen Control (Mẫu tham khảo):**
   - *scrcpy (Open-source Android Screen Copy)*: [https://github.com/Genymobile/scrcpy](https://github.com/Genymobile/scrcpy)
   - *ws-scrcpy (Web-based scrcpy client)*: [https://github.com/NetrisTV/ws-scrcpy](https://github.com/NetrisTV/ws-scrcpy)

---

## 3. LỘ TRÌNH TRIỂN KHAI & MỐC THỜI GIAN (ROADMAP - 4 SPRINTS / 4 TUẦN)

| Tuần / Sprint | Nhiệm vụ của Trung (Core & ADR) | Nhiệm vụ của Khoa (Backend Node.js) | Nhiệm vụ của Chương (Frontend UI) | Kết quả chung (Milestone) |
| :--- | :--- | :--- | :--- | :--- |
| **Tuần 1: Khởi động & Chuẩn hóa** | - Thiết lập kiến trúc & viết ADR-001, ADR-002.<br>- Định nghĩa cấu trúc data model cho Instance. | - Setup dự án Node.js với Express/Fastify.<br>- Định nghĩa tài liệu đặc tả API (OpenAPI/Swagger). | - Phác thảo Wireframe Dashboard.<br>- Dựng layout HTML/CSS ban đầu với theme Dark Mode. | **M1:** Thống nhất giao thức kết nối & Cấu trúc dự án. |
| **Tuần 2: Xây dựng Module lõi** | - Viết `instance_manager.py` (Start, Stop, Status).<br>- Tích hợp `metrics_collector.py`. | - Xây dựng RESTful API CRUD cho instances.<br>- Xây dựng module IPC kết nối với Python CLI/Socket. | - Tạo các Card hiển thị trạng thái từng emulator.<br>- Dựng Modal cấu hình tham số máy ảo. | **M2:** API và Core Engine hoạt động độc lập có Unit Tests. |
| **Tuần 3: Tích hợp thời gian thực** | - Hoàn thiện ADR-003, ADR-004.<br>- Xử lý cơ chế streaming event & log từ Python. | - Cài đặt WebSocket Server.<br>- Broadcast trạng thái và log từ Python sang Client. | - Tích hợp WebSocket Client.<br>- Xây dựng Live Terminal Viewer & Module hiển thị ADR. | **M3:** Điều khiển từ Web -> Node.js -> Python phản hồi tức thì. |
| **Tuần 4: Kiểm thử, Tối ưu & Bàn giao** | - Chạy benchmark tài nguyên đa instance.<br>- Viết báo cáo kỹ thuật & hoàn thiện ADRs. | - Tối ưu hoá xử lý đa tiến trình.<br>- Hoàn thiện CI/CD GitHub Actions. | - Tối ưu UX, hoàn thiện Toast, responsive design.<br>- Hoàn thành Hướng dẫn sử dụng trên Web. | **M4:** Hệ thống hoàn chỉnh, demo mượt mà và đóng gói báo cáo. |

---

## 4. QUY TRÌNH PHỐI HỢP & NGUYÊN TẮC LÀM VIỆC NHÓM

### 4.1. Quy chuẩn Git & Phân nhánh (Git Workflow)
- **Nhánh `main`:** Mã nguồn ổn định, đã kiểm thử thành công, chỉ hợp nhất thông qua Pull Request.
- **Nhánh tính năng (Feature Branches):**
  - Trung: `feat/core-instance-manager`, `docs/architecture-adrs`
  - Khoa: `feat/backend-api-routes`, `feat/websocket-ipc-bridge`
  - Chương: `feat/ui-dashboard-grid`, `feat/adr-interactive-viewer`
- **Quy tắc Commit (Conventional Commits):**
  - `feat:` thêm tính năng mới
  - `fix:` sửa lỗi
  - `docs:` thêm hoặc sửa tài liệu
  - `refactor:` cấu trúc lại mã nguồn mà không thay đổi chức năng
  - `test:` bổ sung hoặc sửa đổi bài test

### 4.2. Giao thức Tích hợp (Contract Definition)
1. **Format dữ liệu trạng thái một Emulator Instance (JSON):**
```json
{
  "id": "emu_01",
  "name": "Emulator-Instance-1",
  "type": "android_x86",
  "status": "RUNNING", // "STOPPED" | "STARTING" | "RUNNING" | "ERROR"
  "port": 5554,
  "metrics": {
    "cpuPercent": 14.5,
    "ramUsageMb": 1540,
    "fps": 60
  },
  "uptimeSeconds": 1820
}
```

2. **Format sự kiện WebSocket:**
```json
{
  "event": "INSTANCE_STATE_CHANGED",
  "timestamp": 1731139200000,
  "payload": {
    "instanceId": "emu_01",
    "oldStatus": "STARTING",
    "newStatus": "RUNNING",
    "message": "Instance booted successfully"
  }
}
```

---

## 5. DANH MỤC NGUỒN TÀI LIỆU THAM KHẢO TỔNG HỢP

1. **Về Kiến trúc Quyết định (ADR):**
   - Martin Fowler, *Architecture Decision Records*: https://martinfowler.com/articles/scaling-architecture-conversationally.html
   - Markdown Architectural Decision Records (MADR): https://adr.github.io/madr/
   - Bộ sưu tập mẫu ADR: https://github.com/joelparkerhenderson/architecture-decision-record
2. **Về Giả lập & Hệ thống Đa máy ảo:**
   - Android Studio Emulator Technical Guide: https://developer.android.com/studio/run/emulator
   - Android Open Source Project (AOSP) Virtualization: https://source.android.com/docs/core/virtualization
   - QEMU / KVM Architecture Overview: https://www.qemu.org/docs/master/
3. **Về Công nghệ Backend & Node.js:**
   - Node.js Official Documentation: https://nodejs.org/en/docs/
   - Express.js Security & Performance Best Practices: https://expressjs.com/en/advanced/best-practice-performance.html
   - WebSocket Specification (RFC 6455): https://datatracker.ietf.org/doc/html/rfc6455
4. **Về Python Core & Concurrency:**
   - Python Official Concurrency Docs: https://docs.python.org/3/library/concurrency.html
   - Pytest Official Documentation: https://docs.pytest.org/
   - Ruff Fast Python Linter: https://docs.astral.sh/ruff/
5. **Về Frontend & UI Dashboard:**
   - Mozilla Developer Network (MDN) Web Docs: https://developer.mozilla.org/
   - Web Performance & Canvas Rendering (web.dev): https://web.dev/
