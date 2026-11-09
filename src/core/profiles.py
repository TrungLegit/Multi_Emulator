"""Lightweight hardware & OS profiles optimized for TikTok and Facebook workloads."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmulatorProfile:
    """Configuration profile defining ultra-low resource bounds for an Android VM."""

    profile_id: str
    name: str
    description: str
    ram_mb: int = 1024
    cpu_cores: int = 2
    width: int = 540
    height: int = 960
    dpi: int = 240
    fps_limit: int = 30
    disable_audio: bool = True
    low_ram_flag: bool = True
    zram_enabled: bool = True
    max_bg_processes: int = 2
    dalvik_heap_size: str = "192m"
    dalvik_heap_growth_limit: str = "96m"
    target_apps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to a dictionary."""
        return asdict(self)


# Pre-configured profiles specifically tuned for social media browsing (TikTok / Facebook)
SOCIAL_PROFILES: dict[str, EmulatorProfile] = {
    "ultra_lite_social": EmulatorProfile(
        profile_id="ultra_lite_social",
        name="Ultra-Lite Social (TikTok/FB Lite)",
        description=(
            "Siêu tiết kiệm tài nguyên (768MB RAM, 360x640, 24 FPS). "
            "Tối ưu để treo nhiều tài khoản Facebook Lite & TikTok Lite cùng lúc."
        ),
        ram_mb=768,
        cpu_cores=1,
        width=360,
        height=640,
        dpi=160,
        fps_limit=24,
        disable_audio=True,
        low_ram_flag=True,
        zram_enabled=True,
        max_bg_processes=1,
        dalvik_heap_size="128m",
        dalvik_heap_growth_limit="64m",
        target_apps=["com.facebook.lite", "com.zhiliaoapp.musically.go"],
    ),
    "standard_tiktok_fb": EmulatorProfile(
        profile_id="standard_tiktok_fb",
        name="Standard Social (TikTok & Facebook Smooth)",
        description=(
            "Cân bằng hoàn hảo giữa độ mượt và nhẹ (1024MB RAM, 540x960 qHD, 30 FPS). "
            "Chuyên dụng để xem video TikTok, Reels và lướt Newsfeed mượt mà."
        ),
        ram_mb=1024,
        cpu_cores=2,
        width=540,
        height=960,
        dpi=240,
        fps_limit=30,
        disable_audio=False,
        low_ram_flag=True,
        zram_enabled=True,
        max_bg_processes=2,
        dalvik_heap_size="192m",
        dalvik_heap_growth_limit="96m",
        target_apps=["com.ss.android.ugc.trill", "com.facebook.katana"],
    ),
    "headless_automation": EmulatorProfile(
        profile_id="headless_automation",
        name="Headless Farm (Tự động hóa không giao diện)",
        description=(
            "Chạy ngầm hoàn toàn không mở cửa sổ đồ họa (-display none), tắt âm thanh. "
            "Giảm tối đa tải GPU & CPU cho kịch bản tương tác tự động."
        ),
        ram_mb=640,
        cpu_cores=1,
        width=360,
        height=640,
        dpi=160,
        fps_limit=15,
        disable_audio=True,
        low_ram_flag=True,
        zram_enabled=True,
        max_bg_processes=1,
        dalvik_heap_size="128m",
        dalvik_heap_growth_limit="64m",
        target_apps=["com.facebook.lite", "com.ss.android.ugc.trill"],
    ),
}


def get_profile(profile_id: str) -> EmulatorProfile:
    """Retrieve a preset profile by ID or raise ValueError if unknown."""
    if profile_id not in SOCIAL_PROFILES:
        valid = ", ".join(SOCIAL_PROFILES.keys())
        raise ValueError(f"Unknown profile '{profile_id}'. Available profiles: {valid}")
    return SOCIAL_PROFILES[profile_id]
