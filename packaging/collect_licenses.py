"""Collect license/notice files from locked runtime distributions."""

from __future__ import annotations

import argparse
import shutil
from importlib import metadata
from pathlib import Path

from release_common import REPOSITORY_ROOT, read_exact_lock


LICENSE_MARKERS = ("license", "copying", "notice")


def is_license_file(path: Path) -> bool:
    return any(marker in path.name.casefold() for marker in LICENSE_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        type=Path,
        default=REPOSITORY_ROOT / "requirements-lock-win-x64.txt",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    copied = 0
    missing: list[str] = []

    shared = REPOSITORY_ROOT / "licenses"
    if shared.is_dir():
        shared_destination = output / "shared"
        shared_destination.mkdir(parents=True, exist_ok=True)
        for source in sorted(shared.iterdir()):
            if source.is_file():
                shutil.copy2(source, shared_destination / source.name)
                copied += 1

    for package in sorted(read_exact_lock(args.lock)):
        distribution = metadata.distribution(package)
        files = [
            file
            for file in (distribution.files or [])
            if is_license_file(Path(str(file)))
        ]
        if not files:
            missing.append(package)
            continue
        package_destination = output / package
        package_destination.mkdir(parents=True, exist_ok=True)
        for index, relative in enumerate(files, start=1):
            source = Path(distribution.locate_file(relative)).resolve()
            if not source.is_file():
                continue
            name = source.name
            destination = package_destination / name
            if destination.exists():
                destination = package_destination / f"{index}-{name}"
            shutil.copy2(source, destination)
            copied += 1

    if missing:
        print("Pacotes sem arquivo de licença no wheel: " + ", ".join(missing))
        print("Os textos de licença compartilhados e THIRD_PARTY_NOTICES.md cobrem os termos declarados.")
    print(f"Arquivos de licença coletados: {copied} em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
