"""Generate the external PyInstaller VersionInfo from version.py."""

from __future__ import annotations

import argparse
from pathlib import Path

from release_common import REPOSITORY_ROOT, read_version, windows_version_tuple


def render(version: str) -> str:
    numeric = windows_version_tuple(version)
    return f"""# UTF-8
# Generated from version.py. Do not edit this output by hand.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric!r},
    prodvers={numeric!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('FileDescription', 'NovaProfiles'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'NovaProfiles'),
          StringStruct('OriginalFilename', 'NovaProfiles.exe'),
          StringStruct('ProductName', 'NovaProfiles'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version-source",
        type=Path,
        default=REPOSITORY_ROOT / "version.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "version_info.txt",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args()

    version = read_version(args.version_source)
    if args.print_version:
        print(version)
        return 0

    expected = render(version)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != expected:
            print(f"VersionInfo desatualizado: {args.output}")
            return 1
        print(f"VersionInfo válido para {version}: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(expected, encoding="utf-8", newline="\n")
    print(f"VersionInfo {version}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
