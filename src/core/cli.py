"""CLI & IPC entry point for Multi_Emulator Connector Engine."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.core.connector import EmulatorConnector
from src.core.device_adapter import CompositeDiscoveryAdapter
from src.core.instance_manager import InstanceManager


def build_parser() -> argparse.ArgumentParser:
    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON (used by Node.js IPC bridge)",
    )
    common_parent.add_argument(
        "--mock",
        action="store_true",
        help="Force simulated Mock emulators during discovery",
    )

    parser = argparse.ArgumentParser(
        prog="multi-emulator",
        description="Multi_Emulator Connector & Sync Hub CLI (Educational ADR version)",
        parents=[common_parent],
    )

    subparsers = parser.add_subparsers(dest="command", help="Connector subcommands")

    # scan
    subparsers.add_parser("scan", help="Scan and discover all available emulators", parents=[common_parent])

    # connect
    connect_parser = subparsers.add_parser(
        "connect", help="Connect to one or all discovered emulators and link them", parents=[common_parent]
    )
    connect_parser.add_argument(
        "--id", dest="instance_id", help="Connect a specific emulator ID (e.g. emu_01)"
    )
    connect_parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Connect all discovered emulators and link into Sync Hub (default)",
    )
    connect_parser.add_argument(
        "--no-link",
        action="store_true",
        help="Connect emulators without automatically linking them into a Sync Group",
    )

    # link
    link_parser = subparsers.add_parser(
        "link", help="Link connected emulators together into a Sync Group", parents=[common_parent]
    )
    link_parser.add_argument(
        "--ids",
        nargs="*",
        help="List of emulator IDs to link together (defaults to all connected)",
    )
    link_parser.add_argument(
        "--group",
        default=EmulatorConnector.DEFAULT_GROUP_ID,
        help="Sync Group ID",
    )
    link_parser.add_argument(
        "--master",
        default=None,
        help="Optional master emulator ID",
    )

    # broadcast
    bcast_parser = subparsers.add_parser(
        "broadcast", help="Broadcast a synchronized command to all linked emulators", parents=[common_parent]
    )
    bcast_parser.add_argument(
        "--cmd",
        required=True,
        help="Command string to execute across linked emulators (e.g. 'input tap 500 800')",
    )
    bcast_parser.add_argument(
        "--group",
        default=EmulatorConnector.DEFAULT_GROUP_ID,
        help="Target Sync Group ID",
    )

    # disconnect
    disc_parser = subparsers.add_parser(
        "disconnect", help="Disconnect one or all connected emulators", parents=[common_parent]
    )
    disc_parser.add_argument(
        "--id", dest="instance_id", help="Specific emulator ID to disconnect"
    )

    # status
    subparsers.add_parser(
        "status", help="Show current Connector Pool, Sync Hub, and Instance statuses", parents=[common_parent]
    )

    # profile-create
    p_create = subparsers.add_parser(
        "profile-create", help="Create one or multiple isolated anti-lag browser profiles", parents=[common_parent]
    )
    p_create.add_argument("--count", type=int, default=1, help="Number of profiles to create")
    p_create.add_argument("--prefix", default="profile", help="Prefix for profile IDs")
    p_create.add_argument("--type", default="auto", choices=["auto", "chrome", "edge", "brave"], help="Browser type")

    # profile-start
    p_start = subparsers.add_parser(
        "profile-start", help="Launch browser profile(s) with anti-lag optimization flags", parents=[common_parent]
    )
    p_start.add_argument("--id", dest="profile_id", help="Specific profile ID to start")
    p_start.add_argument("--all", action="store_true", help="Start all registered browser profiles")
    p_start.add_argument("--url", default="about:blank", help="Initial URL to open")

    # profile-stop
    p_stop = subparsers.add_parser(
        "profile-stop", help="Stop running browser profile(s)", parents=[common_parent]
    )
    p_stop.add_argument("--id", dest="profile_id", help="Specific profile ID to stop")
    p_stop.add_argument("--all", action="store_true", help="Stop all running browser profiles")

    # profile-list
    subparsers.add_parser(
        "profile-list", help="List all browser profiles with CDP port and live status", parents=[common_parent]
    )

    # profile-sync
    p_sync = subparsers.add_parser(
        "profile-sync", help="Synchronize actions across all connected browser profiles", parents=[common_parent]
    )
    p_sync.add_argument("--cmd", required=True, help="Action: 'goto <url>', 'scroll-down', 'click <sel>', 'type <txt>', 'eval <js>'")
    p_sync.add_argument("--group", default=EmulatorConnector.DEFAULT_GROUP_ID, help="Target Sync Group")

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    raw_argv = argv if argv is not None else sys.argv[1:]
    is_json = "--json" in raw_argv
    is_mock = "--mock" in raw_argv

    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "json", False):
        is_json = True
    if getattr(args, "mock", False):
        is_mock = True

    from src.core.browser_profile import BrowserProfileManager

    profile_mgr = BrowserProfileManager()
    adapter = CompositeDiscoveryAdapter(force_mock=is_mock)
    connector = EmulatorConnector(adapter=adapter)
    manager = InstanceManager(connector=connector)

    result: dict[str, Any]

    if args.command == "scan":
        connector.scan_emulators()
        status = connector.get_status()
        result = {
            "action": "scan",
            **status,
            "instances": manager.list_instances(auto_scan=False),
        }
    elif args.command == "connect":
        if args.instance_id:
            ep = connector.connect(args.instance_id)
            result = {
                "action": "connect_one",
                "endpoint": ep.to_dict(),
                **connector.get_status(),
                "instances": manager.list_instances(auto_scan=False),
            }
        else:
            conn_res = connector.connect_all(auto_link=not args.no_link)
            result = {
                "action": "connect_all",
                **conn_res,
                **connector.get_status(),
                "instances": manager.list_instances(auto_scan=False),
            }
    elif args.command == "link":
        group = connector.link_emulators(
            instance_ids=args.ids,
            group_id=args.group,
            master_id=args.master,
        )
        result = {
            "action": "link",
            "syncGroup": group.to_dict(),
            **connector.get_status(),
            "instances": manager.list_instances(auto_scan=False),
        }
    elif args.command == "broadcast":
        bcast = connector.broadcast_command(command=args.cmd, group_id=args.group)
        result = {
            "action": "broadcast",
            "broadcast": bcast,
            **connector.get_status(),
            "instances": manager.list_instances(auto_scan=False),
        }
    elif args.command == "disconnect":
        if args.instance_id:
            ep = connector.disconnect(args.instance_id)
            result = {
                "action": "disconnect_one",
                "endpoint": ep.to_dict(),
                **connector.get_status(),
                "instances": manager.list_instances(auto_scan=False),
            }
        else:
            disc_res = connector.disconnect_all()
            result = {
                "action": "disconnect_all",
                **disc_res,
                **connector.get_status(),
                "instances": manager.list_instances(auto_scan=False),
            }
    elif args.command == "status":
        result = {
            "action": "status",
            **connector.get_status(),
            "instances": manager.list_instances(auto_scan=True),
        }
    elif args.command == "profile-create":
        created = profile_mgr.create_profiles(
            count=args.count, prefix=args.prefix, browser_type=args.type
        )
        result = {
            "action": "profile_create",
            "createdCount": len(created),
            "profiles": [p.to_dict() for p in created],
        }
    elif args.command == "profile-start":
        if args.profile_id:
            res = profile_mgr.launch_profile(args.profile_id, initial_url=args.url)
            result = {"action": "profile_start_one", "result": res}
        else:
            all_res = profile_mgr.launch_all(initial_url=args.url)
            result = {"action": "profile_start_all", "results": all_res}
    elif args.command == "profile-stop":
        if args.profile_id:
            stopped = profile_mgr.stop_profile(args.profile_id)
            result = {"action": "profile_stop_one", "profileId": args.profile_id, "stopped": stopped}
        else:
            stopped_ids = profile_mgr.stop_all()
            result = {"action": "profile_stop_all", "stoppedIds": stopped_ids}
    elif args.command == "profile-list":
        profiles = profile_mgr.list_profiles()
        result = {"action": "profile_list", "count": len(profiles), "profiles": profiles}
    elif args.command == "profile-sync":
        # Connect & link all discovered profiles, then broadcast command
        connector.scan_emulators()
        connector.connect_all(auto_link=True, group_id=args.group)
        bcast = connector.broadcast_command(command=args.cmd, group_id=args.group)
        result = {
            "action": "profile_sync",
            "broadcast": bcast,
            **connector.get_status(),
            "instances": manager.list_instances(auto_scan=False),
        }
    else:
        if is_json:
            print(
                json.dumps(
                    {
                        "name": "Multi_Emulator",
                        "version": "0.1.0",
                        "description": "Multi Emulator ADR version for education",
                        **connector.get_status(),
                    }
                )
            )
            return 0
        return -1

    if is_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        _print_human_readable(result)

    return 0


def _print_human_readable(result: dict[str, Any]) -> None:
    action = result.get("action", "status").upper()

    if "profiles" in result and "createdCount" in result:
        print(f"=== Created {result['createdCount']} Browser Profile(s) ===")
        for p in result["profiles"]:
            print(f"  • {p['id']} ({p['name']}) | Port: {p['debug_port']} | Type: {p.get('browser_type')}")
        return

    if "profiles" in result and "count" in result:
        print(f"=== Registered Browser Profiles ({result['count']}) ===")
        for p in result["profiles"]:
            st = "● RUNNING" if p.get("isAlive") else "○ STOPPED"
            pid = f"(PID: {p['pid']})" if p.get("pid") else ""
            print(f"  {st} {p['id']:<14} | Port: {p['debug_port']} | {p['browser_type'].upper()} {pid}")
        return

    if action in ("PROFILE_START_ONE", "PROFILE_START_ALL"):
        print(f"=== Browser Launch Result: {action} ===")
        res = result.get("result") or result.get("results")
        print(json.dumps(res, indent=2))
        return

    summary = result.get("summary", {})
    print(
        f"=== Multi_Emulator Connector [{action}] ===\n"
        f"Discovered: {summary.get('discoveredCount', 0)} | "
        f"Connected: {summary.get('connectedCount', 0)} | "
        f"Synced: {summary.get('syncedCount', 0)} | "
        f"Sync Groups: {summary.get('activeSyncGroups', 0)}"
    )
    for ep in result.get("endpoints", []):
        role = " [MASTER]" if ep.get("isMaster") else ""
        grp = f" (Group: {ep['syncGroupId']})" if ep.get("syncGroupId") else ""
        print(
            f"  - {ep['id']} | {ep['name']} | {ep['host']}:{ep['port']} "
            f"| State: {ep['connectionState']}{role}{grp} — {ep.get('lastMessage', '')}"
        )
    if "broadcast" in result:
        bcast = result["broadcast"]
        print(
            f"\nBroadcast Command '{bcast['command']}' to {bcast['targetCount']} emulators/profiles:"
        )
        for item in bcast.get("results", []):
            print(f"  * [{item['instanceId']}] -> {item['output']}")


if __name__ == "__main__":
    sys.exit(run_cli())
