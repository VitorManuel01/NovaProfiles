"""Dependency-free helpers shared by release scripts."""

from __future__ import annotations

import ast
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def read_version(source: Path | None = None) -> str:
    """Read the version assignment without importing application code."""
    source = (source or REPOSITORY_ROOT / "version.py").resolve()
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    assignments: dict[str, str] = {}

    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            for target in targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = value_node.value

    for name in ("__version__", "VERSION", "APP_VERSION"):
        value = assignments.get(name)
        if value:
            if not SEMVER_PATTERN.fullmatch(value):
                raise ValueError(f"{source}: {name} is not valid SemVer: {value!r}")
            return value
    raise ValueError(f"{source}: no string __version__, VERSION or APP_VERSION found")


def windows_version_tuple(version: str) -> tuple[int, int, int, int]:
    match = SEMVER_PATTERN.fullmatch(version)
    if not match:
        raise ValueError(f"Not valid SemVer: {version!r}")
    numbers = tuple(int(match.group(name)) for name in ("major", "minor", "patch"))
    if any(number > 65535 for number in numbers):
        raise ValueError("Windows version fields must be between 0 and 65535")
    return (*numbers, 0)


def canonicalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_exact_lock(path: Path) -> dict[str, str]:
    """Read exact `name==version` entries, following local -r includes."""
    path = path.resolve()
    packages: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(maxsplit=1)[1]
            packages.update(read_exact_lock(path.parent / include))
            continue
        if "==" not in line or line.startswith("-"):
            raise ValueError(f"{path}: lock entry is not exact: {raw_line!r}")
        name, version = (part.strip() for part in line.split("==", 1))
        if not name or not version or ";" in version:
            raise ValueError(f"{path}: unsupported lock entry: {raw_line!r}")
        canonical = canonicalize_package_name(name)
        previous = packages.get(canonical)
        if previous and previous != version:
            raise ValueError(f"{path}: conflicting versions for {name}")
        packages[canonical] = version
    return packages
