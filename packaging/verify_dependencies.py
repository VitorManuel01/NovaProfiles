"""Verify exact locked versions and reject known incompatible Qt extras."""

from __future__ import annotations

import argparse
from importlib import metadata
from pathlib import Path

from release_common import (
    REPOSITORY_ROOT,
    canonicalize_package_name,
    read_exact_lock,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        type=Path,
        default=REPOSITORY_ROOT / "requirements-lock-win-x64.txt",
    )
    parser.add_argument(
        "--forbid",
        action="append",
        default=["PySide6", "PySide6-Addons"],
    )
    args = parser.parse_args()

    expected = read_exact_lock(args.lock)
    installed = {
        canonicalize_package_name(dist.metadata["Name"]): dist.version
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }
    errors: list[str] = []
    for name, version in sorted(expected.items()):
        actual = installed.get(name)
        if actual != version:
            errors.append(f"{name}: esperado {version}, instalado {actual or 'ausente'}")
    for package in args.forbid:
        canonical = canonicalize_package_name(package)
        if canonical in installed:
            errors.append(f"pacote incompatível presente: {package} {installed[canonical]}")

    if errors:
        print(f"Ambiente não corresponde a {args.lock.name}:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Dependências verificadas: {args.lock.name} ({len(expected)} pacotes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
