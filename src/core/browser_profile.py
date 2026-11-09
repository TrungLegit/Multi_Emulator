"""Multi-Browser Profile Manager & Ultra-Low-Lag Optimizer.

Manages multiple independent browser profiles (Chrome, Edge, Brave, Chromium)
with anti-lag flags and Chrome DevTools Protocol (CDP) synchronization.
"""

from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Default port range allocated for Chrome DevTools Protocol remote debugging
DEFAULT_BASE_DEBUG_PORT = 9222

# Comprehensive Anti-Lag & Resource-Optimization flags for Chromium-based browsers
ANTI_LAG_CHROME_FLAGS: list[str] = [
    # 1. Disable background telemetry, sync, and update overhead
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-dev-shm-usage",
    "--disable-domain-reliability",
    "--disable-extensions",
    "--disable-sync",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    # 2. Disable heavy background browser features
    (
        "--disable-features=Translate,OptimizationHints,MediaRouter,"
        "DialMediaRouteProvider,CalculateNativeWinOcclusion,"
        "InterestFeedContentSuggestions,CertificateTransparencyComponentUpdater"
    ),
    # 3. Audio & Rendering optimizations (prevents audio interrupts & high GPU render queues)
    "--mute-audio",
    "--disable-smooth-scrolling",
    # 4. Limit disk cache to prevent I/O disk thrashing when running 10+ profiles
    "--disk-cache-size=33554432",  # 32 MB max disk cache
    "--media-cache-size=33554432",  # 32 MB max media cache
    # 5. Process & credential optimizations
    "--password-store=basic",
    "--use-mock-keychain",
    "--force-color-profile=srgb",
]


def detect_browser_executable(preferred: str = "auto") -> str | None:
    """Detect available Chromium-based browser executable on Windows or Linux."""
    env_bin = os.environ.get("BROWSER_BIN")
    if env_bin and Path(env_bin).exists():
        return env_bin

    is_win = platform.system() == "Windows" or os.name == "nt"

    if is_win:
        prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\Default\AppData\Local")

        candidates: list[str] = [
            # Google Chrome
            os.path.join(prog_files, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog_files_x86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local_app_data, r"Google\Chrome\Application\chrome.exe"),
            # Microsoft Edge
            os.path.join(prog_files_x86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(prog_files, r"Microsoft\Edge\Application\msedge.exe"),
            # Brave
            os.path.join(prog_files, r"BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.join(local_app_data, r"BraveSoftware\Brave-Browser\Application\brave.exe"),
            # Cốc Cốc
            os.path.join(local_app_data, r"CocCoc\Browser\Application\browser.exe"),
        ]

        if preferred.lower() == "edge":
            candidates.sort(key=lambda p: 0 if "msedge.exe" in p.lower() else 1)
        elif preferred.lower() == "brave":
            candidates.sort(key=lambda p: 0 if "brave.exe" in p.lower() else 1)

        for path in candidates:
            if os.path.exists(path):
                return path

        for binary_name in ["chrome.exe", "msedge.exe", "brave.exe"]:
            found = shutil.which(binary_name)
            if found:
                return found

        return None

    # Linux / macOS search
    linux_binaries = [
        "google-chrome-stable",
        "google-chrome",
        "chromium-browser",
        "chromium",
        "microsoft-edge-stable",
        "microsoft-edge",
        "brave-browser",
    ]
    for binary_name in linux_binaries:
        found = shutil.which(binary_name)
        if found:
            return found

    return None


@dataclass
class BrowserProfileConfig:
    """Configuration for an isolated, anti-lag browser profile."""

    id: str
    name: str
    debug_port: int
    user_data_dir: str
    browser_type: str = "chrome"
    browser_path: str = ""
    window_width: int = 480
    window_height: int = 720
    window_x: int = 0
    window_y: int = 0
    pid: int | None = None
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MinimalCDPWebSocket:
    """Minimal RFC 6455 WebSocket client using Python standard library socket."""

    def __init__(self, ws_url: str, timeout: float = 2.0) -> None:
        self.ws_url = ws_url
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self._msg_id = 0
        self._connect()

    def _connect(self) -> None:
        parsed = urllib.parse.urlparse(self.ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        self.sock = socket.create_connection((host, port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode("ascii"))
        res = self.sock.recv(4096).decode("latin-1", errors="ignore")
        if " 101 " not in res:
            raise ConnectionError(f"WebSocket handshake failed: {res[:100]}")

    def send_cdp_command(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC message over WebSocket frame and return result."""
        if not self.sock:
            raise ConnectionError("WebSocket is not connected")

        self._msg_id += 1
        payload = json.dumps({"id": self._msg_id, "method": method, "params": params or {}}).encode("utf-8")

        # RFC 6455 Client-to-server text frame (opcode 0x1, masked)
        frame = bytearray([0x81])
        length = len(payload)
        mask = os.urandom(4)

        if length <= 125:
            frame.append(0x80 | length)
        elif length <= 65535:
            frame.append(0x80 | 126)
            frame.extend(length.to_bytes(2, "big"))
        else:
            frame.append(0x80 | 127)
            frame.extend(length.to_bytes(8, "big"))

        frame.extend(mask)
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        frame.extend(masked_payload)

        self.sock.sendall(frame)

        # Receive response frame
        raw_header = self.sock.recv(2)
        if len(raw_header) < 2:
            return {"ok": False, "error": "Empty response"}

        payload_len = raw_header[1] & 0x7F
        if payload_len == 126:
            ext = self.sock.recv(2)
            payload_len = int.from_bytes(ext, "big")
        elif payload_len == 127:
            ext = self.sock.recv(8)
            payload_len = int.from_bytes(ext, "big")

        received = bytearray()
        while len(received) < payload_len:
            chunk = self.sock.recv(min(4096, payload_len - len(received)))
            if not chunk:
                break
            received.extend(chunk)

        try:
            return json.loads(received.decode("utf-8", errors="ignore"))
        except Exception as err:
            return {"ok": True, "raw": received.decode("utf-8", errors="ignore"), "parse_error": str(err)}

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


class CDPClient:
    """Chrome DevTools Protocol (CDP) client over HTTP and WebSocket."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9222, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    def is_alive(self) -> bool:
        """Check if browser remote debugging port is open and responding."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json/version", headers={"User-Agent": "Multi_Emulator"})
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return res.status == 200
        except Exception:
            return False

    def get_version(self) -> dict[str, Any]:
        """Fetch browser version and webSocketDebuggerUrl."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json/version", headers={"User-Agent": "Multi_Emulator"})
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception as err:
            return {"error": str(err)}

    def get_pages(self) -> list[dict[str, Any]]:
        """List active browser tabs/pages."""
        try:
            req = urllib.request.Request(f"{self.base_url}/json", headers={"User-Agent": "Multi_Emulator"})
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception:
            return []

    def get_active_page_ws_url(self) -> str | None:
        """Find the WebSocket URL of the foremost active page tab."""
        pages = self.get_pages()
        for page in pages:
            if page.get("type") == "page" and "webSocketDebuggerUrl" in page:
                return page["webSocketDebuggerUrl"]
        return None

    def navigate(self, url: str) -> dict[str, Any]:
        """Navigate the active tab to the specified URL."""
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("about:"):
            url = f"https://{url}"

        ws_url = self.get_active_page_ws_url()
        if ws_url:
            ws: MinimalCDPWebSocket | None = None
            try:
                ws = MinimalCDPWebSocket(ws_url, timeout=self.timeout)
                res = ws.send_cdp_command("Page.navigate", {"url": url})
                return {"ok": True, "url": url, "result": res}
            except Exception as err:
                return {"ok": False, "url": url, "error": str(err)}
            finally:
                if ws:
                    ws.close()

        # Fallback via HTTP new tab endpoint
        try:
            target_url = f"{self.base_url}/json/new?{urllib.parse.quote(url)}"
            req = urllib.request.Request(target_url, headers={"User-Agent": "Multi_Emulator"}, method="PUT")
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                data = json.loads(res.read().decode("utf-8"))
                return {"ok": True, "url": url, "tab": data}
        except Exception as err:
            return {"ok": False, "url": url, "error": str(err)}

    def execute_js(self, expression: str) -> dict[str, Any]:
        """Evaluate arbitrary JavaScript inside the active page."""
        ws_url = self.get_active_page_ws_url()
        if not ws_url:
            return {"ok": False, "error": "No active page tab found"}

        ws: MinimalCDPWebSocket | None = None
        try:
            ws = MinimalCDPWebSocket(ws_url, timeout=self.timeout)
            res = ws.send_cdp_command("Runtime.evaluate", {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            })
            val = res.get("result", {}).get("result", {}).get("value")
            return {"ok": True, "value": val, "raw": res}
        except Exception as err:
            return {"ok": False, "error": str(err)}
        finally:
            if ws:
                ws.close()

    def scroll(self, delta_x: int = 0, delta_y: int = 500) -> dict[str, Any]:
        """Scroll the active page by specified pixels."""
        script = f"window.scrollBy({{left: {delta_x}, top: {delta_y}, behavior: 'smooth'}}); true;"
        return self.execute_js(script)

    def click_element(self, selector: str) -> dict[str, Any]:
        """Click an element matching the CSS selector."""
        script = (
            f"(() => {{"
            f"  const el = document.querySelector({json.dumps(selector)});"
            f"  if (el) {{ el.click(); return {{ clicked: true, tag: el.tagName }}; }}"
            f"  return {{ clicked: false, error: 'Element not found' }};"
            f"}})()"
        )
        return self.execute_js(script)

    def type_text(self, text: str, selector: str | None = None) -> dict[str, Any]:
        """Type text into the active element or specified CSS selector."""
        script = (
            f"(() => {{"
            f"  const el = {f'document.querySelector({json.dumps(selector)})' if selector else 'document.activeElement'};"
            f"  if (el) {{"
            f"    el.value = (el.value || '') + {json.dumps(text)};"
            f"    el.dispatchEvent(new Event('input', {{ bubbles: true }}));"
            f"    el.dispatchEvent(new Event('change', {{ bubbles: true }}));"
            f"    return {{ typed: true, currentLength: el.value.length }};"
            f"  }}"
            f"  return {{ typed: false, error: 'No active or target input element' }};"
            f"}})()"
        )
        return self.execute_js(script)


class BrowserProfileManager:
    """Manages profiles on disk, handles anti-lag process lifecycle and multi-launching."""

    def __init__(self, base_dir: str | Path = "browser_profiles") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.base_dir / "profiles_manifest.json"
        self._profiles: dict[str, BrowserProfileConfig] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if not self.manifest_file.exists():
            return
        try:
            data = json.loads(self.manifest_file.read_text(encoding="utf-8"))
            for item in data.get("profiles", []):
                cfg = BrowserProfileConfig(**item)
                self._profiles[cfg.id] = cfg
        except Exception:
            self._profiles = {}

    def _save_manifest(self) -> None:
        data = {
            "updatedAt": time.time(),
            "profiles": [p.to_dict() for p in self._profiles.values()],
        }
        self.manifest_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_profiles(
        self,
        count: int = 1,
        prefix: str = "profile",
        browser_type: str = "auto",
        window_width: int = 460,
        window_height: int = 700,
    ) -> list[BrowserProfileConfig]:
        """Create one or multiple isolated anti-lag browser profiles."""
        created: list[BrowserProfileConfig] = []
        browser_bin = detect_browser_executable(preferred=browser_type) or "google-chrome"

        # Calculate tiling coordinates on a standard 1920x1080 display
        cols = 4
        spacing_x = window_width + 10
        spacing_y = window_height + 10

        for _ in range(count):
            idx = len(self._profiles) + 1
            prof_id = f"{prefix}_{idx:02d}"
            while prof_id in self._profiles:
                idx += 1
                prof_id = f"{prefix}_{idx:02d}"

            debug_port = DEFAULT_BASE_DEBUG_PORT + (idx - 1)
            user_data_path = self.base_dir / prof_id
            user_data_path.mkdir(parents=True, exist_ok=True)

            col = (idx - 1) % cols
            row = (idx - 1) // cols
            pos_x = col * spacing_x
            pos_y = row * spacing_y

            config = BrowserProfileConfig(
                id=prof_id,
                name=f"Browser-Profile-{idx:02d}",
                debug_port=debug_port,
                user_data_dir=str(user_data_path),
                browser_type=browser_type,
                browser_path=browser_bin,
                window_width=window_width,
                window_height=window_height,
                window_x=pos_x,
                window_y=pos_y,
                created_at=time.time(),
            )
            self._profiles[prof_id] = config
            created.append(config)

        self._save_manifest()
        return created

    def get_profile(self, profile_id: str) -> BrowserProfileConfig:
        if profile_id not in self._profiles:
            raise KeyError(f"Browser profile '{profile_id}' not found")
        return self._profiles[profile_id]

    def list_profiles(self) -> list[dict[str, Any]]:
        """List all profiles with live CDP connectivity and process status."""
        results: list[dict[str, Any]] = []
        for p in self._profiles.values():
            cdp = CDPClient(port=p.debug_port, timeout=0.15)
            is_alive = cdp.is_alive()
            p_dict = p.to_dict()
            p_dict["isAlive"] = is_alive
            p_dict["status"] = "RUNNING" if is_alive else "STOPPED"
            results.append(p_dict)
        return results

    def build_launch_command(
        self, profile: BrowserProfileConfig, initial_url: str = "about:blank"
    ) -> list[str]:
        """Construct the launch command with comprehensive anti-lag flags."""
        cmd: list[str] = [
            profile.browser_path or "google-chrome",
            f"--user-data-dir={profile.user_data_dir}",
            f"--remote-debugging-port={profile.debug_port}",
            f"--window-size={profile.window_width},{profile.window_height}",
            f"--window-position={profile.window_x},{profile.window_y}",
        ]
        cmd.extend(ANTI_LAG_CHROME_FLAGS)
        cmd.append(initial_url)
        return cmd

    def launch_profile(
        self, profile_id: str, initial_url: str = "about:blank"
    ) -> dict[str, Any]:
        """Launch an individual browser profile process with anti-lag settings."""
        p = self.get_profile(profile_id)
        cdp = CDPClient(port=p.debug_port, timeout=0.2)
        if cdp.is_alive():
            return {"id": p.id, "status": "ALREADY_RUNNING", "port": p.debug_port}

        cmd = self.build_launch_command(p, initial_url=initial_url)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            p.pid = proc.pid
            self._save_manifest()
            return {"id": p.id, "status": "LAUNCHED", "pid": proc.pid, "port": p.debug_port, "command": cmd}
        except Exception as err:
            return {"id": p.id, "status": "ERROR", "error": str(err)}

    def stop_profile(self, profile_id: str) -> bool:
        """Stop a running browser profile process."""
        p = self.get_profile(profile_id)
        stopped = False
        if p.pid:
            try:
                if platform.system() == "Windows":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    os.kill(p.pid, 15)  # SIGTERM
                stopped = True
            except Exception:
                pass
            p.pid = None
            self._save_manifest()
        return stopped

    def launch_all(self, initial_url: str = "about:blank", stagger_delay: float = 0.25) -> list[dict[str, Any]]:
        """Launch all registered profiles with staggered delay to avoid CPU spikes."""
        results: list[dict[str, Any]] = []
        for p in self._profiles.values():
            res = self.launch_profile(p.id, initial_url=initial_url)
            results.append(res)
            time.sleep(stagger_delay)
        return results

    def stop_all(self) -> list[str]:
        """Stop all running browser profiles."""
        stopped_ids: list[str] = []
        for p_id in list(self._profiles.keys()):
            if self.stop_profile(p_id):
                stopped_ids.append(p_id)
        return stopped_ids
