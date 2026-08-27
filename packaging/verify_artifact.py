"""Static smoke test for the portable PyInstaller folder."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pefile

from release_common import REPOSITORY_ROOT, read_version, windows_version_tuple


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    root = args.artifact.resolve()

    required = [
        root / "NovaProfiles.exe",
        root / "_internal" / "qml" / "Main.qml",
        root / "_internal" / "assets" / "NovaProfiles.png",
        root / "_internal" / "translations" / "novaprofiles_pt_BR.qm",
        root / "_internal" / "PySide6" / "plugins" / "platforms" / "qwindows.dll",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Artefato incompleto:")
        for path in missing:
            print(f"- {path}")
        return 1

    executable = root / "NovaProfiles.exe"
    with executable.open("rb") as stream:
        if stream.read(2) != b"MZ":
            print(f"Executável PE inválido: {executable}")
            return 1

    expected_version = read_version(REPOSITORY_ROOT / "version.py")
    pe = pefile.PE(str(executable), fast_load=False)
    try:
        fixed = pe.VS_FIXEDFILEINFO[0]
        actual_version = (
            fixed.FileVersionMS >> 16,
            fixed.FileVersionMS & 0xFFFF,
            fixed.FileVersionLS >> 16,
            fixed.FileVersionLS & 0xFFFF,
        )
        if actual_version != windows_version_tuple(expected_version):
            print(
                f"FileVersion incorreto: {actual_version!r}; "
                f"esperado {windows_version_tuple(expected_version)!r}"
            )
            return 1
    finally:
        pe.close()

    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        version_probe = subprocess.run(
            [str(executable), "--version"],
            cwd=root,
            env=environment,
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Executável não respondeu a --version: {exc}")
        return 1
    if version_probe.returncode != 0:
        print(f"Executável retornou {version_probe.returncode} em --version")
        return 1

    for platform_name in ("offscreen", "windows"):
        platform_environment = environment.copy()
        platform_environment["QT_QPA_PLATFORM"] = platform_name
        try:
            qml_probe = subprocess.run(
                [str(executable), "--smoke-test"],
                cwd=root,
                env=platform_environment,
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"Smoke QML ({platform_name}) do executável falhou: {exc}")
            return 1
        if qml_probe.returncode != 0:
            print(
                f"Smoke QML ({platform_name}) retornou "
                f"{qml_probe.returncode}"
            )
            return 1

    forbidden = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and any(
            marker in str(path).replace("\\", "/").casefold()
            for marker in (
                "webengine",
                "quick3d",
                "pyside6_addons",
                "qt6charts",
                "qt6multimedia",
                "qt6pdf",
                "qt6labs",
                "qt6quickdialogs",
                "qt6quickcontrols2fluent",
                "qt6quickcontrols2fusion",
                "qt6quickcontrols2imagine",
                "qt6quickcontrols2material",
                "qt6quickcontrols2universal",
                "qt6quickcontrols2windows",
                "/qtquick/controls/fluentwinui3/",
                "/qtquick/controls/fusion/",
                "/qtquick/controls/imagine/",
                "/qtquick/controls/material/",
                "/qtquick/controls/universal/",
                "/qtquick/controls/windows/",
                "/qtquick/virtualkeyboard/",
                "/plugins/qmltooling/",
                "/icuuc.dll",
                "/icudt",
                "/libcrypto-3-x64.dll",
                "/libssl-3-x64.dll",
            )
        )
    ]
    if forbidden:
        print("Módulos Qt não utilizados encontrados:")
        for path in forbidden[:20]:
            print(f"- {path.relative_to(root)}")
        return 1

    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    print(f"Smoke do artefato aprovado: {root} ({total / 1024 / 1024:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
