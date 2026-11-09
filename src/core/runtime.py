"""Real runtime: launches QEMU processes, applies ADB tweaks, measures real RAM/CPU."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import psutil

from src.core.adb_optimizer import AdbOptimizer
from src.core.profiles import get_profile
from src.core.qemu_builder import QemuCommandBuilder


class RuntimeError_(Exception):
    """Raised when the host is missing a required tool or the image."""


def find_tool(name: str, override: str | None = None) -> str:
    """Locate an executable (also checks the default QEMU dir on Windows)."""
    cand = override or shutil.which(name)
    if not cand and os.name == "nt":
        p = Path(r"C:\Program Files\qemu") / f"{name}.exe"
        cand = str(p) if p.exists() else None
    if not cand:
        raise RuntimeError_(
            f"Không tìm thấy '{name}'. Cài QEMU (https://www.qemu.org/download/) "
            "/ Android platform-tools và thêm vào PATH."
        )
    return cand


class RealRuntime:
    """Persistent multi-VM runtime. State is stored in <workspace>/state.json."""

    def __init__(self, workspace: str | Path = "vm_data", host_os: str | None = None) -> None:
        self.ws = Path(workspace)
        self.ws.mkdir(parents=True, exist_ok=True)
        self.state_file = self.ws / "state.json"
        self.builder = QemuCommandBuilder(host_os=host_os)

    # ---------- state ----------
    def _load(self) -> dict[str, Any]:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"image": None, "instances": {}}

    def _save(self, s: dict[str, Any]) -> None:
        self.state_file.write_text(json.dumps(s, indent=2))

    def set_image(self, image: str | Path) -> None:
        """Register the Android-x86/BlissOS image (.iso or .qcow2/.img)."""
        p = Path(image).resolve()
        if not p.exists():
            raise RuntimeError_(f"Image không tồn tại: {p}")
        s = self._load()
        s["image"] = str(p)
        self._save(s)

    # ---------- lifecycle ----------
    def create(self, name: str, profile_id: str = "standard") -> str:
        get_profile(profile_id)
        s = self._load()
        n = len(s["instances"]) + 1
        while f"emu_{n:02d}" in s["instances"]:
            n += 1
        iid = f"emu_{n:02d}"
        s["instances"][iid] = {
            "name": name, "profile": profile_id, "adb_port": 5555 + (n - 1) * 2,
            "pid": None, "started_at": None,
        }
        self._save(s)
        return iid

    def _qemu_cmd(self, iid: str, inst: dict[str, Any], image: str, qemu_bin: str, qemu_img: str) -> list[str]:
        profile = get_profile(inst["profile"])
        disk = self.ws / f"{iid}.qcow2"
        is_iso = image.lower().endswith(".iso")
        if not disk.exists():
            if is_iso:  # blank 8G thin disk for Android-x86 installation / data
                subprocess.run([qemu_img, "create", "-f", "qcow2", str(disk), "8G"], check=True, capture_output=True)
            else:  # tiny copy-on-write overlay on top of the shared base image
                fmt = "qcow2" if image.lower().endswith(".qcow2") else "raw"
                subprocess.run(
                    [qemu_img, "create", "-f", "qcow2", "-b", image, "-F", fmt, str(disk)],
                    check=True, capture_output=True,
                )
        cmd = self.builder.build_launch_cmd(
            iid, profile, disk, inst["adb_port"]
        )
        cmd[0] = qemu_bin
        if is_iso:
            cmd += ["-cdrom", image, "-boot", "order=dc,menu=off"]
        return cmd

    def start(self, iid: str, optimize: bool = True) -> dict[str, Any]:
        s = self._load()
        inst = s["instances"].get(iid)
        if not inst:
            raise RuntimeError_(f"Không có instance {iid}")
        if self._alive(inst):
            return {"id": iid, "pid": inst["pid"], "note": "đã chạy"}
        if not s["image"]:
            raise RuntimeError_("Chưa có image. Chạy: python main.py set-image <file.iso|qcow2>")
        qemu_bin = find_tool("qemu-system-x86_64")
        qemu_img = find_tool("qemu-img")
        cmd = self._qemu_cmd(iid, inst, s["image"], qemu_bin, qemu_img)
        log = open(self.ws / f"{iid}.log", "ab")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, creationflags=flags)
        time.sleep(1.0)
        if proc.poll() is not None:
            raise RuntimeError_(f"QEMU thoát ngay (mã {proc.returncode}). Xem {self.ws / (iid + '.log')}")
        inst["pid"], inst["started_at"] = proc.pid, time.time()
        self._save(s)
        return {"id": iid, "pid": proc.pid, "cmd": " ".join(cmd)}

    def optimize(self, iid: str, timeout: int = 180) -> int:
        """Wait for ADB, then run the optimization commands. Returns number applied."""
        s = self._load()
        inst = s["instances"][iid]
        adb = find_tool("adb")
        serial = f"127.0.0.1:{inst['adb_port']}"
        end = time.time() + timeout
        while time.time() < end:
            subprocess.run([adb, "connect", serial], capture_output=True)
            r = subprocess.run([adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                               capture_output=True, text=True)
            if r.stdout.strip() == "1":
                break
            time.sleep(3)
        else:
            raise RuntimeError_("Android chưa boot xong / ADB chưa kết nối (hết thời gian chờ).")
        applied = 0
        for c in AdbOptimizer(serial).build_optimization_commands(get_profile(inst["profile"])):
            c[0] = adb
            if subprocess.run(c, capture_output=True).returncode == 0:
                applied += 1
        return applied

    def stop(self, iid: str) -> bool:
        s = self._load()
        inst = s["instances"][iid]
        ok = False
        if self._alive(inst):
            p = psutil.Process(inst["pid"])
            p.terminate()
            try:
                p.wait(5)
            except psutil.TimeoutExpired:
                p.kill()
            ok = True
        inst["pid"] = inst["started_at"] = None
        self._save(s)
        return ok

    # ---------- metrics ----------
    @staticmethod
    def _alive(inst: dict[str, Any]) -> bool:
        pid = inst.get("pid")
        if not pid or not psutil.pid_exists(pid):
            return False
        try:
            return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    def status(self) -> list[dict[str, Any]]:
        """Return real RSS memory and CPU% of each QEMU process."""
        out = []
        s = self._load()
        procs = {}
        for iid, inst in s["instances"].items():
            if self._alive(inst):
                p = psutil.Process(inst["pid"])
                p.cpu_percent(None)
                procs[iid] = p
        time.sleep(0.5)
        for iid, inst in s["instances"].items():
            p = procs.get(iid)
            out.append({
                "id": iid, "name": inst["name"], "profile": inst["profile"],
                "status": "RUNNING" if p else "STOPPED", "pid": inst["pid"],
                "adb": f"127.0.0.1:{inst['adb_port']}",
                "ram_mb": round(p.memory_info().rss / 1048576) if p else 0,
                "cpu_percent": round(p.cpu_percent(None), 1) if p else 0.0,
                "uptime_s": int(time.time() - inst["started_at"]) if p and inst["started_at"] else 0,
            })
        return out

    # ---------- adb helpers ----------
    def _adb(self, iid: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
        inst = self._load()["instances"][iid]
        adb = find_tool("adb")
        serial = f"127.0.0.1:{inst['adb_port']}"
        subprocess.run([adb, "connect", serial], capture_output=True, timeout=15)
        return subprocess.run([adb, "-s", serial, *args], capture_output=True, text=True, timeout=timeout)

    def install_apk(self, iid: str, apk: str | Path) -> str:
        """Install an .apk file into the instance."""
        r = self._adb(iid, "install", "-r", str(apk), timeout=300)
        if r.returncode != 0 or "Success" not in r.stdout:
            raise RuntimeError_(f"Cài APK lỗi: {r.stdout.strip() or r.stderr.strip()}")
        return "Success"

    def launch_app(self, iid: str, app: str) -> None:
        """Launch tiktok / youtube / facebook."""
        from src.core.profiles import APPS

        if app not in APPS:
            raise RuntimeError_(f"App không hỗ trợ: {app}. Chọn: {', '.join(APPS)}")
        r = self._adb(iid, "shell", "monkey", "-p", APPS[app], "-c", "android.intent.category.LAUNCHER", "1")
        if "No activities found" in r.stdout + r.stderr:
            raise RuntimeError_(f"Chưa cài {app} ({APPS[app]}). Hãy cài APK trước.")

    def key(self, iid: str, name: str) -> None:
        """Send a key: home, back, recent, volup, voldown."""
        codes = {"home": 3, "back": 4, "recent": 187, "volup": 24, "voldown": 25}
        self._adb(iid, "shell", "input", "keyevent", str(codes[name]))

    def screenshot(self, iid: str, out: str | Path) -> Path:
        """Save a PNG screenshot to `out`."""
        inst = self._load()["instances"][iid]
        adb = find_tool("adb")
        serial = f"127.0.0.1:{inst['adb_port']}"
        r = subprocess.run([adb, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=30)
        if r.returncode != 0 or not r.stdout:
            raise RuntimeError_("Chụp màn hình thất bại (Android đã boot chưa?)")
        Path(out).write_bytes(r.stdout)
        return Path(out)
