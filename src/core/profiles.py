"""Lightweight hardware profiles for TikTok / YouTube / Facebook only."""

from dataclasses import asdict, dataclass
from typing import Any

# Package names of the three supported apps
APPS: dict[str, str] = {
    "tiktok": "com.ss.android.ugc.trill",
    "youtube": "com.google.android.youtube",
    "facebook": "com.facebook.katana",
}


@dataclass(frozen=True)
class EmulatorProfile:
    """Resource limits for one Android VM."""

    profile_id: str
    name: str
    ram_mb: int
    cpu_cores: int
    width: int
    height: int
    dpi: int
    fps_limit: int
    disable_audio: bool = False
    max_bg_processes: int = 2

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to a dictionary."""
        return asdict(self)


PROFILES: dict[str, EmulatorProfile] = {
    "lite": EmulatorProfile("lite", "Lite (768MB, 360x640)", 768, 1, 360, 640, 160, 24, False, 1),
    "standard": EmulatorProfile("standard", "Standard (1GB, 540x960)", 1024, 2, 540, 960, 240, 30, False, 2),
}
DEFAULT_PROFILE = "standard"


def get_profile(profile_id: str) -> EmulatorProfile:
    """Retrieve a preset profile by ID or raise ValueError if unknown."""
    if profile_id not in PROFILES:
        raise ValueError(f"Unknown profile '{profile_id}'. Available: {', '.join(PROFILES)}")
    return PROFILES[profile_id]
