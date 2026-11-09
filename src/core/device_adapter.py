"""Device Adapter & Discovery strategies for Multi_Emulator (ADR-003 Adapter Pattern).

Provides:
- DeviceAdapter (ABC): Standard interface for scanning, connecting, and sending commands.
- ADBDeviceAdapter: Scans via `adb devices -l` and probes known local emulator TCP ports
  (Android Studio AVD/LDPlayer/BlueStacks: 5554-5584, Nox: 62001-62005, MEmu: 21503-21513).
- MockDeviceAdapter: Simulated emulators for educational / offline testing when no real
  emulator is running on the host machine.
- CompositeDiscoveryAdapter: Combines real ADB/TCP scanning with optional Mock fallback.
"""

from __future__ import annotations

import abc
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Any


# Known default local TCP port ranges for popular Android emulators
DEFAULT_AVD_PORTS: tuple[int, ...] = tuple(range(5554, 5566, 2)) + tuple(
    range(5555, 5567, 2)
)
NOX_PORTS: tuple[int, ...] = (62001, 62025, 62026, 62027)
MEMU_PORTS: tuple[int, ...] = (21503, 21513, 21523)


@dataclass
class DiscoveredDevice:
    """Represents a raw emulator endpoint found during a scan."""

    id: str
    name: str
    host: str = "127.0.0.1"
    port: int = 5554
    emulator_type: str = "android_x86"
    source: str = "adb"  # "adb" | "tcp_probe" | "mock"
    raw_state: str = "device"  # "device" | "offline" | "unauthorized" | "available"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def serial(self) -> str:
        """Return standard ADB serial string (e.g., emulator-5554 or 127.0.0.1:5555)."""
        if self.id.startswith("emulator-"):
            return self.id
        return f"{self.host}:{self.port}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "serial": self.serial,
            "type": self.emulator_type,
            "source": self.source,
            "rawState": self.raw_state,
            "metadata": self.metadata,
        }


class DeviceAdapter(abc.ABC):
    """Abstract base adapter for discovering and communicating with emulators."""

    @abc.abstractmethod
    def scan(self) -> list[DiscoveredDevice]:
        """Scan and return all currently detectable emulator endpoints."""

    @abc.abstractmethod
    def connect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        """Establish a connection handshake with the given emulator."""

    @abc.abstractmethod
    def disconnect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        """Close connection with the given emulator."""

    @abc.abstractmethod
    def execute_command(
        self, device: DiscoveredDevice, command: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a control or sync command on the connected emulator."""


class ADBDeviceAdapter(DeviceAdapter):
    """Real Android Emulator adapter using ADB CLI and local TCP port probing."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        probe_ports: tuple[int, ...] | None = None,
        tcp_timeout: float = 0.15,
    ) -> None:
        self.host = host
        self.probe_ports = (
            probe_ports
            if probe_ports is not None
            else (DEFAULT_AVD_PORTS + NOX_PORTS + MEMU_PORTS)
        )
        self.tcp_timeout = tcp_timeout
        self.adb_path = shutil.which("adb")

    def _parse_adb_devices(self, output: str) -> list[DiscoveredDevice]:
        """Parse `adb devices -l` text output into DiscoveredDevice objects."""
        discovered: list[DiscoveredDevice] = []
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if line.startswith("List of devices") or line.startswith("* daemon"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, raw_state = parts[0], parts[1]
            meta: dict[str, Any] = {}
            for token in parts[2:]:
                if ":" in token:
                    k, v = token.split(":", 1)
                    meta[k] = v

            port = 5554
            host = self.host
            if serial.startswith("emulator-"):
                try:
                    port = int(serial.split("-", 1)[1])
                except ValueError:
                    port = 5554 + idx * 2
            elif ":" in serial:
                h, p_str = serial.rsplit(":", 1)
                host = h
                try:
                    port = int(p_str)
                except ValueError:
                    port = 5555

            model = meta.get("model", meta.get("device", f"Android-Emulator-{port}"))
            discovered.append(
                DiscoveredDevice(
                    id=f"emu_{port}",
                    name=model,
                    host=host,
                    port=port,
                    emulator_type="android_x86",
                    source="adb",
                    raw_state=raw_state,
                    metadata={"serial": serial, **meta},
                )
            )
        return discovered

    def _scan_adb_cli(self) -> list[DiscoveredDevice]:
        if not self.adb_path:
            return []
        try:
            proc = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            if proc.returncode == 0:
                return self._parse_adb_devices(proc.stdout)
        except (subprocess.SubprocessError, OSError):
            pass
        return []

    def _probe_tcp_port(self, port: int) -> bool:
        """Check if a local TCP port is listening (indicating an active emulator daemon)."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.tcp_timeout)
            try:
                return sock.connect_ex((self.host, port)) == 0
            except OSError:
                return False

    def _classify_port(self, port: int) -> tuple[str, str]:
        if port in NOX_PORTS:
            return ("nox_android", f"NoxPlayer-{port}")
        if port in MEMU_PORTS:
            return ("memu_android", f"MEmu-{port}")
        return ("android_x86", f"AVD-Emulator-{port}")

    def scan(self) -> list[DiscoveredDevice]:
        devices_by_port: dict[int, DiscoveredDevice] = {}

        # 1. Scan via `adb devices -l` if adb is installed
        for dev in self._scan_adb_cli():
            devices_by_port[dev.port] = dev

        # 2. Scan known local TCP ports for running emulators not yet attached to adb
        for port in self.probe_ports:
            if port in devices_by_port:
                continue
            if self._probe_tcp_port(port):
                emu_type, name = self._classify_port(port)
                devices_by_port[port] = DiscoveredDevice(
                    id=f"emu_{port}",
                    name=name,
                    host=self.host,
                    port=port,
                    emulator_type=emu_type,
                    source="tcp_probe",
                    raw_state="available",
                    metadata={"probedPort": port},
                )

        return list(devices_by_port.values())

    def connect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        """Connect via `adb connect` if available, or verify TCP socket reachability."""
        if self.adb_path:
            target = f"{device.host}:{device.port}"
            try:
                proc = subprocess.run(
                    [self.adb_path, "connect", target],
                    capture_output=True,
                    text=True,
                    timeout=4.0,
                    check=False,
                )
                out = (proc.stdout + proc.stderr).strip()
                if "connected to" in out.lower() or "already connected" in out.lower():
                    return True, out
                if device.raw_state == "device":
                    return True, f"Verified active ADB transport for {device.serial}"
            except (subprocess.SubprocessError, OSError) as exc:
                return False, f"ADB connect error: {exc}"

        # Fallback to socket handshake check
        if self._probe_tcp_port(device.port):
            return True, f"Connected to {device.host}:{device.port} via TCP socket"
        return False, f"Endpoint {device.host}:{device.port} is unreachable"

    def disconnect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        if self.adb_path:
            target = f"{device.host}:{device.port}"
            try:
                subprocess.run(
                    [self.adb_path, "disconnect", target],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
            except (subprocess.SubprocessError, OSError):
                pass
        return True, f"Disconnected from {device.id} ({device.host}:{device.port})"

    def execute_command(
        self, device: DiscoveredDevice, command: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        if self.adb_path and device.raw_state == "device":
            serial = device.metadata.get("serial", device.serial)
            try:
                proc = subprocess.run(
                    [self.adb_path, "-s", serial, "shell", command],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                    check=False,
                )
                return {
                    "instanceId": device.id,
                    "ok": proc.returncode == 0,
                    "command": command,
                    "output": proc.stdout.strip() or proc.stderr.strip(),
                }
            except (subprocess.SubprocessError, OSError) as exc:
                return {
                    "instanceId": device.id,
                    "ok": False,
                    "command": command,
                    "output": str(exc),
                }

        return {
            "instanceId": device.id,
            "ok": True,
            "command": command,
            "payload": payload,
            "output": f"[TCP-Bridge:{device.port}] Executed '{command}'",
        }


class MockDeviceAdapter(DeviceAdapter):
    """Simulated emulator adapter for educational demos and testing without heavy AVDs."""

    DEFAULT_MOCK_EMULATORS: tuple[dict[str, Any], ...] = (
        {
            "id": "emu_01",
            "name": "Emulator-Instance-1 (Pixel 6)",
            "port": 5554,
            "emulator_type": "android_x86",
            "metadata": {"androidVersion": "13.0", "resolution": "1080x2400", "dpi": 420},
        },
        {
            "id": "emu_02",
            "name": "Emulator-Instance-2 (Pixel 6)",
            "port": 5556,
            "emulator_type": "android_x86",
            "metadata": {"androidVersion": "13.0", "resolution": "1080x2400", "dpi": 420},
        },
        {
            "id": "emu_03",
            "name": "Emulator-Instance-3 (Tablet Nexus)",
            "port": 5558,
            "emulator_type": "android_x86",
            "metadata": {"androidVersion": "12L", "resolution": "1600x2560", "dpi": 320},
        },
    )

    def __init__(self, mock_presets: list[dict[str, Any]] | None = None) -> None:
        presets = (
            mock_presets
            if mock_presets is not None
            else list(self.DEFAULT_MOCK_EMULATORS)
        )
        self._devices: list[DiscoveredDevice] = [
            DiscoveredDevice(
                id=item["id"],
                name=item["name"],
                host=item.get("host", "127.0.0.1"),
                port=int(item["port"]),
                emulator_type=item.get("emulator_type", "android_x86"),
                source="mock",
                raw_state="available",
                metadata=dict(item.get("metadata", {})),
            )
            for item in presets
        ]

    def scan(self) -> list[DiscoveredDevice]:
        return list(self._devices)

    def connect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        return (
            True,
            f"Connected to simulated emulator {device.name} on {device.host}:{device.port}",
        )

    def disconnect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        return True, f"Disconnected simulated emulator {device.name} ({device.id})"

    def execute_command(
        self, device: DiscoveredDevice, command: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = payload or {}
        return {
            "instanceId": device.id,
            "name": device.name,
            "port": device.port,
            "ok": True,
            "command": command,
            "payload": payload,
            "output": f"[Mock-ADB:{device.port}] Executed '{command}' successfully",
        }


class CompositeDiscoveryAdapter(DeviceAdapter):
    """Combines ADB, Browser Profiles, and Mock discovery into a unified hub."""

    def __init__(
        self,
        adb_adapter: ADBDeviceAdapter | None = None,
        mock_adapter: MockDeviceAdapter | None = None,
        browser_adapter: DeviceAdapter | None = None,
        include_mock_when_empty: bool = True,
        force_mock: bool = False,
        include_browser_profiles: bool = True,
    ) -> None:
        self.adb_adapter = adb_adapter or ADBDeviceAdapter()
        self.mock_adapter = mock_adapter or MockDeviceAdapter()
        self.include_mock_when_empty = include_mock_when_empty
        self.force_mock = force_mock
        self.include_browser_profiles = include_browser_profiles

        if browser_adapter is not None:
            self.browser_adapter = browser_adapter
        else:
            from src.core.browser_adapter import BrowserProfileAdapter

            self.browser_adapter = BrowserProfileAdapter()

    def scan(self) -> list[DiscoveredDevice]:
        if self.force_mock:
            return self.mock_adapter.scan()

        all_devices: list[DiscoveredDevice] = []

        # 1. Discover browser profiles
        if self.include_browser_profiles and self.browser_adapter:
            try:
                all_devices.extend(self.browser_adapter.scan())
            except Exception:
                pass

        # 2. Discover real ADB / emulator endpoints
        real_devices = self.adb_adapter.scan()
        if real_devices:
            all_devices.extend(real_devices)

        if all_devices:
            return all_devices

        if self.include_mock_when_empty:
            return self.mock_adapter.scan()

        return []

    def _select_adapter(self, device: DiscoveredDevice) -> DeviceAdapter:
        if device.source == "browser_cdp" or device.emulator_type == "browser_profile":
            return self.browser_adapter
        if device.source == "mock":
            return self.mock_adapter
        return self.adb_adapter

    def connect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        return self._select_adapter(device).connect_device(device)

    def disconnect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        return self._select_adapter(device).disconnect_device(device)

    def execute_command(
        self, device: DiscoveredDevice, command: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self._select_adapter(device).execute_command(device, command, payload)
