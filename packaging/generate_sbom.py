"""Create a deterministic CycloneDX SBOM from the exact runtime lock."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from urllib.parse import quote

from release_common import REPOSITORY_ROOT, read_exact_lock, read_version


def purl(name: str, version: str) -> str:
    return f"pkg:pypi/{quote(name)}@{quote(version)}"


def build_bom(lock: Path, version_source: Path) -> dict:
    app_version = read_version(version_source)
    packages = read_exact_lock(lock)
    app_ref = f"pkg:github/VitorManuel01/NovaProfiles@{quote(app_version)}"
    dependency_refs = [purl(name, value) for name, value in sorted(packages.items())]
    fingerprint = "NovaProfiles|" + app_version + "|" + "|".join(dependency_refs)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, fingerprint)}",
        "version": 1,
        "metadata": {
            "component": {
                "bom-ref": app_ref,
                "type": "application",
                "name": "NovaProfiles",
                "version": app_version,
                "purl": app_ref,
            }
        },
        "components": [
            {
                "bom-ref": purl(name, value),
                "type": "library",
                "name": name,
                "version": value,
                "purl": purl(name, value),
                "properties": [
                    {"name": "novaprofiles:source-lock", "value": lock.name}
                ],
            }
            for name, value in sorted(packages.items())
        ],
        "dependencies": [
            {"ref": app_ref, "dependsOn": dependency_refs},
            *({"ref": dependency_ref, "dependsOn": []} for dependency_ref in dependency_refs),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        type=Path,
        default=REPOSITORY_ROOT / "requirements-lock-win-x64.txt",
    )
    parser.add_argument(
        "--version-source",
        type=Path,
        default=REPOSITORY_ROOT / "version.py",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    bom = build_bom(args.lock, args.version_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(bom, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"SBOM CycloneDX: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
