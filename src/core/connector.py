"""Emulator Connector & Sync Hub for Multi_Emulator.

Handles:
1. Scanning / Discovering all existing emulators on the host (ADB, TCP ports, or Mock).
2. Connecting to individual or all discovered emulators concurrently.
3. Linking connected emulators together into a Sync Group (Sync Hub) so they can
   exchange state and receive broadcast commands in parallel.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.device_adapter import (
    CompositeDiscoveryAdapter,
    DeviceAdapter,
    DiscoveredDevice,
)


class ConnectionState(str, Enum):
    """Lifecycle states of an emulator inside the Connector Pool."""

    DISCOVERED = "DISCOVERED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    SYNCED = "SYNCED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


@dataclass
class EmulatorEndpoint:
    """State of a discovered emulator managed by EmulatorConnector."""

    device: DiscoveredDevice
    state: ConnectionState = ConnectionState.DISCOVERED
    connected_at: float | None = None
    last_message: str = "Discovered via scan"
    sync_group_id: str | None = None
    is_master: bool = False

    def to_dict(self) -> dict[str, Any]:
        uptime = (
            int(max(0.0, time.time() - self.connected_at))
            if self.connected_at and self.state in (ConnectionState.CONNECTED, ConnectionState.SYNCED)
            else 0
        )
        return {
            **self.device.to_dict(),
            "connectionState": self.state.value,
            "connectedAt": self.connected_at,
            "uptimeSeconds": uptime,
            "lastMessage": self.last_message,
            "syncGroupId": self.sync_group_id,
            "isMaster": self.is_master,
        }


@dataclass
class SyncGroup:
    """Represents a cluster of emulators linked together for synchronized actions."""

    group_id: str
    name: str
    member_ids: list[str] = field(default_factory=list)
    master_id: str | None = None
    created_at: float = field(default_factory=time.time)
    last_sync_command: str | None = None
    last_sync_timestamp: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "groupId": self.group_id,
            "name": self.name,
            "memberIds": list(self.member_ids),
            "memberCount": len(self.member_ids),
            "masterId": self.master_id,
            "createdAt": self.created_at,
            "lastSyncCommand": self.last_sync_command,
            "lastSyncTimestamp": self.last_sync_timestamp,
        }


class EmulatorConnector:
    """Discovers available emulators, connects them, and links them into a Sync Hub."""

    DEFAULT_GROUP_ID = "sync_hub_default"

    def __init__(
        self,
        adapter: DeviceAdapter | None = None,
        state_file: str | Path | None = None,
        max_workers: int = 8,
    ) -> None:
        self.adapter: DeviceAdapter = adapter or CompositeDiscoveryAdapter()
        self.max_workers = max_workers
        default_state_path = Path(
            os.environ.get(
                "MULTI_EMULATOR_STATE_FILE",
                Path(__file__).resolve().parents[2] / ".connector_state.json",
            )
        )
        self.state_file: Path | None = (
            Path(state_file) if state_file is not None else default_state_path
        )
        self.endpoints: dict[str, EmulatorEndpoint] = {}
        self.sync_groups: dict[str, SyncGroup] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # State Persistence (for seamless CLI <-> Node.js IPC coordination)
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if not self.state_file or not self.state_file.exists():
            return
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            for ep_data in data.get("endpoints", []):
                dev = DiscoveredDevice(
                    id=ep_data["id"],
                    name=ep_data["name"],
                    host=ep_data.get("host", "127.0.0.1"),
                    port=int(ep_data["port"]),
                    emulator_type=ep_data.get("type", "android_x86"),
                    source=ep_data.get("source", "mock"),
                    raw_state=ep_data.get("rawState", "available"),
                    metadata=ep_data.get("metadata", {}),
                )
                self.endpoints[dev.id] = EmulatorEndpoint(
                    device=dev,
                    state=ConnectionState(ep_data.get("connectionState", "DISCOVERED")),
                    connected_at=ep_data.get("connectedAt"),
                    last_message=ep_data.get("lastMessage", ""),
                    sync_group_id=ep_data.get("syncGroupId"),
                    is_master=bool(ep_data.get("isMaster", False)),
                )
            for grp_data in data.get("syncGroups", []):
                grp = SyncGroup(
                    group_id=grp_data["groupId"],
                    name=grp_data.get("name", "Default Sync Hub"),
                    member_ids=list(grp_data.get("memberIds", [])),
                    master_id=grp_data.get("masterId"),
                    created_at=grp_data.get("createdAt", time.time()),
                    last_sync_command=grp_data.get("lastSyncCommand"),
                    last_sync_timestamp=grp_data.get("lastSyncTimestamp"),
                )
                self.sync_groups[grp.group_id] = grp
        except (OSError, ValueError, KeyError):
            pass

    def _save_state(self) -> None:
        if not self.state_file:
            return
        try:
            payload = {
                "updatedAt": int(time.time() * 1000),
                "endpoints": [ep.to_dict() for ep in self.endpoints.values()],
                "syncGroups": [grp.to_dict() for grp in self.sync_groups.values()],
            }
            self.state_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Step 1: Scan / Discover all existing emulators
    # ------------------------------------------------------------------
    def scan_emulators(self) -> list[EmulatorEndpoint]:
        """Scan for all currently available emulators and update the connector pool."""
        discovered_devices = self.adapter.scan()
        for dev in discovered_devices:
            if dev.id in self.endpoints:
                existing = self.endpoints[dev.id]
                existing.device = dev
            else:
                self.endpoints[dev.id] = EmulatorEndpoint(
                    device=dev,
                    state=ConnectionState.DISCOVERED,
                    last_message=f"Discovered via {dev.source} ({dev.host}:{dev.port})",
                )
        self._save_state()
        return list(self.endpoints.values())

    # ------------------------------------------------------------------
    # Step 2: Connect to individual or all discovered emulators
    # ------------------------------------------------------------------
    def connect(self, instance_id: str) -> EmulatorEndpoint:
        """Connect to a single discovered emulator by ID."""
        if instance_id not in self.endpoints:
            self.scan_emulators()
        if instance_id not in self.endpoints:
            raise KeyError(f"Emulator '{instance_id}' not found in discovered pool.")

        endpoint = self.endpoints[instance_id]
        endpoint.state = ConnectionState.CONNECTING
        ok, message = self.adapter.connect_device(endpoint.device)
        if ok:
            endpoint.state = (
                ConnectionState.SYNCED
                if endpoint.sync_group_id
                else ConnectionState.CONNECTED
            )
            if endpoint.connected_at is None:
                endpoint.connected_at = time.time()
            endpoint.last_message = message
        else:
            endpoint.state = ConnectionState.ERROR
            endpoint.last_message = message

        self._save_state()
        return endpoint

    def connect_all(self, auto_link: bool = True) -> dict[str, Any]:
        """Scan (if needed), connect all discovered emulators in parallel, and link them."""
        if not self.endpoints:
            self.scan_emulators()

        target_ids = list(self.endpoints.keys())
        connected_ids: list[str] = []
        failed_ids: list[str] = []

        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(target_ids)))) as pool:
            future_map = {
                pool.submit(self.connect, instance_id): instance_id
                for instance_id in target_ids
            }
            for future in as_completed(future_map):
                ep = future.result()
                if ep.state in (ConnectionState.CONNECTED, ConnectionState.SYNCED):
                    connected_ids.append(ep.device.id)
                else:
                    failed_ids.append(ep.device.id)

        connected_ids.sort()
        sync_group: SyncGroup | None = None
        if auto_link and connected_ids:
            sync_group = self.link_emulators(
                instance_ids=connected_ids,
                group_id=self.DEFAULT_GROUP_ID,
                group_name="Primary Multi-Emulator Sync Hub",
                master_id=connected_ids[0],
            )

        self._save_state()
        return {
            "totalDiscovered": len(target_ids),
            "connectedCount": len(connected_ids),
            "failedCount": len(failed_ids),
            "connectedIds": connected_ids,
            "failedIds": failed_ids,
            "syncGroup": sync_group.to_dict() if sync_group else None,
            "endpoints": [ep.to_dict() for ep in self.endpoints.values()],
        }

    # ------------------------------------------------------------------
    # Step 3: Link Emulators Together into a Sync Hub & Broadcast Commands
    # ------------------------------------------------------------------
    def link_emulators(
        self,
        instance_ids: list[str] | None = None,
        group_id: str = DEFAULT_GROUP_ID,
        group_name: str = "Primary Multi-Emulator Sync Hub",
        master_id: str | None = None,
    ) -> SyncGroup:
        """Link multiple connected emulators together into a synchronized cluster."""
        if instance_ids is None:
            instance_ids = [
                ep.device.id
                for ep in self.endpoints.values()
                if ep.state in (ConnectionState.CONNECTED, ConnectionState.SYNCED)
            ]

        valid_members: list[str] = []
        for iid in instance_ids:
            if iid not in self.endpoints:
                continue
            ep = self.endpoints[iid]
            if ep.state not in (ConnectionState.CONNECTED, ConnectionState.SYNCED):
                ep = self.connect(iid)
            if ep.state in (ConnectionState.CONNECTED, ConnectionState.SYNCED):
                valid_members.append(iid)

        resolved_master = (
            master_id
            if (master_id and master_id in valid_members)
            else (valid_members[0] if valid_members else None)
        )

        # Update endpoint membership flags
        for ep in self.endpoints.values():
            if ep.device.id in valid_members:
                ep.sync_group_id = group_id
                ep.state = ConnectionState.SYNCED
                ep.is_master = ep.device.id == resolved_master
                role_label = "MASTER" if ep.is_master else "PEER"
                ep.last_message = f"Linked in {group_id} as {role_label}"
            elif ep.sync_group_id == group_id:
                ep.sync_group_id = None
                ep.is_master = False
                if ep.state == ConnectionState.SYNCED:
                    ep.state = ConnectionState.CONNECTED

        group = SyncGroup(
            group_id=group_id,
            name=group_name,
            member_ids=valid_members,
            master_id=resolved_master,
        )
        self.sync_groups[group_id] = group
        self._save_state()
        return group

    def broadcast_command(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
        group_id: str = DEFAULT_GROUP_ID,
    ) -> dict[str, Any]:
        """Broadcast a command concurrently across all emulators linked in a Sync Group."""
        if group_id not in self.sync_groups:
            raise KeyError(f"Sync Group '{group_id}' does not exist. Link emulators first.")

        group = self.sync_groups[group_id]
        member_endpoints = [
            self.endpoints[mid]
            for mid in group.member_ids
            if mid in self.endpoints
            and self.endpoints[mid].state in (ConnectionState.CONNECTED, ConnectionState.SYNCED)
        ]

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, max(1, len(member_endpoints)))
        ) as pool:
            future_map = {
                pool.submit(
                    self.adapter.execute_command, ep.device, command, payload
                ): ep
                for ep in member_endpoints
            }
            for future in as_completed(future_map):
                ep = future_map[future]
                res = future.result()
                ep.last_message = f"Synced cmd: {command}"
                results.append(res)

        results.sort(key=lambda item: item.get("instanceId", ""))
        now_ts = time.time()
        group.last_sync_command = command
        group.last_sync_timestamp = now_ts
        self._save_state()

        return {
            "groupId": group_id,
            "command": command,
            "timestamp": int(now_ts * 1000),
            "targetCount": len(member_endpoints),
            "results": results,
        }

    # ------------------------------------------------------------------
    # Disconnect & Status Inspection
    # ------------------------------------------------------------------
    def disconnect(self, instance_id: str) -> EmulatorEndpoint:
        if instance_id not in self.endpoints:
            raise KeyError(f"Emulator '{instance_id}' not found.")

        ep = self.endpoints[instance_id]
        _, msg = self.adapter.disconnect_device(ep.device)
        ep.state = ConnectionState.DISCONNECTED
        ep.connected_at = None
        ep.is_master = False
        old_group = ep.sync_group_id
        ep.sync_group_id = None
        ep.last_message = msg

        if old_group and old_group in self.sync_groups:
            grp = self.sync_groups[old_group]
            if instance_id in grp.member_ids:
                grp.member_ids.remove(instance_id)
            if grp.master_id == instance_id:
                grp.master_id = grp.member_ids[0] if grp.member_ids else None
                if grp.master_id and grp.master_id in self.endpoints:
                    self.endpoints[grp.master_id].is_master = True

        self._save_state()
        return ep

    def disconnect_all(self) -> dict[str, Any]:
        disconnected: list[str] = []
        for iid in list(self.endpoints.keys()):
            self.disconnect(iid)
            disconnected.append(iid)
        self.sync_groups.clear()
        self._save_state()
        return {
            "disconnectedCount": len(disconnected),
            "disconnectedIds": disconnected,
            "endpoints": [ep.to_dict() for ep in self.endpoints.values()],
        }

    def get_status(self) -> dict[str, Any]:
        endpoints_list = [ep.to_dict() for ep in self.endpoints.values()]
        connected_count = sum(
            1
            for ep in self.endpoints.values()
            if ep.state in (ConnectionState.CONNECTED, ConnectionState.SYNCED)
        )
        synced_count = sum(
            1 for ep in self.endpoints.values() if ep.state == ConnectionState.SYNCED
        )
        return {
            "summary": {
                "discoveredCount": len(endpoints_list),
                "connectedCount": connected_count,
                "syncedCount": synced_count,
                "activeSyncGroups": len(self.sync_groups),
            },
            "endpoints": endpoints_list,
            "syncGroups": [grp.to_dict() for grp in self.sync_groups.values()],
        }
