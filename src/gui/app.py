"""LDPlayer-style desktop manager (PySide6) for lightweight TikTok/YouTube/Facebook VMs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QMainWindow, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView, QHeaderView,
)

from src.core.profiles import APPS, DEFAULT_PROFILE, PROFILES
from src.core.runtime import RealRuntime, RuntimeError_

COLS = ["ID", "Tên", "Cấu hình", "Trạng thái", "RAM (MB)", "CPU %", "ADB"]


class _Signals(QObject):
    done = Signal(str)
    failed = Signal(str)


class _Job(QRunnable):
    """Run a blocking runtime call off the UI thread."""

    def __init__(self, fn: Callable[[], Any], ok_msg: str) -> None:
        super().__init__()
        self.fn, self.ok_msg, self.signals = fn, ok_msg, _Signals()

    def run(self) -> None:
        try:
            self.fn()
            self.signals.done.emit(self.ok_msg)
        except (RuntimeError_, Exception) as e:  # noqa: BLE001 - show any error to user
            self.signals.failed.emit(str(e))


class MainWindow(QMainWindow):
    """Main manager window: instance table + toolbar."""

    def __init__(self, workspace: str = "vm_data") -> None:
        super().__init__()
        self.rt = RealRuntime(workspace)
        self.pool = QThreadPool.globalInstance()
        self.setWindowTitle("Multi_Emulator — Android Lite (TikTok · YouTube · Facebook)")
        self.resize(900, 460)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.profile = QComboBox()
        for pid, p in PROFILES.items():
            self.profile.addItem(p.name, pid)
        self.profile.setCurrentIndex(list(PROFILES).index(DEFAULT_PROFILE))
        self.app_box = QComboBox()
        self.app_box.addItems(list(APPS))

        top = QHBoxLayout()
        top.addWidget(self._btn("Chọn image…", self.pick_image))
        top.addWidget(QLabel("Cấu hình:"))
        top.addWidget(self.profile)
        top.addWidget(self._btn("＋ Tạo máy", self.create))
        top.addStretch()
        row = QHBoxLayout()
        for text, fn in [
            ("▶ Start", self.start), ("■ Stop", self.stop), ("⚡ Tối ưu", self.optimize),
            ("📦 Cài APK", self.install), ("🏠 Home", lambda: self.key("home")),
            ("◀ Back", lambda: self.key("back")), ("📷 Chụp", self.shot),
        ]:
            row.addWidget(self._btn(text, fn))
        row.addWidget(self.app_box)
        row.addWidget(self._btn("Mở app", self.open_app))
        self.status = QLabel("Sẵn sàng")
        lay = QVBoxLayout()
        lay.addLayout(top)
        lay.addWidget(self.table)
        lay.addLayout(row)
        lay.addWidget(self.status)
        w = QWidget()
        w.setLayout(lay)
        self.setCentralWidget(w)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.refresh()

    @staticmethod
    def _btn(text: str, fn: Callable[[], Any]) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(lambda _=False: fn())
        return b

    def selected(self) -> str | None:
        r = self.table.currentRow()
        if r < 0:
            self.status.setText("Hãy chọn một máy trong danh sách")
            return None
        return self.table.item(r, 0).text()

    def refresh(self) -> None:
        try:
            rows = self.rt.status()
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Lỗi đọc trạng thái: {e}")
            return
        sel = self.table.currentRow()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["id"], r["name"], PROFILES[r["profile"]].name if r["profile"] in PROFILES else r["profile"],
                    r["status"], r["ram_mb"], r["cpu_percent"], r["adb"]]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))
        if 0 <= sel < len(rows):
            self.table.selectRow(sel)

    def run_job(self, fn: Callable[[], Any], ok: str) -> None:
        self.status.setText("Đang xử lý…")
        job = _Job(fn, ok)
        job.signals.done.connect(self.status.setText)
        job.signals.failed.connect(lambda m: (self.status.setText("Lỗi: " + m), QMessageBox.warning(self, "Lỗi", m)))
        job.signals.done.connect(lambda _: self.refresh())
        self.pool.start(job)

    # ---- actions ----
    def pick_image(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Chọn image Android-x86/BlissOS", "", "Image (*.iso *.qcow2 *.img)")
        if f:
            try:
                self.rt.set_image(f)
                self.status.setText("Đã chọn image: " + Path(f).name)
            except RuntimeError_ as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    def create(self) -> None:
        name, ok = QInputDialog.getText(self, "Tạo máy", "Tên máy:")
        if ok and name.strip():
            iid = self.rt.create(name.strip(), self.profile.currentData())
            self.status.setText(f"Đã tạo {iid}")
            self.refresh()

    def start(self) -> None:
        if i := self.selected():
            self.run_job(lambda: self.rt.start(i), f"Đã khởi động {i}. Chờ Android boot rồi bấm ⚡ Tối ưu")

    def stop(self) -> None:
        if i := self.selected():
            self.run_job(lambda: self.rt.stop(i), f"Đã dừng {i}")

    def optimize(self) -> None:
        if i := self.selected():
            self.run_job(lambda: self.rt.optimize(i), f"Đã tối ưu {i}")

    def install(self) -> None:
        if i := self.selected():
            f, _ = QFileDialog.getOpenFileName(self, "Chọn APK", "", "APK (*.apk)")
            if f:
                self.run_job(lambda: self.rt.install_apk(i, f), f"Đã cài {Path(f).name}")

    def key(self, name: str) -> None:
        if i := self.selected():
            self.run_job(lambda: self.rt.key(i, name), f"Đã gửi {name}")

    def shot(self) -> None:
        if i := self.selected():
            out = Path(self.rt.ws) / f"{i}.png"
            self.run_job(lambda: self.rt.screenshot(i, out), f"Đã lưu {out}")

    def open_app(self) -> None:
        if i := self.selected():
            app = self.app_box.currentText()
            self.run_job(lambda: self.rt.launch_app(i, app), f"Đã mở {app}")


def run_gui(workspace: str = "vm_data") -> None:
    """Launch the desktop manager."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(workspace)
    win.show()
    app.exec()
