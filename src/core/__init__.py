"""Multi_Emulator Core Package — Emulator Discovery, Connector & Instance Management."""

from src.core.browser_adapter import BrowserProfileAdapter
from src.core.browser_profile import (
    ANTI_LAG_CHROME_FLAGS,
    BrowserProfileConfig,
    BrowserProfileManager,
    CDPClient,
    detect_browser_executable,
)
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
    DiscoveredDevice,
    MockDeviceAdapter,
)
from src.core.instance_manager import InstanceManager

__all__ = [
    "ConnectionState",
    "EmulatorConnector",
    "EmulatorEndpoint",
    "SyncGroup",
    "DeviceAdapter",
    "DiscoveredDevice",
    "ADBDeviceAdapter",
    "MockDeviceAdapter",
    "CompositeDiscoveryAdapter",
    "BrowserProfileAdapter",
    "BrowserProfileConfig",
    "BrowserProfileManager",
    "CDPClient",
    "detect_browser_executable",
    "ANTI_LAG_CHROME_FLAGS",
    "InstanceManager",
]
