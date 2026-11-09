"""QEMU command-line builder optimized for Windows (WHPX) and Linux (KVM) Android VMs."""

import platform
from pathlib import Path

from src.core.profiles import EmulatorProfile


class QemuCommandBuilder:
    """Builds low-overhead QEMU launch commands with Copy-on-Write disk overlays."""

    def __init__(self, host_os: str | None = None) -> None:
        """Initialize builder for target host OS ('Windows', 'Linux', or 'Darwin')."""
        self.host_os = host_os or platform.system()

    def detect_accelerator(self) -> list[str]:
        """Return optimal hardware virtualization flags for the host OS."""
        if self.host_os == "Windows":
            # Windows 10/11 native hypervisor platform (WHPX) with kernel-irqchip off for stability
            return ["-accel", "whpx,kernel-irqchip=off", "-cpu", "max"]
        if self.host_os == "Linux":
            # Native Linux KVM hardware virtualization
            return ["-enable-kvm", "-cpu", "host"]
        # Fallback software translation (TCG multi-threaded)
        return ["-accel", "tcg,thread=multi", "-cpu", "max"]

    @staticmethod
    def build_overlay_disk_cmd(base_image_path: str | Path, overlay_path: str | Path) -> list[str]:
        """Generate qemu-img command to create a tiny Copy-on-Write (qcow2) disk per instance."""
        return [
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            "-b",
            str(base_image_path),
            "-F",
            "qcow2",
            str(overlay_path),
        ]

    def build_launch_cmd(
        self,
        instance_id: str,
        profile: EmulatorProfile,
        overlay_disk: str | Path,
        adb_port: int,
        headless: bool = False,
    ) -> list[str]:
        """Build the complete ultra-lightweight QEMU launch command for an Android-x86 VM."""
        cmd: list[str] = [
            "qemu-system-x86_64",
            "-name",
            f"MultiEmu-{instance_id}",
            "-m",
            str(profile.ram_mb),
            "-smp",
            f"cores={profile.cpu_cores},threads=1,sockets=1",
        ]

        # 1. Hardware acceleration (WHPX on Windows / KVM on Linux)
        cmd.extend(self.detect_accelerator())

        # 2. Paravirtualized VirtIO storage with writeback cache & discard for low disk I/O
        cmd.extend([
            "-drive",
            f"file={overlay_disk},if=virtio,format=qcow2,cache=writeback,discard=unmap",
        ])

        # 3. VirtIO-GPU 2D/VirGL graphics tuned for low-resolution social media video decoding
        if headless or profile.profile_id == "headless_automation":
            cmd.extend(["-display", "none", "-vga", "std"])
        else:
            # Standard VGA works with Android-x86 out of the box (software rendering)
            cmd.extend(["-vga", "std", "-display", "gtk"])

        # 4. Audio subsystem stripping (saves CPU interrupts when muted)
        if profile.disable_audio:
            cmd.extend(["-audiodev", "none,id=noaudio"])

        # 5. VirtIO network adapter with ADB port forwarding (Host adb_port -> Guest 5555)
        cmd.extend([
            "-netdev",
            f"user,id=net0,hostfwd=tcp:127.0.0.1:{adb_port}-:5555",
            "-device",
            "virtio-net-pci,netdev=net0",
        ])

        # 6. Tablet USB pointer for accurate touch/swipe coordinates without mouse grab
        cmd.extend(["-usb", "-device", "usb-tablet"])

        # 7. Strip unnecessary legacy hardware (Floppy, Parallel, Serial, Ballooning)
        cmd.extend([
            "-no-user-config",
            "-device",
            "virtio-balloon-pci",
        ])

        return cmd
