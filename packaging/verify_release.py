"""Validate the final ZIP, checksum and CycloneDX release bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from release_common import REPOSITORY_ROOT, read_version


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_release(archive: Path, checksum: Path, sbom: Path) -> None:
    version = read_version(REPOSITORY_ROOT / "version.py")
    expected_name = f"NovaProfiles-{version}-win-x64.zip"
    if archive.name != expected_name:
        raise ValueError(f"Nome do ZIP inválido: {archive.name}; esperado {expected_name}")

    digest = sha256(archive)
    expected_checksum = f"{digest} *{archive.name}"
    actual_checksum = checksum.read_text(encoding="ascii").strip()
    if actual_checksum != expected_checksum:
        raise ValueError("O arquivo SHA-256 não corresponde ao ZIP")

    try:
        with ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError(f"Caminho inseguro no ZIP: {name}")
                if not path.parts or path.parts[0] != "NovaProfiles":
                    raise ValueError(f"Entrada fora da pasta NovaProfiles: {name}")

            required = {
                "NovaProfiles/NovaProfiles.exe",
                "NovaProfiles/PARAR_SERVICO_NSSM_ANTIGO.cmd",
                "NovaProfiles/README.md",
                "NovaProfiles/THIRD_PARTY_NOTICES.md",
                "NovaProfiles/assets/NovaProfiles.png",
                "NovaProfiles/docs/screenshots/main-window.png",
                "NovaProfiles/packaging/stop_legacy_service.ps1",
                "NovaProfiles/_internal/qml/Main.qml",
                "NovaProfiles/_internal/translations/novaprofiles_pt_BR.qm",
                "NovaProfiles/THIRD_PARTY_LICENSES/pyinstaller/COPYING.txt",
                "NovaProfiles/THIRD_PARTY_LICENSES/shared/LGPL-3.0-only.txt",
            }
            missing = sorted(required - names)
            if missing:
                raise ValueError("Arquivos ausentes no ZIP: " + ", ".join(missing))

            forbidden = []
            for name in names:
                lowered = name.casefold()
                basename = PurePosixPath(lowered).name
                if (
                    basename in {".env", "profiles.json"}
                    or basename.endswith((".log", ".pcap", ".pcapng"))
                    or "__pycache__" in PurePosixPath(lowered).parts
                ):
                    forbidden.append(name)
            if forbidden:
                raise ValueError(
                    "Dados locais ou temporários encontrados no ZIP: "
                    + ", ".join(sorted(forbidden)[:20])
                )

            corrupt = bundle.testzip()
            if corrupt:
                raise ValueError(f"Entrada corrompida no ZIP: {corrupt}")
    except BadZipFile as exc:
        raise ValueError(f"ZIP inválido: {exc}") from exc

    bom = json.loads(sbom.read_text(encoding="utf-8"))
    component = bom.get("metadata", {}).get("component", {})
    if bom.get("bomFormat") != "CycloneDX" or component.get("version") != version:
        raise ValueError("SBOM ausente, inválido ou com versão divergente")
    if not bom.get("components") or not bom.get("dependencies"):
        raise ValueError("SBOM não contém componentes/dependências")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--checksum", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_release(
            args.archive.resolve(),
            args.checksum.resolve(),
            args.sbom.resolve(),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Pacote de release inválido: {exc}")
        return 1
    print(f"Pacote de release verificado: {args.archive.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
