#!/usr/bin/env python3
"""Multi_Emulator — Python core entry point (Educational ADR version)."""


def get_project_info() -> dict[str, str]:
    """Return metadata about the Multi_Emulator project."""
    return {
        "name": "Multi_Emulator",
        "version": "0.1.0",
        "description": "Multi Emulator ADR version for education",
    }


def main() -> None:
    """Run the main CLI entry point."""
    info = get_project_info()
    print(f"{info['name']} v{info['version']} — {info['description']}")


if __name__ == "__main__":
    main()
