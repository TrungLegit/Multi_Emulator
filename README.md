# Multi_Emulator

> Multi Emulator ADR version for education.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

**Multi_Emulator** is an educational project built with **Python**, **Node.js**, and **HTML** to explore and demonstrate multi-emulator concepts and architecture decision records (ADR).

## Tech Stack

- **Backend / Core**: Python 3.10+
- **Tooling / Runtime**: Node.js 18+
- **Frontend / UI**: HTML5, CSS3, JavaScript

## Getting Started

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) and `npm`
- [Git](https://git-scm.com/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/TrungLegit/Multi_Emulator.git
   cd Multi_Emulator
   ```

2. **Set up the Python environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

## Hướng Dẫn Sử Dụng Nhanh (Quick Usage — Python Connector CLI)

Module **Emulator Connector** cho phép quét tất cả các máy ảo hiện có (qua ADB, cổng TCP nội bộ `5554-5566`, `62001`, `21503` hoặc chế độ Mock tự động), kết nối chúng lại và gom vào một **Sync Hub** chung:

```bash
# 1. Quét (Scan) tất cả các emulator hiện có trên máy
python3 main.py scan

# 2. Kết nối tất cả các emulator đã quét và tự động gom vào Sync Hub chung
python3 main.py connect --all

# 3. Kết nối riêng lẻ 1 emulator theo ID
python3 main.py connect --id emu_01

# 4. Liên kết (Link) các emulator cụ thể vào một nhóm đồng bộ và chọn máy Master
python3 main.py link --ids emu_01 emu_02 emu_03 --group sync_hub_default --master emu_01

# 5. Phát lệnh đồng bộ (Broadcast) tới tất cả emulator trong Sync Hub
python3 main.py broadcast --cmd "input tap 540 960"

# 6. Kiểm tra trạng thái hiện tại của Connector Pool & Sync Hub
python3 main.py status

# 7. Xuất kết quả dạng JSON (dùng cho IPC với Node.js hoặc debug)
python3 main.py status --json

# 8. Ngắt kết nối một hoặc toàn bộ emulator
python3 main.py disconnect --id emu_02
python3 main.py disconnect

# 9. Chạy bộ Unit Tests kiểm thử Connector
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Khởi chạy Giao diện Web Dashboard (Node.js + HTML)

```bash
npm start
# Truy cập http://localhost:3000 để sử dụng bảng điều khiển Scan / Connect / Broadcast trực quan
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details on how to submit pull requests and report issues.

## Security

Please review our [SECURITY.md](SECURITY.md) policy for reporting security vulnerabilities responsibly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
