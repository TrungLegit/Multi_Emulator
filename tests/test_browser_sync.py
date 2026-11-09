"""Unit tests for Multi-Browser Profile Management, Anti-Lag flags, and Sync Broadcast.

Tests profile creation, anti-lag Chromium flags, BrowserProfileAdapter,
and synchronous command broadcast across multiple browser instances.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.browser_adapter import BrowserProfileAdapter
from src.core.browser_profile import (
    ANTI_LAG_CHROME_FLAGS,
    BrowserProfileConfig,
    BrowserProfileManager,
    CDPClient,
    detect_browser_executable,
)
from src.core.cli import run_cli
from src.core.connector import ConnectionState, EmulatorConnector
from src.core.device_adapter import CompositeDiscoveryAdapter, DiscoveredDevice


class TestBrowserSyncHub(unittest.TestCase):
    """Test suite for browser profiles and anti-lag synchronization."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.manager = BrowserProfileManager(base_dir=self.base_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_anti_lag_flags_have_memory_and_cpu_optimizations(self) -> None:
        """Verify presence of critical flags for low RAM and CPU usage."""
        self.assertIn("--mute-audio", ANTI_LAG_CHROME_FLAGS)
        self.assertIn("--disable-smooth-scrolling", ANTI_LAG_CHROME_FLAGS)
        self.assertIn("--disk-cache-size=33554432", ANTI_LAG_CHROME_FLAGS)
        self.assertIn("--disable-background-networking", ANTI_LAG_CHROME_FLAGS)
        self.assertIn("--no-first-run", ANTI_LAG_CHROME_FLAGS)

    def test_create_multiple_browser_profiles_and_manifest(self) -> None:
        """Test creating isolated profiles with distinct debug ports and directories."""
        profiles = self.manager.create_profiles(count=3, prefix="test_prof")
        self.assertEqual(len(profiles), 3)
        self.assertEqual(profiles[0].debug_port, 9222)
        self.assertEqual(profiles[1].debug_port, 9223)
        self.assertEqual(profiles[2].debug_port, 9224)

        # Verify disk isolation
        self.assertTrue(Path(profiles[0].user_data_dir).exists())
        self.assertTrue((self.base_dir / "profiles_manifest.json").exists())

        # Verify launch command includes anti-lag flags and debug port
        cmd = self.manager.build_launch_command(profiles[0], initial_url="https://example.com")
        cmd_str = " ".join(cmd)
        self.assertIn("--remote-debugging-port=9222", cmd_str)
        self.assertIn("--mute-audio", cmd_str)
        self.assertIn("https://example.com", cmd_str)

    def test_browser_profile_adapter_discovery(self) -> None:
        """Test BrowserProfileAdapter discovery within the connector architecture."""
        adapter = BrowserProfileAdapter(manager=self.manager, auto_seed_count=2)
        devices = adapter.scan()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].source, "browser_cdp")
        self.assertEqual(devices[0].emulator_type, "browser_profile")
        self.assertEqual(devices[0].port, 9222)
        self.assertEqual(devices[1].port, 9223)

    def test_browser_profile_adapter_command_execution(self) -> None:
        """Test parsing and command mapping for navigate, scroll, click, and type."""
        device = DiscoveredDevice(
            id="prof_01",
            name="Profile 1",
            host="127.0.0.1",
            port=9222,
            emulator_type="browser_profile",
            source="browser_cdp",
        )
        adapter = BrowserProfileAdapter(manager=self.manager)

        # Mock CDPClient methods
        with patch.object(CDPClient, "navigate", return_value={"ok": True, "url": "https://facebook.com"}):
            res_nav = adapter.execute_command(device, "goto https://facebook.com")
            self.assertTrue(res_nav["ok"])
            self.assertEqual(res_nav["action"], "navigate")

        with patch.object(CDPClient, "scroll", return_value={"ok": True}):
            res_scroll = adapter.execute_command(device, "scroll-down")
            self.assertTrue(res_scroll["ok"])
            self.assertEqual(res_scroll["action"], "scroll_down")

            res_swipe = adapter.execute_command(device, "input swipe 200 800 200 200")
            self.assertTrue(res_swipe["ok"])
            self.assertEqual(res_swipe["action"], "swipe_scroll")

        with patch.object(CDPClient, "click_element", return_value={"ok": True}):
            res_click = adapter.execute_command(device, "click button.submit-btn")
            self.assertTrue(res_click["ok"])
            self.assertEqual(res_click["action"], "click")

        with patch.object(CDPClient, "type_text", return_value={"ok": True}):
            res_type = adapter.execute_command(device, "type test_password")
            self.assertTrue(res_type["ok"])
            self.assertEqual(res_type["action"], "type")

    def test_composite_adapter_scans_both_browsers_and_emulators(self) -> None:
        """Verify CompositeDiscoveryAdapter aggregates browser profiles seamlessly."""
        browser_adapter = BrowserProfileAdapter(manager=self.manager, auto_seed_count=2)
        composite = CompositeDiscoveryAdapter(
            browser_adapter=browser_adapter,
            include_mock_when_empty=True,
            force_mock=False,
            include_browser_profiles=True,
        )

        devices = composite.scan()
        # Should contain at least 2 browser profiles
        browser_devs = [d for d in devices if d.source == "browser_cdp"]
        self.assertEqual(len(browser_devs), 2)

    def test_sync_broadcast_to_multiple_browser_profiles(self) -> None:
        """Test connecting multiple browser profiles into a SyncGroup and broadcasting actions."""
        browser_adapter = BrowserProfileAdapter(manager=self.manager, auto_seed_count=3)
        state_file = self.base_dir / "connector_state.json"
        connector = EmulatorConnector(adapter=browser_adapter, state_file=state_file)

        # 1. Connect all profiles
        with patch.object(BrowserProfileAdapter, "connect_device", return_value=(True, "Connected")):
            conn_res = connector.connect_all(auto_link=True)
            self.assertEqual(conn_res["connectedCount"], 3)
            self.assertIsNotNone(conn_res["syncGroup"])

        # 2. Broadcast action to all profiles
        with patch.object(CDPClient, "navigate", return_value={"ok": True}):
            bcast = connector.broadcast_command("goto https://google.com")
            self.assertEqual(bcast["targetCount"], 3)
            self.assertEqual(len(bcast["results"]), 3)
            self.assertTrue(all(item["ok"] for item in bcast["results"]))

    def test_cli_browser_profile_commands(self) -> None:
        """Test CLI subcommands for profile creation and listing."""
        code_create = run_cli(["profile-create", "--count", "2", "--prefix", "cli_test", "--json"])
        self.assertEqual(code_create, 0)

        code_list = run_cli(["profile-list", "--json"])
        self.assertEqual(code_list, 0)


if __name__ == "__main__":
    unittest.main()
