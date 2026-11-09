# ADR-002: Chiến lược Tối ưu Hóa Tài nguyên (RAM, CPU, GPU) cho Tác vụ TikTok & Facebook

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày tạo:** 2026-11-09
- **Người phụ trách:** Trung & Nhóm Core Engine

---

## 1. Bối cảnh (Context)

Tác vụ mục tiêu của hệ thống là **xem TikTok và lướt Facebook**. Đặc điểm kỹ thuật của 2 ứng dụng này:
- Không yêu cầu dựng hình 3D phức tạp (như PUBG hay Genshin Impact).
- Chủ yếu sử dụng **2D UI Rendering**, **Giải mã video luồng (Video Decoding H.264/VP9)** và **Kết nối mạng HTTP/QUIC**.
- Tuy nhiên, cả TikTok và Facebook đều có cơ chế tải trước (preload) nhiều video và chạy nhiều dịch vụ ngầm gây tốn RAM nếu không được giới hạn.

## 2. Quyết định (Decision)

Chúng tôi áp dụng bộ **Profile Tối ưu Hóa 3 Lớp (3-Layer Optimization Profile)**:

### Lớp 1: Cấu hình Phần cứng Máy ảo (VM Hardware Profile)
- **Độ phân giải (Resolution) & DPI:** Hạ xuống `540x960` (qHD) với `240 DPI` (hoặc `360x640 @ 160 DPI` ở chế độ siêu tiết kiệm). Giảm 75% số điểm ảnh cần render so với FullHD `1080x1920`, giúp giảm tải GPU và băng thông mạng (TikTok/FB tự động trả về video 480p/540p nhẹ hơn).
- **Giới hạn Khung hình (Frame Rate Cap):** Khóa ở mức `30 FPS` (đủ mượt cho video ngắn và cuộn trang, giảm 50% chu kỳ render so với 60 FPS).
- **Bộ nhớ RAM:** Cấp phát `1024 MB` (Standard Social) hoặc `768 MB` (Ultra-Lite) kết hợp `zRAM` nén bộ nhớ trong nhân Android.
- **CPU:** Cấp `2 vCPU cores` với cờ `-cpu host` để truyền thẳng tập lệnh giải mã SIMD (SSE4.2, AVX2) giúp giải mã video cực nhanh.

### Lớp 2: Tinh chỉnh Hệ điều hành Android (`build.prop` & `settings` qua ADB)
- **Tắt toàn bộ hiệu ứng chuyển cảnh (Animations):**
  - `window_animation_scale = 0`
  - `transition_animation_scale = 0`
  - `animator_duration_scale = 0`
- **Giới hạn tiến trình chạy ngầm (Background Process Limit):**
  - Đặt `max_cached_processes = 4` (ngăn các app khác chiếm RAM).
- **Tối ưu máy ảo Dalvik/ART (`dalvik.vm.*`):**
  - `dalvik.vm.heapsize=256m`
  - `dalvik.vm.heapgrowthlimit=128m`
  - `ro.config.low_ram=true` (Kích hoạt chế độ Android Go / Low-RAM giúp Facebook & TikTok tự chuyển sang chế độ tiết kiệm tài nguyên).

### Lớp 3: Tự động Debloat (Gỡ bỏ dịch vụ thừa qua ADB)
Khi máy ảo khởi chạy lần đầu, Python Engine tự động chạy script vô hiệu hóa (`pm disable-user`):
- Dịch vụ in ấn (`com.android.bips`, `com.android.printspooler`)
- Hình nền động (`com.android.wallpapercropper`, `com.android.dreams.basic`)
- Kho ứng dụng và dịch vụ đồng bộ ngầm không cần thiết, ưu tiên dùng **Facebook Lite** / **TikTok Lite** hoặc bản chuẩn đã tắt tự phát video ngầm.

## 3. Kết quả Kỳ vọng (Benchmarks Mục tiêu)

| Thông số | Giả lập Mặc định (Chưa tối ưu) | Multi_Emulator (Sau tối ưu) | Mức tiết kiệm |
| :--- | :--- | :--- | :--- |
| **RAM mỗi máy ảo** | ~2,500 MB | **768 MB - 1,024 MB** | **~60% - 70%** |
| **CPU khi lướt TikTok** | 18% - 25% | **4% - 8%** | **~65%** |
| **Dung lượng đĩa / máy** | 4 GB - 8 GB | **300 MB - 600 MB (Overlay)** | **~85%** |
| **Độ phân giải** | 1080x1920 (60 FPS) | **540x960 (30 FPS)** | **Giảm 75% tải GPU** |
