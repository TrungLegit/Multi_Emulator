"""Browser Profile DeviceAdapter for Multi_Emulator Connector Hub.

Plugs directly into Trung & Chương's DeviceAdapter & SyncGroup architecture,
enabling multi-browser profile discovery, linking, and synchronized broadcast actions.
"""

from __future__ import annotations

import re
from typing import Any

from src.core.browser_profile import (
    BrowserProfileConfig,
    BrowserProfileManager,
    CDPClient,
)
from src.core.device_adapter import DeviceAdapter, DiscoveredDevice


class BrowserProfileAdapter(DeviceAdapter):
    """Integrates isolated browser profiles into the Multi_Emulator Sync Hub."""

    def __init__(
        self,
        manager: BrowserProfileManager | None = None,
        auto_seed_count: int = 3,
    ) -> None:
        self.manager = manager or BrowserProfileManager()
        self.auto_seed_count = auto_seed_count

    def scan(self) -> list[DiscoveredDevice]:
        """Scan and discover all registered browser profiles."""
        profiles = self.manager._profiles
        # Auto seed default profiles on first run if empty
        if not profiles and self.auto_seed_count > 0:
            self.manager.create_profiles(count=self.auto_seed_count)
            profiles = self.manager._profiles

        devices: list[DiscoveredDevice] = []
        for p in profiles.values():
            cdp = CDPClient(port=p.debug_port, timeout=0.15)
            is_running = cdp.is_alive()
            devices.append(
                DiscoveredDevice(
                    id=p.id,
                    name=f"{p.name} ({p.browser_type.upper()})",
                    host="127.0.0.1",
                    port=p.debug_port,
                    emulator_type="browser_profile",
                    source="browser_cdp",
                    raw_state="device" if is_running else "available",
                    metadata={
                        "debugPort": p.debug_port,
                        "browserType": p.browser_type,
                        "userDataDir": p.user_data_dir,
                        "isRunning": is_running,
                        "pid": p.pid,
                    },
                )
            )
        return devices

    def connect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        """Handshake with the browser profile, auto-launching if currently stopped."""
        cdp = CDPClient(port=device.port, timeout=0.3)
        if not cdp.is_alive():
            # Check if this profile exists in manifest
            if device.id in self.manager._profiles:
                res = self.manager.launch_profile(device.id)
                if res.get("status") == "ERROR":
                    return False, f"Failed to launch browser profile {device.id}: {res.get('error')}"
            else:
                return True, f"Browser profile {device.id} is offline on port {device.port}"

        # Fetch browser version for metadata verification
        ver = cdp.get_version()
        browser_info = ver.get("Browser", "Chromium/CDP")
        return True, f"Connected to {device.name} [{browser_info}] on CDP port {device.port}"

    def disconnect_device(self, device: DiscoveredDevice) -> tuple[bool, str]:
        """Disconnect session from the browser profile."""
        return True, f"Disconnected browser profile {device.name} ({device.id})"

    def execute_command(
        self, device: DiscoveredDevice, command: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a synchronized action across this browser profile."""
        payload = payload or {}
        cmd = command.strip()
        cdp = CDPClient(port=device.port, timeout=3.0)

        # 1. Navigation: "goto <url>" | "nav <url>" | "open <url>" | raw url
        if (
            cmd.startswith("goto ")
            or cmd.startswith("nav ")
            or cmd.startswith("open ")
            or cmd.startswith("http://")
            or cmd.startswith("https://")
        ):
            url = re.sub(r"^(goto|nav|open)\s+", "", cmd).strip()
            nav_res = cdp.navigate(url)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": nav_res.get("ok", True),
                "command": command,
                "action": "navigate",
                "output": f"[{device.id}] Navigated to '{url}'",
                "details": nav_res,
            }

        # 2. Scroll actions: "scroll-down" | "scroll-up" | "scroll <x> <y>"
        if cmd == "scroll-down" or cmd == "scroll":
            scroll_res = cdp.scroll(delta_x=0, delta_y=500)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": scroll_res.get("ok", True),
                "command": command,
                "action": "scroll_down",
                "output": f"[{device.id}] Scrolled down by 500px",
                "details": scroll_res,
            }
        if cmd == "scroll-up":
            scroll_res = cdp.scroll(delta_x=0, delta_y=-500)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": scroll_res.get("ok", True),
                "command": command,
                "action": "scroll_up",
                "output": f"[{device.id}] Scrolled up by 500px",
                "details": scroll_res,
            }
        if cmd.startswith("scroll "):
            parts = cmd.split()
            dy = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 500
            dx = int(parts[2]) if len(parts) > 2 and parts[2].lstrip("-").isdigit() else 0
            scroll_res = cdp.scroll(delta_x=dx, delta_y=dy)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": scroll_res.get("ok", True),
                "command": command,
                "action": "scroll",
                "output": f"[{device.id}] Scrolled by dx={dx}, dy={dy}",
                "details": scroll_res,
            }

        # Mobile swipe compatibility: "input swipe x1 y1 x2 y2 ..."
        if cmd.startswith("input swipe"):
            parts = cmd.split()
            if len(parts) >= 5:
                y1 = int(parts[3])
                y2 = int(parts[4])
                delta_y = y1 - y2
                scroll_res = cdp.scroll(delta_x=0, delta_y=delta_y)
                return {
                    "instanceId": device.id,
                    "name": device.name,
                    "port": device.port,
                    "ok": scroll_res.get("ok", True),
                    "command": command,
                    "action": "swipe_scroll",
                    "output": f"[{device.id}] Swiped scroll delta_y={delta_y}",
                    "details": scroll_res,
                }

        # 3. Click actions: "click <selector>" | "click-coords <x> <y>" | "input tap <x> <y>"
        if cmd.startswith("click "):
            selector = cmd[6:].strip()
            click_res = cdp.click_element(selector)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": click_res.get("ok", True),
                "command": command,
                "action": "click",
                "output": f"[{device.id}] Clicked selector '{selector}'",
                "details": click_res,
            }
        if cmd.startswith("input tap ") or cmd.startswith("tap "):
            parts = cmd.split()
            x = int(parts[2]) if cmd.startswith("input tap") else int(parts[1])
            y = int(parts[3]) if cmd.startswith("input tap") else int(parts[2])
            tap_js = f"document.elementFromPoint({x}, {y})?.click();"
            tap_res = cdp.execute_js(tap_js)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": tap_res.get("ok", True),
                "command": command,
                "action": "tap",
                "output": f"[{device.id}] Tapped at coordinates ({x}, {y})",
                "details": tap_res,
            }

        # 4. Type actions: "type <text>" | "input text <text>"
        if cmd.startswith("type ") or cmd.startswith("input text "):
            text = cmd[5:].strip() if cmd.startswith("type ") else cmd[11:].strip()
            type_res = cdp.type_text(text=text)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": type_res.get("ok", True),
                "command": command,
                "action": "type",
                "output": f"[{device.id}] Typed text '{text}'",
                "details": type_res,
            }

        # 5. Evaluate JavaScript: "eval <js>" | "js <js>"
        if cmd.startswith("eval ") or cmd.startswith("js "):
            script = cmd[5:].strip() if cmd.startswith("eval ") else cmd[3:].strip()
            eval_res = cdp.execute_js(script)
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": eval_res.get("ok", True),
                "command": command,
                "action": "eval",
                "output": f"[{device.id}] Evaluated JS: {eval_res.get('value')}",
                "details": eval_res,
            }

        # 6. Page reload
        if cmd in ("reload", "refresh"):
            rel_res = cdp.execute_js("window.location.reload(); true;")
            return {
                "instanceId": device.id,
                "name": device.name,
                "port": device.port,
                "ok": rel_res.get("ok", True),
                "command": command,
                "action": "reload",
                "output": f"[{device.id}] Page reloaded",
                "details": rel_res,
            }

        # 7. Fallback: run as raw JS expression or report unknown
        fallback_res = cdp.execute_js(cmd)
        return {
            "instanceId": device.id,
            "name": device.name,
            "port": device.port,
            "ok": fallback_res.get("ok", True),
            "command": command,
            "action": "execute",
            "output": f"[{device.id}] Executed command '{command}'",
            "details": fallback_res,
        }
