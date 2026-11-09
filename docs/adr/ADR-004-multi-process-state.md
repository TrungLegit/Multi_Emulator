# ADR-004: Quản Lý Đồng Bộ Đa Máy Ảo (Multi-Instance Sync Hub & Lightweight Profiles)

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày:** 2026-11-08
- **Tác giả:** Trung, Khoa, Chương

## 1. Bối cảnh (Context)
Mục tiêu cốt lõi của dự án là chạy mượt các ứng dụng mạng xã hội (Facebook, Instagram, TikTok, YouTube) và treo game trên hàng chục máy ảo cùng lúc giống như mô hình **Phone Farm Box**. Nếu mỗi máy ảo tiêu tốn 4GB RAM và xử lý lệnh tuần tự, máy chủ sẽ nhanh chóng quá tải và độ trễ giữa các màn hình sẽ rất lớn.

## 2. Quyết định (Decision)
1. **Cấu hình Siêu nhẹ (`src/core/profiles.py` & `adb_optimizer.py`):**
   - Giới hạn cấu hình Lite chỉ từ `768MB - 1024MB RAM`, độ phân giải `360x640` hoặc `540x960` (DPI 160-240), khóa FPS ở mức 24-30 FPS.
   - Tự động tắt toàn bộ hiệu ứng chuyển cảnh Android (`window_animation_scale 0.0`) và vô hiệu hóa các dịch vụ chạy ngầm không cần thiết qua ADB.
2. **Đồng bộ hóa đa luồng (`SyncGroup` & `ThreadPoolExecutor`):**
   - Gom các máy ảo vào một `SyncGroup` có 1 máy chủ đạo (`MASTER`) và các máy thành viên (`PEER`).
   - Khi người dùng thao tác trên màn hình Master hoặc bấm nút trên bảng điều khiển của Chương (Tap, Swipe, Mở App FB/IG/TikTok, Tối ưu RAM), lệnh được phát song song (`broadcast_command`) qua `ThreadPoolExecutor` tới toàn bộ các máy trong nhóm cùng lúc.

## 3. Hệ quả (Consequences)
- **Tích cực:** Giảm hơn 65% lượng RAM tiêu thụ trên mỗi instance so với giả lập truyền thống; toàn bộ dàn 21 máy trên lưới màn hình phản hồi đồng제 (synchronized) gần như tức thì.
