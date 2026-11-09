# ADR-003: Chiến Lược Trừu Tượng Hóa Bộ Điều Khiển Giả Lập (Adapter Pattern)

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày:** 2026-11-08
- **Tác giả:** Trung

## 1. Bối cảnh (Context)
Hệ thống `Multi_Emulator` cần điều khiển được cả các máy ảo thực tế (QEMU/Android-x86, LDPlayer, NoxPlayer, MEmu qua cổng TCP `5554-5584`, `62001`, `21503`) lẫn chế độ mô phỏng (Mock Phone Farm) phục vụ mục đích học tập, kiểm thử CI/CD và trình diễn giao diện khi máy tính không bật sẵn hàng chục máy ảo thật.

## 2. Quyết định (Decision)
Áp dụng mẫu thiết kế **Adapter Pattern** thông qua lớp trừu tượng `DeviceAdapter` (`src/core/device_adapter.py`) với 3 cài đặt cụ thể:
1. `ADBDeviceAdapter`: Quét thiết bị thật qua `adb devices -l` và dò cổng TCP cục bộ (`socket.connect_ex`).
2. `MockDeviceAdapter`: Giả lập các máy ảo Android siêu nhẹ phục vụ demo, kiểm thử tự động và hiển thị ma trận Phone Farm.
3. `CompositeDiscoveryAdapter`: Tự động ưu tiên thiết bị thật từ ADB/TCP; nếu không có thiết bị thật nào đang mở sẽ tự động chuyển sang `MockDeviceAdapter` (Fallback).

## 3. Lý do lựa chọn (Rationale)
- **Đa tương thích:** Có thể kết nối và đồng bộ cùng lúc nhiều loại giả lập khác nhau về chung một bảng điều khiển.
- **Trải nghiệm "Chạy ngay lập tức" (Zero-Config Demo):** Giảng viên, sinh viên hoặc người dùng clone repo từ GitHub về có thể chạy ngay giao diện Phone Farm Matrix với đầy đủ tính năng mà không bắt buộc phải tải file ISO Android hàng GB.
