"""Multi_Emulator Core Package — Emulator Discovery, Connector & Instance Management."""

from src.core.connector import (
    ConnectionState,
    EmulatorConnector,
    EmulatorEndpoint,
    SyncGroup,
)
from src.core.device_adapter import (
    ADBDeviceAdapter,
    CompositeDiscoveryAdapter,
    DeviceAdapter,
    MockDeviceAdapter,
)
from src.core.instance_manager import InstanceManager

__all__ = [
    "ConnectionState",
    "EmulatorConnector",
    "EmulatorEndpoint",
    "SyncGroup",
    "DeviceAdapter",
    "ADBDeviceAdapter",
    "MockDeviceAdapter",
    "CompositeDiscoveryAdapter",
    "InstanceManager",
]
