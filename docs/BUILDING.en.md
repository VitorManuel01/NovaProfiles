# Build and dependencies

<p align="center"><a href="BUILDING.md">Português</a> | <strong>English</strong></p>

## Supported environment

- Windows 10/11 x64;
- CPython 3.11, 3.12, 3.13, or 3.14 x64;
- PowerShell 5.1 or later;
- PyPI access for the first installation.

The build is intentionally Windows-only because the artifact includes platform-specific Qt/HID wheels and binaries.

## Dependency files

- `requirements.txt`: accepted maintenance ranges;
- `requirements-build.txt`: accepted build ranges;
- `requirements-lock-win-x64.txt`: exact runtime dependencies;
- `requirements-build-lock-win-x64.txt`: exact runtime + build dependencies;
- `requirements-bootstrap-lock.txt`: exact `pip` version used during bootstrap.

The scripts install wheels only (`--only-binary=:all:`) and disable transitive resolution (`--no-deps`) because every dependency is listed in the lock. They then run `pip check`.

When reusing `.venv`, the installer explicitly removes old `PySide6`/`PySide6-Addons` packages, reinstalls the pins, and verifies versions and the absence of those extras before allowing a build. This prevents WebEngine or other unused modules from leaking from an old environment into the portable package.

The current locks cover several CPython versions whose native packages have different wheels. They pin versions but do not include a partial hash list, which would create a false impression of coverage. For complete cryptographic verification, the maintainer must download **all** accepted Windows x64 wheels for every supported Python version on a release machine, verify their origin, generate SHA-256 hashes, and only then enable `--require-hashes`. Do not copy hashes from an incomplete platform set.

## Installation

Runtime:

```powershell
.\INSTALAR.cmd
```

Runtime and build tools:

```powershell
powershell -NoProfile -File .\packaging\install.ps1 -BuildTools
```

Do not use an unversioned `pip install --upgrade pip`. Bootstrap installs the version declared in the lock.

## Portable build

Friendly mode:

```powershell
.\BUILD_EXE.cmd
```

Non-interactive mode after preparing `.venv`:

```powershell
$env:NOVAPROFILES_NO_PAUSE = "1"
powershell -NoProfile -File .\packaging\build.ps1 -SkipDependencyInstall
```

To create only `dist\NovaProfiles`, add `-SkipArchive`.

The process:

1. compiles `translations\*.ts` with the `lrelease` supplied by PySide6;
2. generates `build\version_info.txt` from `version.py`;
3. runs the tracked spec with UPX disabled;
4. removes unused QML/Addons modules;
5. validates PE/version/resources and loads the executable interface in offscreen mode;
6. includes documentation in the portable package;
7. creates the ZIP, SHA-256, and CycloneDX SBOM under `artifacts`;
8. tests ZIP integrity, checksum, content, and SBOM version.

To provide another VersionInfo file generated inside the repository:

```powershell
powershell -NoProfile -File .\packaging\build.ps1 -VersionInfo .\build\custom-version-info.txt
```

The spec receives that path through `NOVAPROFILES_VERSION_INFO`. The file must follow the PyInstaller VersionInfo format.

## Local validation

```powershell
.venv\Scripts\python.exe -m compileall -q main.py version.py backend packaging
.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -File packaging\lint_qml.ps1
.venv\Scripts\python.exe packaging\verify_artifact.py dist\NovaProfiles
```

When changing a user-visible string, update the catalog and translate every new entry before recompiling:

```powershell
powershell -NoProfile -File packaging\update_translations.ps1
powershell -NoProfile -File packaging\compile_translations.ps1
```

The artifact smoke test runs only `--version` and `--smoke-test`. The latter loads the interface with the offscreen and Windows plugins using a null controller: it does not read profiles, search for processes, or open/write HID. Verification also checks PE, `FileVersion`, required resources, and the absence of unused Qt modules. The physical checklist remains mandatory for protocol changes.
