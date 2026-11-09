#!/usr/bin/env python3
"""CLI for real VM control (set-image/create/start/stop/optimize/vm-status/install/open)."""

import argparse

from src.core.profiles import APPS, DEFAULT_PROFILE, PROFILES


def run_vm_cli(argv: list[str]) -> None:
    """Run the real-VM CLI."""
    parser = argparse.ArgumentParser(prog="main.py", description="Multi_Emulator — Android lite for TikTok/YouTube/Facebook")
    parser.add_argument("--workspace", default="vm_data")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("set-image")
    p.add_argument("path")
    p = sub.add_parser("create")
    p.add_argument("name")
    p.add_argument("--profile", default=DEFAULT_PROFILE, choices=list(PROFILES))
    for c in ("start", "stop", "optimize"):
        sub.add_parser(c).add_argument("id")
    p = sub.add_parser("install")
    p.add_argument("id")
    p.add_argument("apk")
    p = sub.add_parser("open")
    p.add_argument("id")
    p.add_argument("app", choices=list(APPS))
    sub.add_parser("vm-status")
    sub.add_parser("gui", help="Mở giao diện")
    args = parser.parse_args(argv)

    if args.cmd == "gui":
        from src.gui.app import run_gui

        run_gui(args.workspace)
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
        elif args.cmd == "stop":
            print("Đã dừng" if rt.stop(args.id) else "Máy không chạy")
        elif args.cmd == "optimize":
            print("Đã áp dụng", rt.optimize(args.id), "lệnh tối ưu")
        elif args.cmd == "install":
            print(rt.install_apk(args.id, args.apk))
        elif args.cmd == "open":
            rt.launch_app(args.id, args.app)
            print("Đã mở", args.app)
        elif args.cmd == "vm-status":
            for r in rt.status():
                print(f"{r['id']} {r['name']:<16} {r['status']:<8} PID={r['pid']} "
                      f"RAM={r['ram_mb']}MB CPU={r['cpu_percent']}% ADB={r['adb']}")
    except RuntimeError_ as e:
        raise SystemExit(f"Lỗi: {e}")
