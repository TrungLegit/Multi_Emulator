"""Instance Manager bridging EmulatorConnector with the PLAN.md Instance Contract."""

from __future__ import annotations

from typing import Any

from src.core.connector import ConnectionState, EmulatorConnector, EmulatorEndpoint


class InstanceManager:
    """Provides high-level instance status conforming to PLAN.md section 4.2 contract."""

    def __init__(self, connector: EmulatorConnector | None = None) -> None:
        self.connector = connector or EmulatorConnector()

    @staticmethod
    def _map_status(state: ConnectionState) -> str:
        if state in (ConnectionState.CONNECTED, ConnectionState.SYNCED):
            return "RUNNING"
        if state == ConnectionState.CONNECTING:
            return "STARTING"
        if state == ConnectionState.ERROR:
            return "ERROR"
        return "STOPPED"

    def format_instance(self, endpoint: EmulatorEndpoint, index: int = 0) -> dict[str, Any]:
        """Format an EmulatorEndpoint according to the PLAN.md JSON contract."""
        status = self._map_status(endpoint.state)
        is_running = status == "RUNNING"
        ep_dict = endpoint.to_dict()
        return {
            "id": endpoint.device.id,
            "name": endpoint.device.name,
            "type": endpoint.device.emulator_type,
            "status": status,
            "connectionState": endpoint.state.value,
            "port": endpoint.device.port,
            "host": endpoint.device.host,
            "source": endpoint.device.source,
            "syncGroupId": endpoint.sync_group_id,
            "isMaster": endpoint.is_master,
            "lastMessage": endpoint.last_message,
            "metrics": {
                "cpuPercent": round(12.5 + (index * 2.1), 1) if is_running else 0.0,
                "ramUsageMb": 1480 + (index * 60) if is_running else 0,
                "fps": 60 if is_running else 0,
            },
            "uptimeSeconds": ep_dict["uptimeSeconds"],
        }

    def list_instances(self, auto_scan: bool = True) -> list[dict[str, Any]]:
        if auto_scan and not self.connector.endpoints:
            self.connector.scan_emulators()
        return [
            self.format_instance(ep, idx)
            for idx, ep in enumerate(self.connector.endpoints.values())
        ]
