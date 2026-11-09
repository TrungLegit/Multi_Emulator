# ADR-005: Chiến Lược Sử Dụng Browser Profile Chống Lag & Giao Thức Chrome DevTools Protocol (CDP)

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày quyết định:** 2026-11-09
- **Người đề xuất:** Trung & Nhóm Core Engine
- **Liên quan:** ADR-001, ADR-003, ADR-004

---

## 1. Bối cảnh (Context)
Dự án **Multi_Emulator** hướng tới việc chạy đồng thời từ 20 đến 50 phiên làm việc phục vụ các tác vụ mạng xã hội và web tự động (**TikTok, Facebook, YouTube, Google, Instagram**).

Giải pháp ban đầu sử dụng máy ảo Android QEMU tiêu tốn quá nhiều tài nguyên phần cứng (mỗi instance ngốn từ `1.5GB - 3GB RAM` và `15% - 25% CPU`). Khi chạy đồng loạt từ 10 máy trở lên, hệ thống dễ rơi vào tình trạng tràn RAM, nghẽn I/O ổ đĩa và giật lag nghiêm trọng, đòi hỏi máy chủ cấu hình máy trạm rất đắt tiền.

Trong khi đó, hầu hết các nền tảng mạng xã hội hiện đại đều cung cấp phiên bản Web / Mobile Web đầy đủ tính năng và tối ưu hóa tốt cho trình duyệt.

## 2. Quyết định (Decision)
Chúng tôi quyết định mở rộng kiến trúc hệ thống sang mô hình **Anti-Lag Multi-Browser Profile**:

1. **Cô Lập Hồ Sơ (Profile Isolation):**
   - Mỗi phiên làm việc là một profile trình duyệt độc lập (dựa trên nhân Chromium: Google Chrome, Microsoft Edge, Brave, Cốc Cốc) với thư mục dữ liệu `user-data-dir` riêng biệt.
2. **Bộ Cờ Tối Ưu Chống Lag (Anti-Lag Optimization Flags):**
   - `--mute-audio`: Tắt hoàn toàn giải mã âm thanh ngầm, giảm tải ngắt CPU và card âm thanh.
   - `--disable-smooth-scrolling`: Tắt cuộn mượt giả lập để giảm tải hàng đợi dựng hình (render queue) của GPU/CPU.
   - `--disk-cache-size=33554432` & `--media-cache-size=33554432`: Khóa bộ nhớ đệm ở mức 32MB để chống nghẽn I/O ổ đĩa khi chạy hàng chục profile.
   - `--disable-background-networking`, `--disable-background-timer-throttling`, `--disable-backgrounding-occluded-windows`: Ngăn Chrome gửi telemetry, update ngầm và tránh bị hệ điều hành giảm ưu tiên khi xếp chồng cửa sổ.
   - `--no-first-run`, `--no-default-browser-check`: Khởi chạy tức thì.
3. **Điều Khiển Đồng Bộ Bằng Chrome DevTools Protocol (CDP):**
   - Mỗi profile được mở một cổng gỡ lỗi từ xa (`--remote-debugging-port=9222, 9223...`).
   - Xây dựng module `CDPClient` chuẩn RFC 6455 bằng Python chuẩn không phụ thuộc thư viện nặng như Selenium hay Puppeteer.
   - Đồng bộ hóa các hành vi: Điều hướng trang (`Page.navigate` / `goto`), cuộn trang (`window.scrollBy`), click phần tử (`Runtime.evaluate`), điền văn bản và thực thi script.
4. **Tích Hợp Vào Sync Hub Hợp Nhất (Unified Adapter):**
   - Lớp `BrowserProfileAdapter` kế thừa `DeviceAdapter`, cho phép hệ thống Connector Hub điều khiển song song cả Browser Profiles lẫn Thiết bị Android trong cùng một Sync Group.

## 3. Hệ quả (Consequences)

### Ưu điểm:
- **Tiết kiệm tài nguyên vượt trội:** Giảm 85-90% dung lượng RAM (chỉ còn ~80MB - 150MB/profile) và gần 0% CPU khi nghỉ, giúp máy tính phổ thông chạy mượt mà 20 - 50 profiles.
- **Tốc độ khởi động tức thì:** Mở 10 profiles chỉ mất khoảng 2-3 giây.
- **Tự động xếp gạch (Tiling):** Tự động tính toán tọa độ để xếp các cửa sổ thành lưới giám sát chuyên nghiệp.

### Hạn chế & Giải pháp:
- Một số tác vụ yêu cầu app Android native sâu (như can thiệp cảm biến thiết bị) không chạy được trên web browser. Trong trường hợp đó, hệ thống tự động chuyển sang sử dụng thiết bị Android thông qua `ADBDeviceAdapter`.
