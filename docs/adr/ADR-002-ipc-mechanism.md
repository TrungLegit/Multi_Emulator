# ADR-002: Cơ Chế Giao Tiếp Liên Tiến Trình (IPC) Giữa Node.js và Python Core

- **Trạng thái:** Đã chấp thuận (Accepted)
- **Ngày:** 2026-11-08
- **Tác giả:** Trung & Khoa

## 1. Bối cảnh (Context)
Khi người dùng trên giao diện Dashboard của Chương nhấn các nút như **"Scan Emulators"**, **"Connect & Sync All"**, hoặc kéo thanh trượt điều chỉnh tốc độ cuộn/gửi lệnh đồng loạt (**"Broadcast Command"**), máy chủ Node.js cần gọi xuống Python Core Engine và nhận kết quả trả về mà không làm treo (block) Event Loop của Node.js.

## 2. Quyết định (Decision)
Sử dụng cơ chế **JSON-over-Stdio IPC thông qua `child_process.execFile`** kết hợp cờ `--json` trên CLI của Python (`python3 main.py --json <subcommand>`), kèm theo lưu trữ trạng thái bền vững tại file `.connector_state.json`.

## 3. Lý do lựa chọn (Rationale)
- **Không cần cài đặt Message Broker bên ngoài:** Không phụ thuộc Redis hay RabbitMQ, giữ cho bộ cài đặt dự án cực kỳ gọn nhẹ.
- **Chuẩn hóa dữ liệu (Schema Contract):** Python Core luôn xuất dữ liệu JSON chuẩn (`summary`, `instances`, `syncGroups`) qua `stdout`. Node.js dễ dàng `JSON.parse()` và chuyển tiếp xuống Frontend hoặc phát qua kênh thời gian thực.
- **An toàn & Không nghẽn (Non-blocking):** `execFile` chạy tiến trình con bất đồng bộ với timeout kiểm soát chặt chẽ (15 giây), ngăn chặn lỗi treo server.

## 4. Hệ quả (Consequences)
- **Tích cực:** Dễ dàng debug trực tiếp từ terminal bằng cách gõ lệnh `python3 main.py --json status` trước khi tích hợp lên giao diện Web.
- **Tiêu cực:** Mỗi lệnh IPC khởi tạo một tiến trình Python ngắn hạn, nhưng nhờ trạng thái được đồng bộ qua `.connector_state.json`, thời gian phản hồi chỉ mất vài chục mili-giây.
