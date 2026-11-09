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
    parser = argparse.ArgumentParser(
        prog="multi-emulator",
        description="Multi_Emulator Connector & Sync Hub CLI (Educational ADR version)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON (used by Node.js IPC bridge)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force simulated Mock emulators during discovery",
    )

    subparsers = parser.add_subparsers(dest="command", help="Connector subcommands")

    # scan
    subparsers.add_parser("scan", help="Scan and discover all available emulators")

    # connect
    connect_parser = subparsers.add_parser(
        "connect", help="Connect to one or all discovered emulators and link them"
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
        "link", help="Link connected emulators together into a Sync Group"
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
        "broadcast", help="Broadcast a synchronized command to all linked emulators"
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
        "disconnect", help="Disconnect one or all connected emulators"
    )
    disc_parser.add_argument(
        "--id", dest="instance_id", help="Specific emulator ID to disconnect"
    )

    # status
    subparsers.add_parser(
        "status", help="Show current Connector Pool, Sync Hub, and Instance statuses"
    )

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    adapter = CompositeDiscoveryAdapter(force_mock=bool(args.mock))
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
    else:
        if args.json:
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

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        _print_human_readable(result)

    return 0


def _print_human_readable(result: dict[str, Any]) -> None:
    action = result.get("action", "status").upper()
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
            f"\nBroadcast Command '{bcast['command']}' to {bcast['targetCount']} emulators:"
        )
        for item in bcast.get("results", []):
            print(f"  * [{item['instanceId']}] -> {item['output']}")


if __name__ == "__main__":
    sys.exit(run_cli())
