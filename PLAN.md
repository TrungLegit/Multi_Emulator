# KẾ HOẠCH PHÁT TRIỂN DỰ ÁN MULTI_EMULATOR
**Định Hướng Mới: Hệ Thống Điều Khiển Đồng Bộ Đa Profile Trình Duyệt & Giả Lập Siêu Nhẹ (Anti-Lag Multi-Browser & Emulator Sync Hub)**

---

## 1. TỔNG QUAN & BỐI CẢNH CHUYỂN ĐỔI CHIẾN LƯỢC (PROJECT PIVOT)

### 1.1. Lý do chuyển đổi định hướng
Ở giai đoạn đầu, dự án tiếp cận theo hướng dựng máy ảo Android QEMU toàn phần. Tuy nhiên, qua khảo sát thực tế:
- Máy ảo Android toàn phần (Full Virtual Machine) tiêu tốn từ `1.5GB - 3GB RAM` và `15% - 25% CPU` cho mỗi instance. Trên một máy tính phổ thông (RAM 16GB, CPU 4-8 cores), việc chạy đồng thời từ 10 - 20 máy ảo dẫn tới quá tải, tràn RAM và giật lag nghiêm trọng.
- Phần lớn các tác vụ người dùng mong muốn thực hiện (lướt **TikTok**, tương tác **Facebook**, xem **YouTube Shorts**, nuôi tài khoản, tự động hóa web) hoàn toàn có thể chạy mượt mà trực tiếp trên **các Profile Trình duyệt Độc lập (Chromium-based: Chrome, Edge, Brave, Cốc Cốc)** với phiên bản Mobile Web / Web App.

### 1.2. Định hướng mới của Multi_Emulator
Hệ thống chuyển đổi sang mô hình **Multi-Profile Browser & Lightweight Emulator Sync Hub**:
1. **Tiết kiệm tài nguyên triệt để (Anti-Lag Profile Engine):** Mỗi profile trình duyệt được cách ly hoàn toàn dữ liệu (`user-data-dir`) và chạy với bộ cờ tối ưu hóa đặc biệt (`--mute-audio`, `--disk-cache-size=32MB`, `--disable-smooth-scrolling`, tắt background telemetry). Bộ nhớ tiêu tốn chỉ khoảng **80MB - 150MB RAM** và gần như **0% CPU khi rảnh**, cho phép một máy tính chạy đồng thời từ **20 đến 50 profiles mượt mà**.
2. **Điều khiển đồng bộ thời gian thực (Chrome DevTools Protocol - CDP Synchronization):** Gửi các thao tác giống nhau (Mở URL, cuộn trang, click phần tử, gõ văn bản, chạy JavaScript) đồng loạt tới tất cả các profile hoặc thiết bị chỉ với một cú click hoặc một dòng lệnh.
3. **Trung tâm kết nối hợp nhất (Unified Connector Hub):** Kiến trúc của nhóm cho phép quản lý và đồng bộ song song cả **Browser Profiles** lẫn **Android Emulators** (qua ADB / TCP) trong cùng một Sync Hub.

```
+-----------------------------------------------------------------------------------+
|                        TẦNG TRÌNH DIỄN & GIAO DIỆN (CHƯƠNG)                        |
|        Modern Web Dashboard: Phone Farm Matrix (7x3) + Browser Sync Controller    |
|   - Bảng điều khiển đồng bộ URL / Action      - Lưới hiển thị 21+ Profile/Màn hình |
|   - Nút thao tác hàng loạt (Scroll, Click)     - Quản lý tài nguyên & Terminal Log  |
+-----------------------------------------^-----------------------------------------+
                                          | (RESTful API & Real-time WebSocket)
+-----------------------------------------v-----------------------------------------+
|                    TẦNG ĐIỀU PHỐI & API GATEWAY (KHOA)                            |
|                     Node.js Backend Orchestrator & Server                         |
|   - RESTful API (/api/browser/*, /api/connector/*)                               |
|   - Real-time WebSocket Broadcaster & Event Hub                                   |
|   - Python IPC Bridge (child_process) & Task Queue Staggering                     |
+-----------------------------------------^-----------------------------------------+
                                          | (CLI / JSON IPC)
+-----------------------------------------v-----------------------------------------+
|                  TẦNG ĐỘNG CƠ LÕI & ĐIỀU KHIỂN ĐỒNG BỘ (TRUNG)                    |
|                        Python 3.10+ Core Sync Hub Engine                          |
|   - BrowserProfileManager: Quản lý vòng đời profile & bộ cờ Anti-Lag               |
|   - BrowserProfileAdapter & CompositeDiscoveryAdapter: Nhận diện CDP & ADB        |
|   - Synchronized Action Translator: goto, scroll, click, type, eval JS            |
|   - Hồ sơ Quyết định Kiến trúc (ADR-001 đến ADR-005)                              |
+-----------------------------------------------------------------------------------+
```

---

## 2. PHÂN CHIA NHIỆM VỤ CHI TIẾT CHO 3 THÀNH VIÊN

---

### PHẦN 1: TRUNG — CORE ARCHITECT & BROWSER ANTI-LAG ENGINE LEAD
*Phụ trách: Kiến trúc hệ thống, Động cơ Profile trình duyệt chống lag, Bộ chuyển đổi CDP và Chuẩn hóa ADR.*

#### A. Nhiệm vụ cụ thể:
1. **Nâng cấp Động cơ Profile Trình duyệt (`src/core/browser_profile.py`):**
   - Hoàn thiện cơ chế tự động nhận diện các trình duyệt có sẵn trên máy chủ (Google Chrome, Microsoft Edge, Brave, Chromium, Cốc Cốc) trên cả Windows và Linux.
   - Tối ưu bộ cờ Chromium Anti-Lag: giới hạn cache đĩa (32MB), tắt âm thanh, tắt smooth scrolling, tắt background networking, cô lập `user-data-dir`.
   - Tính toán thuật toán xếp gạch tự động (Window Tiling): tự động chia tọa độ `x, y` và kích thước `width, height` để khi mở 10-20 cửa sổ, các màn hình tự xếp khít nhau như một màn hình giám sát trung tâm.
2. **Bộ điều khiển Chrome DevTools Protocol (`CDPClient`):**
   - Viết client WebSocket/HTTP chuẩn theo RFC 6455 sử dụng thư viện chuẩn của Python, không phụ thuộc thư viện bên ngoài nặng nề như Selenium hay Puppeteer.
   - Hỗ trợ các hành động đồng bộ:
     - `navigate(url)`: Mở trang web (TikTok, Facebook, YouTube, Google...).
     - `scroll(dx, dy)`: Cuộn trang mượt mà hoặc tức thì.
     - `click_element(selector)`: Bấm nút theo CSS Selector.
     - `type_text(text, selector)`: Điền văn bản vào ô tìm kiếm hoặc form đăng nhập.
     - `execute_js(script)`: Chạy JavaScript tùy biến để cào dữ liệu hoặc tự động tương tác.
3. **Mở rộng Adapter & Sync Hub (`src/core/browser_adapter.py` & `device_adapter.py`):**
   - Kết nối `BrowserProfileAdapter` vào `CompositeDiscoveryAdapter` để lệnh `scan` và `connect --all` gom cả Profile Trình duyệt và Máy ảo Android vào chung một `SyncGroup`.
   - Hỗ trợ biên dịch chéo lệnh: các lệnh cảm ứng của Android như `input tap <x> <y>` và `input swipe <x1> <y1> <x2> <y2>` được tự động ánh xạ sang tọa độ click và cuộn trang trên trình duyệt.
4. **Tài liệu Quyết định Kiến trúc (ADR):**
   - Bổ sung `docs/adr/ADR-005-browser-profile-anti-lag-cdp.md` ghi nhận quyết định chuyển đổi sang kiến trúc Browser Profile và giao thức CDP.

#### B. Sản phẩm bàn giao (Deliverables):
- `src/core/browser_profile.py`: Quản lý profile, cờ chống lag và client CDP.
- `src/core/browser_adapter.py`: Adapter kết nối vào Sync Hub.
- `docs/adr/ADR-005-browser-profile-anti-lag-cdp.md`.
- Bộ Unit Test `tests/test_browser_sync.py` đạt tỷ lệ pass 100%.

#### C. Nguồn tài liệu tham khảo cho Trung:
- **Chrome DevTools Protocol (CDP) Official Docs:** [https://chromedevtools.github.io/devtools-protocol/](https://chromedevtools.github.io/devtools-protocol/)
- **Danh mục Cờ Chromium Switches (Peter Beverloo):** [https://peter.sh/experiments/chromium-command-line-switches/](https://peter.sh/experiments/chromium-command-line-switches/)
- **RFC 6455 - The WebSocket Protocol:** [https://datatracker.ietf.org/doc/html/rfc6455](https://datatracker.ietf.org/doc/html/rfc6455)
- **Kiến trúc Trình duyệt Antidetect & Multi-login (Nghiên cứu):** [https://adspower.com/blog/browser-automation-with-puppeteer-selenium](https://adspower.com/blog/browser-automation-with-puppeteer-selenium)

---

### PHẦN 2: KHOA — BACKEND ORCHESTRATOR & API GATEWAY LEAD
*Phụ trách: Server Node.js, RESTful API, Real-time WebSocket Hub, Cầu nối IPC & Quản lý Hàng đợi tác vụ.*

#### A. Nhiệm vụ cụ thể:
1. **Nâng cấp Cầu nối IPC (`server/services/pythonBridge.js`):**
   - Bổ sung các hàm gọi xuống Python CLI với định dạng JSON:
     - `createBrowserProfiles(count, prefix, browserType)`
     - `startBrowserProfile(id, url)`
     - `stopBrowserProfile(id)`
     - `listBrowserProfiles()`
     - `syncBrowserAction(command, groupId)`
2. **Xây dựng RESTful API trong `index.js` & `server/routes/`:**
   - `GET /api/browser/profiles`: Lấy danh sách profiles kèm trạng thái online/offline và cổng CDP.
   - `POST /api/browser/profiles/create`: Tạo thêm 1 hoặc N profile mới.
   - `POST /api/browser/profiles/start`: Khởi chạy 1 hoặc toàn bộ profiles.
   - `POST /api/browser/profiles/stop`: Đóng 1 hoặc toàn bộ profiles.
   - `POST /api/browser/sync`: Phát lệnh đồng bộ tới tất cả profiles (navigate, scroll, click, type, eval).
3. **Cơ chế Khởi chạy Giãn cách (Staggered Launch Queue):**
   - Xây dựng hàng đợi khởi chạy: Khi người dùng yêu cầu mở 20 profile cùng lúc, server kích hoạt lần lượt cách nhau 250ms - 400ms để tránh hiện tượng CPU spike làm nghẽn máy.
4. **WebSocket Real-time Broadcaster (`server/services/websocketHub.js`):**
   - Truyền phát các sự kiện thay đổi trạng thái của profile và log thực thi thao tác đồng bộ xuống giao diện người dùng theo thời gian thực.
5. **Kiểm thử API & CI/CD Pipeline:**
   - Viết bài test tích hợp cho API Node.js và cấu hình GitHub Actions workflow.

#### B. Sản phẩm bàn giao (Deliverables):
- `server/services/pythonBridge.js` & `server/routes/browserProfiles.js`.
- Bổ sung các routes hoàn chỉnh trong `index.js`.
- Kênh WebSocket broadcast trạng thái profiles.
- Tài liệu kiểm thử API (Postman Collection hoặc cURL test script).

#### C. Nguồn tài liệu tham khảo cho Khoa:
- **Node.js Child Process Documentation:** [https://nodejs.org/api/child_process.html](https://nodejs.org/api/child_process.html)
- **Node.js Concurrency & Asynchronous Patterns:** [https://nodejs.org/en/docs/guides/event-loop-timers-and-nexttick/](https://nodejs.org/en/docs/guides/event-loop-timers-and-nexttick/)
- **WebSocket Library for Node.js (`ws`):** [https://github.com/websockets/ws](https://github.com/websockets/ws)
- **Design Patterns for Micro-services IPC:** [https://microservices.io/patterns/communication-style/messaging.html](https://microservices.io/patterns/communication-style/messaging.html)

---

### PHẦN 3: CHƯƠNG — FRONTEND LEAD & MULTI-PROFILE MATRIX DASHBOARD
*Phụ trách: Giao diện Web Dashboard, Lưới Phone Farm Matrix & Browser Sync Control Bar, Trực quan hóa dữ liệu.*

#### A. Nhiệm vụ cụ thể:
1. **Nâng cấp Giao diện Dashboard (`index.html` và `public/`):**
   - Ghép nối phân hệ **Browser Profile Sync Matrix** song song với Phone Farm Matrix 7x3 sẵn có.
   - Hiển thị danh thiếp (Card View) của từng profile trình duyệt:
     - Biểu tượng trình duyệt (Chrome, Edge, Brave), ID profile, Cổng CDP, Trạng thái (Running / Stopped / Synced).
     - Nút thao tác nhanh trên từng profile: Khởi chạy, Đóng, Mở link riêng.
2. **Thanh Điều Khiển Tác Vụ Đồng Bộ (Synchronized Control Bar):**
   - Ô nhập link URL thông minh + nút **"Mở trên tất cả Profiles"** (Goto All).
   - Bộ nút truy cập nhanh 1-chạm: **TikTok**, **Facebook**, **YouTube**, **Google**.
   - Bộ phím tắt điều khiển đồng bộ:
     - ⬇️ **Cuộn xuống (Scroll Down)**: Tự động cuộn feed video TikTok / Reels Facebook.
     - ⬆️ **Cuộn lên (Scroll Up)**.
     - 🔄 **Làm mới tất cả (Reload All)**.
     - ⌨️ **Gõ chữ đồng loạt (Sync Typing)**.
     - 🖱️ **Bấm theo Selector (Click Selector)**.
3. **Modal Quản lý & Tạo Nhanh Profile:**
   - Nút **"Tạo nhanh N Profiles"**: Cho phép người dùng nhập số lượng (ví dụ 5, 10, 20 profile) để hệ thống tự động sinh cấu hình và cổng CDP.
4. **Tối ưu hóa Giao diện & Hiển thị Thời gian Thực:**
   - Lắng nghe sự kiện từ WebSocket của Khoa để cập nhật trạng thái các profile không cần F5.
   - Bảng log hệ thống hiển thị chi tiết kết quả broadcast lệnh trên từng profile.

#### B. Sản phẩm bàn giao (Deliverables):
- File `public/index.html` và `index.html` hoàn thiện với Tab Browser Sync Hub.
- Module JavaScript frontend: `public/js/browserSync.js` hoặc tích hợp vào `public/js/app.js`.
- Bổ sung hướng dẫn sử dụng Browser Sync trong `docs/USER_GUIDE.md`.

#### C. Nguồn tài liệu tham khảo cho Chương:
- **Nielsen Norman Group - Dashboard Design Patterns:** [https://www.nngroup.com/articles/dashboards-preattentive/](https://www.nngroup.com/articles/dashboards-preattentive/)
- **CSS Grid Layout Guide (CSS-Tricks):** [https://css-tricks.com/snippets/css/complete-guide-grid/](https://css-tricks.com/snippets/css/complete-guide-grid/)
- **Web App Responsive Architecture & Performance (web.dev):** [https://web.dev/learn/design/](https://web.dev/learn/design/)
- **Giao diện Mẫu Antidetect Browser (Tham khảo UX AdsPower / Gologin):** [https://gologin.com/](https://gologin.com/)

---

## 3. LỘ TRÌNH TRIỂN KHAI 4 TUẦN (SPRINT ROADMAP)

| Tuần / Sprint | Trung (Core & Anti-Lag Engine) | Khoa (Backend & IPC Gateway) | Chương (Frontend & Dashboard) | Kết quả chung (Milestone) |
| :--- | :--- | :--- | :--- | :--- |
| **Tuần 1: Nền tảng Profile & Cờ Anti-Lag** | - Viết `browser_profile.py` với bộ cờ anti-lag.<br>- Tự động phát hiện Chrome/Edge/Brave.<br>- Viết ADR-005. | - Nâng cấp `pythonBridge.js` hỗ trợ profile commands.<br>- Dựng các route RESTful `/api/browser/*`. | - Thiết kế thanh điều khiển Browser Sync Bar.<br>- Dựng layout card cho Browser Profiles. | **M1:** Tạo và mở được nhiều profile trình duyệt siêu nhẹ qua CLI và API. |
| **Tuần 2: Điều khiển Đồng bộ qua CDP** | - Hoàn thiện `CDPClient` (RFC 6455).<br>- Hỗ trợ goto, scroll, click, type, eval.<br>- Kết nối vào `CompositeDiscoveryAdapter`. | - Xây dựng cơ chế Staggered Launch Queue.<br>- Viết API `/api/browser/sync` xử lý broadcast song song. | - Hoàn thiện các nút thao tác nhanh (TikTok, FB, Scroll, Type).<br>- Tích hợp Modal tạo nhanh N profiles. | **M2:** Broadcast 1 lệnh làm tất cả profile mở web và cuộn trang đồng thời. |
| **Tuần 3: Tích hợp WebSocket & Matrix View** | - Biên dịch chéo lệnh cảm ứng (tap/swipe) từ Android sang Browser.<br>- Viết Unit Test cho toàn bộ adapter. | - Hoàn thiện WebSocket Hub phát sóng sự kiện thời gian thực.<br>- Xử lý bắt lỗi khi có profile bị crash. | - Tích hợp WebSocket client cập nhật live.<br>- Ghép hoàn chỉnh vào Dashboard chính. | **M3:** Giao diện Web điều khiển mượt mà cả Browser Profiles lẫn Phone Farm. |
| **Tuần 4: Stress Test, Tối ưu & Bàn giao** | - Stress test 20 - 30 profiles đồng thời trên máy tính phổ thông.<br>- Đo đạc lượng RAM/CPU tiết kiệm được. | - Hoàn thiện tài liệu API và CI/CD GitHub Actions.<br>- Đóng gói cấu hình chạy một lệnh. | - Tối ưu UX/UI, hiệu ứng phản hồi, hoàn thành tài liệu `USER_GUIDE.md`. | **M4:** Hệ thống hoàn chỉnh, chạy cực nhẹ, không giật lag, sẵn sàng báo cáo. |

---

## 4. QUY TRÌNH PHỐI HỢP & NGUYÊN TẮC LÀM VIỆC NHÓM

### 4.1. Quy chuẩn Phân nhánh Git (Git Workflow)
- Nhánh `main`: Mã nguồn đã qua kiểm thử tự động (`pytest` và `npm test` đều pass).
- Các nhánh tính năng đang hoạt động:
  - `feat/browser-sync-hub`: Động cơ đồng bộ đa profile trình duyệt chống lag.
  - `feat/ui-dashboard-grid`: Giao diện Phone Farm Matrix và Dashboard.
  - `feat/backend-api-routes`: Hệ thống API server và WebSocket.
- Quy tắc Commit: Tuân thủ Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

### 4.2. Định dạng Hợp đồng Dữ liệu (JSON Contract)
Khi gọi lệnh đồng bộ broadcast, payload trả về có định dạng chuẩn:
```json
{
  "action": "profile_sync",
  "broadcast": {
    "groupId": "sync_hub_default",
    "command": "goto https://www.tiktok.com",
    "targetCount": 5,
    "results": [
      {
        "instanceId": "profile_01",
        "name": "Browser-Profile-01 (CHROME)",
        "port": 9222,
        "ok": true,
        "action": "navigate",
        "output": "[profile_01] Navigated to 'https://www.tiktok.com'"
      }
    ]
  }
}
```

---

## 5. TỔNG HỢP NGUỒN TÀI LIỆU THAM KHẢO

1. **Về Chrome DevTools Protocol & Chromium Switches:**
   - Chrome DevTools Protocol Viewer: https://chromedevtools.github.io/devtools-protocol/
   - The Chromium Projects - Command Line Flags: https://www.chromium.org/developers/how-tos/run-chromium-with-flags/
   - List of Chromium Command Line Switches: https://peter.sh/experiments/chromium-command-line-switches/
2. **Về Công nghệ Giao tiếp Thời gian Thực & Tự Động Hóa:**
   - RFC 6455 WebSocket Specification: https://datatracker.ietf.org/doc/html/rfc6455
   - Node.js Official Documentation: https://nodejs.org/en/docs/
   - WebSocket Library for Node.js (`ws`): https://github.com/websockets/ws
3. **Về Android ADB & Device Interoperability:**
   - Android Debug Bridge (ADB) User Guide: https://developer.android.com/tools/adb
   - Android Input Manager (`input tap`, `input swipe`): https://source.android.com/docs/core/interaction/input
4. **Về Thiết kế Giao diện Điều khiển Đa Thiết bị (UI/UX):**
   - Nielsen Norman Group - Designing Effective Dashboards: https://www.nngroup.com/articles/dashboards-preattentive/
   - CSS Grid Complete Guide: https://css-tricks.com/snippets/css/complete-guide-grid/
