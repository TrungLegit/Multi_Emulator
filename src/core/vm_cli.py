#!/usr/bin/env python3
"""Multi_Emulator — Python Core Engine CLI (Lightweight Android Edition for TikTok & FB)."""

import argparse
import json
from typing import Any

from src.core.local_manager import LocalInstanceManager
from src.core.profiles import SOCIAL_PROFILES


def get_project_info() -> dict[str, str]:
    """Return metadata about the Multi_Emulator project."""
    return {
        "name": "Multi_Emulator",
        "version": "0.2.0",
        "description": "Ultra-lightweight Android Multi-Emulator Engine (TikTok/FB Optimized)",
    }


def build_demo_cluster(host_os: str = "Windows") -> dict[str, Any]:
    """Create a demonstration cluster showing low-RAM/CPU optimization for TikTok & Facebook."""
    manager = LocalInstanceManager(host_os=host_os)

    # Create 3 optimized Android instances
    inst1 = manager.create_instance("TikTok-Node-01", profile_id="standard_tiktok_fb")
    inst2 = manager.create_instance("FBLite-Node-02", profile_id="ultra_lite_social")
    inst3 = manager.create_instance("Farm-Headless-03", profile_id="headless_automation")

    boot1 = manager.start_instance(inst1.instance_id)
    boot2 = manager.start_instance(inst2.instance_id)
    manager.start_instance(inst3.instance_id)

    task1 = manager.run_social_task(inst1.instance_id, "tiktok")
    task2 = manager.run_social_task(inst2.instance_id, "facebook")

    return {
        "project": get_project_info(),
        "host_os_target": host_os,
        "available_profiles": {k: v.to_dict() for k, v in SOCIAL_PROFILES.items()},
        "instances": manager.list_instances(),
        "sample_qemu_boot_plan": boot1,
        "sample_ultralite_boot_plan": boot2,
        "active_social_tasks": [task1, task2],
    }


def run_vm_cli(argv: list[str]) -> None:
    """Run the real-VM CLI (set-image/create/start/stop/optimize/status/demo)."""
    parser = argparse.ArgumentParser(prog="main.py", description="Multi_Emulator — lightweight Android VM manager")
    parser.add_argument("--workspace", default="vm_data")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("demo", help="In kế hoạch mô phỏng (không chạy VM)")
    p = sub.add_parser("set-image", help="Đăng ký image Android-x86/BlissOS (.iso/.qcow2)")
    p.add_argument("path")
    p = sub.add_parser("create", help="Tạo instance")
    p.add_argument("name")
    p.add_argument("--profile", default="standard_tiktok_fb", choices=list(SOCIAL_PROFILES))
    for c in ("start", "stop", "optimize"):
        p = sub.add_parser(c)
        p.add_argument("id")
    sub.add_parser("vm-status", help="RAM/CPU thật của các máy đang chạy")
    args = parser.parse_args(argv)

    if args.cmd in (None, "demo"):
        print(json.dumps(build_demo_cluster(), indent=2, ensure_ascii=False))
        return

    from src.core.runtime import RealRuntime, RuntimeError_

    rt = RealRuntime(args.workspace)
    try:
        if args.cmd == "set-image":
            rt.set_image(args.path)
            print("OK, image:", args.path)
        elif args.cmd == "create":
            print("Đã tạo", rt.create(args.name, args.profile))
        elif args.cmd == "start":
            r = rt.start(args.id)
            print(f"{args.id} đang chạy, PID {r['pid']}")
            if "cmd" in r:
                print(r["cmd"])
        elif args.cmd == "stop":
            print("Đã dừng" if rt.stop(args.id) else "Máy không chạy")
        elif args.cmd == "optimize":
            print("Đã áp dụng", rt.optimize(args.id), "lệnh tối ưu")
        elif args.cmd == "vm-status":
            for r in rt.status():
                print(f"{r['id']} {r['name']:<16} {r['status']:<8} PID={r['pid']} "
                      f"RAM={r['ram_mb']}MB CPU={r['cpu_percent']}% ADB={r['adb']}")
    except RuntimeError_ as e:
        raise SystemExit(f"Lỗi: {e}")

