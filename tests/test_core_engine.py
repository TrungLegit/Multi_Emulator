"""Unit tests for the Ultra-Lightweight Android Core Engine (TikTok/Facebook optimized)."""

import pytest

from main import get_project_info
from src.core.vm_cli import build_demo_cluster
from src.core.adb_optimizer import BLOATWARE_PACKAGES, AdbOptimizer
from src.core.local_manager import LocalInstanceManager
from src.core.profiles import SOCIAL_PROFILES, get_profile
from src.core.qemu_builder import QemuCommandBuilder


def test_project_info() -> None:
    """Verify project metadata."""
    info = get_project_info()
    assert info["name"] == "Multi_Emulator"
    assert "version" in info


def test_social_profiles_are_low_resource() -> None:
    """Ensure all presets stay at or below 1024MB RAM and 30 FPS for maximum savings."""
    for profile_id, profile in SOCIAL_PROFILES.items():
        assert profile.ram_mb <= 1024, f"{profile_id} exceeds 1024MB RAM limit"
        assert profile.cpu_cores <= 2, f"{profile_id} exceeds 2 vCPU cores"
        assert profile.fps_limit <= 30, f"{profile_id} exceeds 30 FPS limit"
        assert profile.width <= 540, f"{profile_id} width exceeds 540p"
        assert profile.low_ram_flag is True


def test_windows_whpx_qemu_command_generation() -> None:
    """Verify Windows 10/11 WHPX hardware acceleration and VirtIO flags."""
    builder = QemuCommandBuilder(host_os="Windows")
    profile = get_profile("standard_tiktok_fb")
    cmd = builder.build_launch_cmd(
        instance_id="emu_01",
        profile=profile,
        overlay_disk="vm_data/emu_01.qcow2",
        adb_port=5555,
    )
    cmd_str = " ".join(cmd)
    assert "whpx,kernel-irqchip=off" in cmd_str
    assert "-m 1024" in cmd_str
    assert "-vga std" in cmd_str
    assert "hostfwd=tcp:127.0.0.1:5555-:5555" in cmd_str


def test_linux_kvm_and_headless_mode() -> None:
    """Verify Linux KVM acceleration and headless display stripping."""
    builder = QemuCommandBuilder(host_os="Linux")
    profile = get_profile("headless_automation")
    cmd = builder.build_launch_cmd(
        instance_id="emu_02",
        profile=profile,
        overlay_disk="vm_data/emu_02.qcow2",
        adb_port=5557,
        headless=True,
    )
    cmd_str = " ".join(cmd)
    assert "-enable-kvm" in cmd_str
    assert "-display none" in cmd_str
    assert "-audiodev none,id=noaudio" in cmd_str


def test_adb_optimizer_disables_animations_and_bloatware() -> None:
    """Verify ADB commands strip animations, lower resolution, and disable bloatware."""
    profile = get_profile("ultra_lite_social")
    optimizer = AdbOptimizer(adb_serial="127.0.0.1:5555")
    cmds = [" ".join(c) for c in optimizer.build_optimization_commands(profile)]

    assert any("wm size 360x640" in c for c in cmds)
    assert any("wm density 160" in c for c in cmds)
    assert any("window_animation_scale 0.0" in c for c in cmds)
    assert any("max_cached_processes" in c for c in cmds)
    for pkg in BLOATWARE_PACKAGES:
        assert any(f"pm disable-user --user 0 {pkg}" in c for c in cmds)


def test_instance_manager_lifecycle_and_social_tasks() -> None:
    """Test creating, starting, running TikTok/Facebook tasks, and stopping instances."""
    manager = LocalInstanceManager(host_os="Windows")
    inst1 = manager.create_instance("TikTok-Clone-1", profile_id="standard_tiktok_fb")
    inst2 = manager.create_instance("FBLite-Clone-2", profile_id="ultra_lite_social")

    assert inst1.adb_port == 5555
    assert inst2.adb_port == 5557
    assert inst1.status == "STOPPED"

    boot_info = manager.start_instance(inst1.instance_id)
    assert boot_info["instance"]["status"] == "RUNNING"
    assert boot_info["instance"]["metrics"]["ram_usage_mb"] < 1024

    tiktok_task = manager.run_social_task(inst1.instance_id, "tiktok")
    assert tiktok_task["target_package"] == "com.ss.android.ugc.trill"
    assert "input swipe 270" in tiktok_task["auto_scroll_command"]

    stopped = manager.stop_instance(inst1.instance_id)
    assert stopped["status"] == "STOPPED"
    assert stopped["metrics"]["ram_usage_mb"] == 0


def test_demo_cluster_builder() -> None:
    """Verify the end-to-end demo cluster payload structure."""
    cluster = build_demo_cluster(host_os="Windows")
    assert len(cluster["instances"]) == 3
    assert "ultra_lite_social" in cluster["available_profiles"]
    assert len(cluster["active_social_tasks"]) == 2


def test_real_runtime_spawns_and_measures(tmp_path, monkeypatch) -> None:
    """Use a fake 'qemu' (python sleep) to verify real PID tracking and psutil metrics."""
    import sys
    import src.core.runtime as rt_mod

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
    iid = rt.create("t", "ultra_lite_social")
    info = rt.start(iid)
    try:
        st = rt.status()[0]
        assert st["status"] == "RUNNING" and st["pid"] == info["pid"] and st["ram_mb"] > 0
    finally:
        assert rt.stop(iid)
    assert rt.status()[0]["status"] == "STOPPED"
