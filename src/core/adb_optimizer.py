"""ADB post-boot optimizer & automation helper for TikTok and Facebook workloads."""

from src.core.profiles import EmulatorProfile

# Unnecessary built-in Android packages that waste RAM in social-media emulators
BLOATWARE_PACKAGES: list[str] = [
    "com.android.printspooler",
    "com.android.bips",
    "com.android.dreams.basic",
    "com.android.dreams.phototable",
    "com.android.wallpapercropper",
    "com.android.musicfx",
    "com.android.calendar",
    "com.android.contacts",
    "com.android.deskclock",
    "com.android.email",
    "com.android.calculator2",
]


class AdbOptimizer:
    """Generates and executes ADB optimization commands to minimize CPU/RAM usage."""

    def __init__(self, adb_serial: str = "127.0.0.1:5555") -> None:
        """Initialize optimizer bound to a specific emulator ADB serial (`host:port`)."""
        self.adb_serial = adb_serial

    def _adb_shell(self, shell_cmd: str) -> list[str]:
        """Wrap an Android shell command with the target ADB device serial."""
        return ["adb", "-s", self.adb_serial, "shell", shell_cmd]

    def build_optimization_commands(self, profile: EmulatorProfile) -> list[list[str]]:
        """Build the sequence of ADB commands to slim down Android for TikTok/FB."""
        commands: list[list[str]] = [
            # 1. Force low resolution & DPI to reduce GPU fill-rate by up to 75%
            self._adb_shell(f"wm size {profile.width}x{profile.height}"),
            self._adb_shell(f"wm density {profile.dpi}"),
            # 2. Disable all window/transition animations for instant UI response & zero GPU waste
            self._adb_shell("settings put global window_animation_scale 0.0"),
            self._adb_shell("settings put global transition_animation_scale 0.0"),
            self._adb_shell("settings put global animator_duration_scale 0.0"),
            # 3. Restrict background cached apps so TikTok/Facebook get dedicated RAM
            self._adb_shell(
                "settings put global activity_manager_constants "
                f"max_cached_processes={profile.max_bg_processes + 2}"
            ),
            # 4. Disable auto-brightness, screen timeout, and location scanning
            self._adb_shell("settings put system screen_brightness 40"),
            self._adb_shell("settings put system screen_off_timeout 2147483647"),
            self._adb_shell("settings put global wifi_scan_always_enabled 0"),
            self._adb_shell("settings put global ble_scan_always_enabled 0"),
        ]

        # 5. Disable bloatware packages
        for pkg in BLOATWARE_PACKAGES:
            commands.append(self._adb_shell(f"pm disable-user --user 0 {pkg}"))

        return commands

    def build_swipe_up_command(
        self, width: int = 540, height: int = 960, duration_ms: int = 250
    ) -> list[str]:
        """Build ADB swipe gesture to scroll to the next TikTok video or Facebook post."""
        center_x = width // 2
        start_y = int(height * 0.78)
        end_y = int(height * 0.22)
        return self._adb_shell(
            f"input swipe {center_x} {start_y} {center_x} {end_y} {duration_ms}"
        )

    def build_launch_app_command(self, package_name: str) -> list[str]:
        """Build ADB monkey command to launch TikTok or Facebook main activity."""
        return self._adb_shell(
            f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        )
