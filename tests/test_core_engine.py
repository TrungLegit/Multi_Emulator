"""Tests for the lightweight Android engine (TikTok/YouTube/Facebook)."""

import sys

import src.core.runtime as rt_mod
from src.core.adb_optimizer import BLOATWARE_PACKAGES, AdbOptimizer
from src.core.profiles import APPS, PROFILES, get_profile
from src.core.qemu_builder import QemuCommandBuilder


def test_profiles_are_low_resource() -> None:
    for p in PROFILES.values():
        assert p.ram_mb <= 1024 and p.cpu_cores <= 2 and p.fps_limit <= 30 and p.width <= 540
    assert set(APPS) == {"tiktok", "youtube", "facebook"}


def test_qemu_command_windows_and_linux() -> None:
    prof = get_profile("standard")
    w = " ".join(QemuCommandBuilder("Windows").build_launch_cmd("e1", prof, "d.qcow2", 5555))
    assert "whpx" in w and "-m 1024" in w and "hostfwd=tcp:127.0.0.1:5555-:5555" in w
    k = " ".join(QemuCommandBuilder("Linux").build_launch_cmd("e1", get_profile("lite"), "d.qcow2", 5557))
    assert "-enable-kvm" in k and "-m 768" in k


def test_adb_optimizer() -> None:
    cmds = [" ".join(c) for c in AdbOptimizer("127.0.0.1:5555").build_optimization_commands(get_profile("lite"))]
    assert any("wm size 360x640" in c for c in cmds)
    assert any("window_animation_scale 0.0" in c for c in cmds)
    assert any("max_cached_processes" in c for c in cmds)
    for pkg in BLOATWARE_PACKAGES:
        assert any(pkg in c for c in cmds)


def test_real_runtime_spawns_and_measures(tmp_path, monkeypatch) -> None:
    fake = tmp_path / "fakeqemu.py"
    fake.write_text("import time\ntime.sleep(30)\n")
    wrapper = tmp_path / "fake"
    wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {fake}\n")
    wrapper.chmod(0o755)
    img = tmp_path / "a.qcow2"
    img.write_text("x")
    monkeypatch.setattr(rt_mod, "find_tool", lambda n, o=None: str(wrapper))
    monkeypatch.setattr(rt_mod.subprocess, "run", lambda *a, **k: None)
    rt = rt_mod.RealRuntime(tmp_path / "ws", host_os="Linux")
    rt.set_image(img)
    iid = rt.create("t", "lite")
    info = rt.start(iid)
    try:
        st = rt.status()[0]
        assert st["status"] == "RUNNING" and st["pid"] == info["pid"] and st["ram_mb"] > 0
    finally:
        assert rt.stop(iid)
    assert rt.status()[0]["status"] == "STOPPED"


def test_gui_builds_offscreen(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from src.gui.app import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow(str(tmp_path))
    w.rt.create("x", "lite")
    w.refresh()
    assert w.table.rowCount() == 1 and w.table.item(0, 0).text() == "emu_01"
