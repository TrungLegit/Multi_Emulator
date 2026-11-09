"""Multi-instance lifecycle manager for lightweight Android emulators."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.adb_optimizer import AdbOptimizer
from src.core.profiles import EmulatorProfile, get_profile
from src.core.qemu_builder import QemuCommandBuilder


@dataclass
class EmulatorInstance:
    """Represents a single lightweight Android emulator instance."""

    instance_id: str
    name: str
    profile_id: str
    adb_port: int
    status: str = "STOPPED"  # STOPPED | STARTING | RUNNING | ERROR
    pid: int | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    active_task: str = "idle"  # idle | tiktok_scroll | facebook_feed
    cpu_percent: float = 0.0
    ram_usage_mb: int = 0

    @property
    def adb_serial(self) -> str:
        """Return the ADB connection string for this instance."""
        return f"127.0.0.1:{self.adb_port}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize instance state and resource metrics for API / Dashboard."""
        profile = get_profile(self.profile_id)
        uptime = int(time.time() - self.started_at) if self.started_at and self.status == "RUNNING" else 0
        return {
            "id": self.instance_id,
            "name": self.name,
            "profile_id": self.profile_id,
            "profile_name": profile.name,
            "status": self.status,
            "adb_port": self.adb_port,
            "adb_serial": self.adb_serial,
            "resolution": f"{profile.width}x{profile.height}",
            "dpi": profile.dpi,
            "fps_limit": profile.fps_limit,
            "active_task": self.active_task,
            "metrics": {
                "cpu_percent": self.cpu_percent,
                "ram_usage_mb": self.ram_usage_mb,
                "ram_allocated_mb": profile.ram_mb,
                "cpu_cores": profile.cpu_cores,
            },
            "uptime_seconds": uptime,
        }


class LocalInstanceManager:
    """Local (dry-run) manager: creation, optimization, and lifecycle of multiple lightweight Android VMs."""

    BASE_ADB_PORT = 5555

    def __init__(
        self,
        workspace_dir: str | Path = "./vm_data",
        host_os: str | None = None,
    ) -> None:
        """Initialize the instance manager and QEMU command builder."""
        self.workspace_dir = Path(workspace_dir)
        self.qemu_builder = QemuCommandBuilder(host_os=host_os)
        self._instances: dict[str, EmulatorInstance] = {}

    def create_instance(
        self,
        name: str,
        profile_id: str = "standard_tiktok_fb",
        instance_id: str | None = None,
    ) -> EmulatorInstance:
        """Register a new lightweight Android instance with a dedicated ADB port."""
        profile = get_profile(profile_id)  # Validates profile_id
        idx = len(self._instances) + 1
        inst_id = instance_id or f"emu_{idx:02d}"
        if inst_id in self._instances:
            raise ValueError(f"Instance '{inst_id}' already exists.")

        adb_port = self.BASE_ADB_PORT + (idx - 1) * 2
        instance = EmulatorInstance(
            instance_id=inst_id,
            name=name,
            profile_id=profile.profile_id,
            adb_port=adb_port,
        )
        self._instances[inst_id] = instance
        return instance

    def get_instance(self, instance_id: str) -> EmulatorInstance:
        """Retrieve an instance by ID or raise KeyError."""
        if instance_id not in self._instances:
            raise KeyError(f"Emulator instance '{instance_id}' not found.")
        return self._instances[instance_id]

    def list_instances(self) -> list[dict[str, Any]]:
        """Return serialized states of all registered emulator instances."""
        return [inst.to_dict() for inst in self._instances.values()]

    def start_instance(self, instance_id: str, dry_run: bool = True) -> dict[str, Any]:
        """Start an emulator instance and return its QEMU + ADB optimization plan."""
        inst = self.get_instance(instance_id)
        profile = get_profile(inst.profile_id)

        overlay_disk = self.workspace_dir / f"{inst.instance_id}_overlay.qcow2"
        base_image = self.workspace_dir / "android_x86_64_slim_base.qcow2"

        disk_cmd = self.qemu_builder.build_overlay_disk_cmd(base_image, overlay_disk)
        qemu_cmd = self.qemu_builder.build_launch_cmd(
            instance_id=inst.instance_id,
            profile=profile,
            overlay_disk=overlay_disk,
            adb_port=inst.adb_port,
        )
        optimizer = AdbOptimizer(adb_serial=inst.adb_serial)
        adb_cmds = optimizer.build_optimization_commands(profile)

        inst.status = "RUNNING"
        inst.started_at = time.time()
        # Estimated low-resource footprint during active social media browsing
        inst.ram_usage_mb = int(profile.ram_mb * 0.68)
        inst.cpu_percent = 4.2 if profile.cpu_cores == 1 else 6.5

        return {
            "instance": inst.to_dict(),
            "dry_run": dry_run,
            "overlay_disk_command": " ".join(disk_cmd),
            "qemu_launch_command": " ".join(qemu_cmd),
            "adb_optimization_commands": [" ".join(c) for c in adb_cmds],
        }

    def stop_instance(self, instance_id: str) -> dict[str, Any]:
        """Stop a running emulator instance and release resources."""
        inst = self.get_instance(instance_id)
        inst.status = "STOPPED"
        inst.started_at = None
        inst.active_task = "idle"
        inst.cpu_percent = 0.0
        inst.ram_usage_mb = 0
        return inst.to_dict()

    def run_social_task(self, instance_id: str, task: str) -> dict[str, Any]:
        """Configure an instance for a specific social task ('tiktok' or 'facebook')."""
        inst = self.get_instance(instance_id)
        if inst.status != "RUNNING":
            raise RuntimeError(f"Instance '{instance_id}' must be RUNNING to execute tasks.")

        profile = get_profile(inst.profile_id)
        optimizer = AdbOptimizer(adb_serial=inst.adb_serial)

        if task == "tiktok":
            pkg = (
                "com.zhiliaoapp.musically.go"
                if profile.profile_id == "ultra_lite_social"
                else "com.ss.android.ugc.trill"
            )
            inst.active_task = "tiktok_scroll"
            inst.cpu_percent = 5.8
        elif task == "facebook":
            pkg = (
                "com.facebook.lite"
                if profile.profile_id == "ultra_lite_social"
                else "com.facebook.katana"
            )
            inst.active_task = "facebook_feed"
            inst.cpu_percent = 4.1
        else:
            raise ValueError("Task must be either 'tiktok' or 'facebook'.")

        launch_cmd = optimizer.build_launch_app_command(pkg)
        swipe_cmd = optimizer.build_swipe_up_command(
            width=profile.width, height=profile.height
        )

        return {
            "instance": inst.to_dict(),
            "target_package": pkg,
            "launch_command": " ".join(launch_cmd),
            "auto_scroll_command": " ".join(swipe_cmd),
        }
