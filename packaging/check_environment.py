"""Validate the platform supported by the pinned Windows distribution."""

from __future__ import annotations

import platform
import struct
import sys


def main() -> int:
    errors: list[str] = []
    if sys.platform != "win32":
        errors.append("NovaProfiles is distributed only for Windows")
    if struct.calcsize("P") * 8 != 64 or platform.machine().upper() not in {
        "AMD64",
        "X86_64",
    }:
        errors.append("the dependency lock requires Windows x64 (AMD64)")
    if not ((3, 11) <= sys.version_info[:2] < (3, 15)):
        errors.append("use CPython 3.11, 3.12, 3.13 or 3.14")

    if errors:
        print("Ambiente incompatível:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Ambiente: CPython {platform.python_version()} / Windows x64")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
