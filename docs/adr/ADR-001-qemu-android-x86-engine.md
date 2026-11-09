# ADR-001: Kiến trúc Giả lập Android Siêu nhẹ dựa trên QEMU/WHPX/KVM

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày tạo:** 2026-11-09
- **Người phụ trách:** Trung & Nhóm Core Engine

---

## 1. Bối cảnh (Context)

Dự án **Multi_Emulator** cần xây dựng một động cơ giả lập Android cơ bản phục vụ mục đích học tập và chạy đa phiên (multi-instance) cho các tác vụ mạng xã hội nhẹ nhàng như **lướt Facebook, xem TikTok** trên máy chủ **Windows 10/11** (và tương thích Linux).

Các trình giả lập thương mại (BlueStacks, LDPlayer, Nox) thường đi kèm nhiều dịch vụ quảng cáo, gaming overlay, phần mềm rác (bloatware) và cấu hình mặc định nặng dành cho game 3D, dẫn đến mỗi máy ảo tiêu tốn từ `2GB - 4GB RAM` và `15% - 30% CPU`. Khi chạy từ 5-10 máy ảo đồng thời, hệ thống dễ bị tràn RAM và nghẽn cổ chai CPU/Disk.

## 2. Quyết định (Decision)

Chúng tôi quyết định sử dụng **QEMU kết hợp Android-x86 / BlissOS (Minimal Image)** làm động cơ lõi, được điều khiển và tối ưu hóa trực tiếp thông qua tầng **Python Core Engine**:

1. **Tăng tốc phần cứng (Hardware Acceleration):**
   - Trên **Windows 10/11**: Sử dụng `WHPX` (Windows Hypervisor Platform) hoặc `HAXM` / `GVM`.
   - Trên **Linux**: Sử dụng `KVM` (Kernel-based Virtual Machine).
2. **Cơ chế ổ đĩa Copy-on-Write (`qcow2` Backing File):**
   - Duy nhất 1 file ảnh gốc (`base_android_slim.img` - Read-Only).
   - Mỗi máy ảo con chỉ tạo một file `overlay_instance_X.qcow2` chứa dữ liệu thay đổi (chỉ tốn vài chục MB thay vì copy cả 4GB cho mỗi máy).
   - Giúp giảm 90% dung lượng ổ cứng và tăng tốc độ khởi tạo máy ảo mới xuống dưới 1 giây.
3. **Ảo hóa Thiết bị (VirtIO Paravirtualization):**
   - Sử dụng `virtio-blk` cho ổ cứng, `virtio-net` cho mạng, `virtio-gpu` / `virgl` cho đồ họa 2D/Video hardware decoding (H.264/HEVC cho TikTok/Reels).
   - Loại bỏ giả lập âm thanh (`-audiodev none`) khi chạy chế độ tự động hóa hàng loạt để tiết kiệm ngắt (interrupts) CPU.

## 3. Hệ quả (Consequences)

### Ưu điểm:
- **Siêu nhẹ:** Mỗi instance chỉ tiêu tốn khoảng `768MB - 1024MB RAM` và `< 5% CPU` khi lướt TikTok/Facebook.
- **Không Bloatware:** Kiểm soát hoàn toàn hệ điều hành khách (Guest OS).
- **Khởi tạo tức thì:** Tạo 10 máy ảo mới trong vài giây nhờ cơ chế `qcow2` overlay.

### Nhược điểm & Thách thức:
- Cần cài đặt QEMU và bật Hyper-V / WHPX trên Windows.
- Các ứng dụng yêu cầu ARM native mà chưa có bản x86_64 cần tích hợp thư viện dịch mã nhị phân nhẹ (`libhoudini` hoặc `libndk_translation`).
