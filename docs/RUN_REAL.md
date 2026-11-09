# Chạy giả lập thật (Windows 10/11)

1. Bật **Windows Hypervisor Platform** (Windows Features) và khởi động lại.
2. Cài [QEMU for Windows](https://www.qemu.org/download/#windows) và [Android platform-tools](https://developer.android.com/tools/releases/platform-tools); thêm vào PATH.
3. Tải image Android-x86 / BlissOS x86_64 (.iso): https://www.android-x86.org/ hoặc https://blissos.org/
4. Cài Python 3.10+ rồi:
```
pip install -r requirements.txt
python main.py set-image C:\path\android-x86_64-9.0-r2.iso
python main.py create Tiktok1 --profile standard
python main.py start emu_01
python main.py optimize emu_01    # sau khi Android boot xong, áp dụng tối ưu qua ADB
python main.py vm-status           # RAM/CPU thật của tiến trình QEMU
python main.py stop emu_01
```
Lần đầu với file .iso: chọn "Live CD / Install to disk" của Android-x86 (ổ 8G qcow2 mỏng được tạo sẵn).
Sau khi cài xong, nên lưu ổ đã cài làm base .qcow2 rồi `set-image` để các máy sau dùng overlay copy-on-write.

## Giao diện (kiểu LDPlayer) và app
```
python main.py gui                       # mở trình quản lý: tạo/start/stop, tối ưu, cài APK, mở app, chụp màn hình
python main.py install emu_01 tiktok.apk # cài APK bằng CLI
python main.py open emu_01 youtube       # mở tiktok | youtube | facebook
```
Dùng image có Google Play (hoặc tự cài APK TikTok/YouTube/Facebook). Cửa sổ máy ảo do QEMU mở riêng.
