"""Unit tests for the Multi_Emulator Discovery & Connector Engine.

Compatible with both `pytest` and standard library `python3 -m unittest`.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.core.connector import ConnectionState, EmulatorConnector
from src.core.device_adapter import (
    ADBDeviceAdapter,
    CompositeDiscoveryAdapter,
    MockDeviceAdapter,
)
from src.core.instance_manager import InstanceManager


class TestEmulatorConnector(unittest.TestCase):
    """Test suite for Emulator scanning, connecting, linking, and broadcasting."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "state.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scan_discovers_all_emulators(self) -> None:
        connector = EmulatorConnector(
            adapter=MockDeviceAdapter(),
            state_file=self.state_file,
        )

        endpoints = connector.scan_emulators()
        self.assertEqual(len(endpoints), 3)
        self.assertEqual(
            [ep.device.id for ep in endpoints], ["emu_01", "emu_02", "emu_03"]
        )
        self.assertTrue(
            all(ep.state == ConnectionState.DISCOVERED for ep in endpoints)
        )

    def test_connect_all_and_link_into_sync_hub(self) -> None:
        connector = EmulatorConnector(
            adapter=MockDeviceAdapter(),
            state_file=self.state_file,
        )

        result = connector.connect_all(auto_link=True)
        self.assertEqual(result["totalDiscovered"], 3)
        self.assertEqual(result["connectedCount"], 3)
        self.assertEqual(result["failedCount"], 0)
        self.assertIsNotNone(result["syncGroup"])
        self.assertEqual(
            result["syncGroup"]["groupId"], EmulatorConnector.DEFAULT_GROUP_ID
        )
        self.assertEqual(result["syncGroup"]["masterId"], "emu_01")
        self.assertEqual(
            result["syncGroup"]["memberIds"], ["emu_01", "emu_02", "emu_03"]
        )

        # Verify state persistence reload
        reloaded = EmulatorConnector(
            adapter=MockDeviceAdapter(),
            state_file=self.state_file,
        )
        status = reloaded.get_status()
        self.assertEqual(status["summary"]["syncedCount"], 3)
        self.assertEqual(status["summary"]["activeSyncGroups"], 1)

    def test_broadcast_command_across_linked_emulators(self) -> None:
        connector = EmulatorConnector(
            adapter=MockDeviceAdapter(),
            state_file=self.state_file,
        )
        connector.connect_all(auto_link=True)

        bcast = connector.broadcast_command("input tap 540 960")
        self.assertEqual(bcast["targetCount"], 3)
        self.assertEqual(len(bcast["results"]), 3)
        self.assertTrue(all(item["ok"] is True for item in bcast["results"]))
        self.assertEqual(
            [item["instanceId"] for item in bcast["results"]],
            ["emu_01", "emu_02", "emu_03"],
        )

    def test_adb_output_parser_and_instance_contract(self) -> None:
        adb_adapter = ADBDeviceAdapter(probe_ports=())
        sample_output = (
            "List of devices attached\n"
            "emulator-5554          device product:sdk_gphone64_x86_64 model:Pixel_6 device:emu64x\n"
            "127.0.0.1:62001        device product:nox model:Nox_Phone device:nox\n"
        )
        parsed = adb_adapter._parse_adb_devices(sample_output)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].port, 5554)
        self.assertEqual(parsed[0].name, "Pixel_6")
        self.assertEqual(parsed[1].port, 62001)
        self.assertEqual(parsed[1].name, "Nox_Phone")

        connector = EmulatorConnector(
            adapter=CompositeDiscoveryAdapter(force_mock=True),
            state_file=self.state_file,
        )
        connector.connect_all(auto_link=True)
        manager = InstanceManager(connector=connector)
        instances = manager.list_instances()
        self.assertEqual(len(instances), 3)
        first = instances[0]
        self.assertEqual(first["id"], "emu_01")
        self.assertEqual(first["status"], "RUNNING")
        self.assertEqual(first["connectionState"], "SYNCED")
        self.assertIn("cpuPercent", first["metrics"])
        self.assertIn("ramUsageMb", first["metrics"])
        self.assertIn("fps", first["metrics"])


if __name__ == "__main__":
    unittest.main()
