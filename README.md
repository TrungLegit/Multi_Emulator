# Multi_Emulator

> **Hệ Thống Điều Khiển Đồng Bộ Đa Profile Trình Duyệt & Giả Lập Siêu Nhẹ (Anti-Lag Multi-Browser & Emulator Sync Hub)**  
> *Phiên bản Giáo dục & Hồ sơ Quyết định Kiến trúc (Educational ADR Edition)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Node.js: 18+](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![Chromium: CDP](https://img.shields.io/badge/Protocol-Chrome_DevTools_Protocol-orange.svg)](https://chromedevtools.github.io/devtools-protocol/)

---

## 📌 Tổng Quan (Overview)

**Multi_Emulator** là nền tảng quản lý và điều khiển đồng bộ đa phiên làm việc (**Multi-Instance Sync Hub**) được phát triển nhằm giải quyết triệt để vấn đề giật lag và tràn tài nguyên khi chạy hàng loạt tác vụ mạng xã hội và web tự động (**TikTok, Facebook, YouTube, Google, Instagram, Web Games**).

Thay vì phải chạy các trình giả lập Android cồng kềnh tiêu tốn từ 2GB - 4GB RAM mỗi máy, **Multi_Emulator** áp dụng giải pháp **Multi-Browser Profile (Chromium-based: Chrome, Edge, Brave, Cốc Cốc)** kết hợp cùng các thiết bị Android sẵn có:
- **Tiết kiệm đến 90% tài nguyên:** Mỗi profile trình duyệt chỉ chiếm khoảng **80MB - 150MB RAM** và gần như **0% CPU khi nghỉ**, cho phép một máy tính thông thường chạy mượt mà từ **20 đến 50 profiles cùng lúc**.
- **Điều khiển đồng bộ thời gian thực (CDP Synchronization):** Mở link URL, cuộn trang, gõ chữ, click nút hoặc chạy script tự động hóa đồng loạt trên tất cả các profile chỉ với một lệnh duy nhất.
- **Trung tâm kết nối hợp nhất (Unified Sync Hub):** Tích hợp cả Profile Trình duyệt lẫn Máy ảo Android trong cùng một giao diện điều khiển.

---

## ⚡ Các Tính Năng Nổi Bật (Key Features)

1. **Bộ Cờ Tối Ưu Chống Lag (Anti-Lag Chromium Engine):**
   - Giới hạn bộ nhớ đệm ổ cứng tối đa `32MB/profile` (chống nghẽn I/O đĩa).
   - Tắt âm thanh ngầm (`--mute-audio`), tắt cuộn mượt (`--disable-smooth-scrolling`) giảm tải render GPU/CPU.
   - Vô hiệu hóa toàn bộ telemetry, tự cập nhật và tác vụ ngầm (`--disable-background-networking`, `--disable-sync`).
   - Tự động chia tọa độ và xếp gạch cửa sổ gọn gàng trên màn hình (Window Tiling).
2. **Đồng Bộ Hóa Hành Động Đa Nền Tảng (CDP & ADB Broadcaster):**
   - **Mở trang web đồng loạt:** `goto <url>` (TikTok, Facebook, YouTube...).
   - **Cuộn trang đồng loạt:** `scroll-down`, `scroll-up`, `scroll <dx> <dy>`.
   - **Click & Gõ chữ đồng loạt:** `click <selector>`, `type <text>`.
   - **Chạy JavaScript hàng loạt:** `eval <js_code>`.
   - Tương thích chéo với các lệnh cảm ứng Android (`input tap`, `input swipe`).
3. **Giao Diện Web Dashboard Hiện Đại (Phone Farm Matrix & Browser Sync Hub):**
   - Lưới hiển thị 21+ máy ảo / profiles trực quan.
   - Thanh tác vụ điều hướng 1-chạm (Quick Nav) và phát lệnh đồng bộ tức thì.
   - Giám sát trạng thái kết nối, RAM/CPU và Activity Log thời gian thực.
4. **Kiến Trúc Giáo Dục & Hồ Sơ Quyết Định Kiến Trúc (ADRs):**
   - Ghi nhận đầy đủ các bản ghi ADR từ ADR-001 đến ADR-005 trong thư mục `docs/adr/`.

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

- **Backend / Core Engine:** Python 3.10+ (Quản lý profile, tối ưu hóa cờ anti-lag, Client Chrome DevTools Protocol RFC 6455).
- **Orchestrator / Server:** Node.js 18+ (RESTful API, WebSocket Broadcaster, IPC Bridge).
- **Frontend / Dashboard:** HTML5, CSS3 Grid/Flexbox, Vanilla JavaScript (ES6 Modules, Realtime Event Stream).
- **Kiểm thử tự động:** `pytest`, `unittest`.

---

## 🚀 Hướng Dẫn Cài Đặt (Installation)

### Yêu cầu tiên quyết
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) & `npm`
- Một trình duyệt nền Chromium đã cài sẵn trên máy (Google Chrome, Microsoft Edge, Brave, hoặc Cốc Cốc)

### Các bước cài đặt
```bash
# 1. Clone repository
git clone https://github.com/TrungLegit/Multi_Emulator.git
cd Multi_Emulator

# 2. Khởi tạo môi trường ảo Python và cài đặt dependencies
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Cài đặt dependencies cho Node.js
npm install
```

---

## 📖 Hướng Dẫn Sử Dụng Nhanh (Quick Start)

### 1. Quản lý & Điều Khiển Bằng Dòng Lệnh (CLI)

```bash
# Tạo 3 profile trình duyệt tối ưu chống lag
python3 main.py profile-create --count 3

# Xem danh sách các profile và cổng kết nối CDP
python3 main.py profile-list

# Khởi chạy tất cả các profile (có giãn cách chống giật CPU)
python3 main.py profile-start --all --url "https://www.tiktok.com"

# Quét và kết nối toàn bộ profile vào Sync Hub
python3 main.py scan
python3 main.py connect --all

# Phát lệnh đồng bộ tới tất cả các profile:
# Mở link YouTube Shorts đồng loạt:
python3 main.py broadcast --cmd "goto https://www.youtube.com"

# Cuộn trang đồng loạt:
python3 main.py broadcast --cmd "scroll-down"

# Đóng tất cả profile khi hoàn thành:
python3 main.py profile-stop --all
```

### 2. Khởi Chạy Giao Diện Web Dashboard

```bash
npm start
```
Truy cập **`http://localhost:3000`** trên trình duyệt để sử dụng bảng điều khiển đồ họa:
- Bấm **"🔍 1. Scan Hub"** để quét các profile và thiết bị.
- Bấm **"🔗 2. Connect & Link All"** để gom vào nhóm đồng bộ.
- Nhập URL hoặc bấm các nút **TikTok / Facebook / YouTube** để mở và tương tác đồng thời trên tất cả các cửa sổ!

### 3. Chạy Kiểm Thử Tự Động (Run Tests)

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
# Hoặc dùng pytest:
pytest -v
```

---

## 👥 Phân Chia Vai Trò Nhóm (Team & Responsibilities)

Chi tiết kế hoạch triển khai 4 tuần và phân chia trách nhiệm được ghi nhận tại [**`PLAN.md`**](PLAN.md):

- **Trung (Core Architect & Browser Anti-Lag Engine Lead):** Quản lý cấu hình profile, bộ cờ tối ưu hóa chống lag, bộ điều khiển CDP Client và chuẩn hóa tài liệu ADR.
- **Khoa (Backend Orchestrator & API Gateway Lead):** Phát triển API RESTful Node.js, kênh truyền thông thời gian thực WebSocket, cầu nối IPC và hàng đợi tác vụ.
- **Chương (Frontend Lead & Phone Farm Matrix Dashboard):** Thiết kế giao diện lưới đa màn hình 7x3, thanh công cụ điều khiển đồng bộ và chuyên trang học tập kiến trúc ADR.

---

## 📄 Bản Quyền (License)

Dự án được phát hành theo giấy phép [MIT License](LICENSE).
