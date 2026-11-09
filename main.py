#!/usr/bin/env python3
"""Multi_Emulator — Python core entry point (Educational ADR version)."""

from __future__ import annotations

import sys

from src.core.cli import run_cli


def get_project_info() -> dict[str, str]:
    """Return metadata about the Multi_Emulator project."""
    return {
        "name": "Multi_Emulator",
        "version": "0.1.0",
        "description": "Multi Emulator ADR version for education",
    }


def main(argv: list[str] | None = None) -> None:
    """Run the main CLI entry point or print project info if no subcommand is given."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        info = get_project_info()
        print(f"{info['name']} v{info['version']} — {info['description']}")
        print(
            "Usage: python3 main.py [scan | connect | link | broadcast | disconnect | status | profile-create | profile-start | profile-stop | profile-list | profile-sync] [--json]"
        )
        return

    code = run_cli(args)
    if code == -1:
        info = get_project_info()
        print(f"{info['name']} v{info['version']} — {info['description']}")


if __name__ == "__main__":
    main()
