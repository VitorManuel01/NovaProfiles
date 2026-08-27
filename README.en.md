<p align="center">
  <img src="assets/NovaProfiles.png" alt="NovaProfiles icon" width="96">
</p>

<p align="center">
  <a href="README.md">Português</a> |
  <strong>English</strong>
</p>

# NovaProfiles

[![Windows CI](https://github.com/VitorManuel01/NovaProfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/VitorManuel01/NovaProfiles/actions/workflows/ci.yml)

A remapping profile manager for the **GameSir Super Nova** controller on Windows. NovaProfiles associates profiles with games, detects the running executable, and applies RB, L4, and R4 mappings directly through the dongle's HID interface.

> **Project status:** experimental, community-developed software with no affiliation with GameSir. Automated validation does not replace testing on physical hardware.

![NovaProfiles main window](docs/screenshots/main-window.png)

## What it does

- creates, renames, duplicates, imports, and exports profiles;
- associates a profile with the full path of an executable;
- switches profiles automatically when a game opens or closes;
- indicates when an edit has not yet been written to the controller;
- reapplies the expected profile after the dongle reconnects;
- provides a catalog of USB HID keyboard targets and safe controller targets;
- starts with Windows, minimizes to the system tray, and can restore the Default profile on exit;
- keeps user data, import backups, and logs outside the program directory;
- provides Brazilian Portuguese and English interfaces according to the Windows language.

## Compatibility

| Item | Validated/target support |
|---|---|
| System | Windows 10 or 11 x64 |
| Running from source | CPython 3.11 through 3.14 x64 |
| Controller | GameSir Super Nova |
| Connection | 2.4 GHz dongle, XInput mode |
| Expected interface | VID `3537`, PID `103E`, vendor-defined MI_01/COL04 collection |

Bluetooth, USB cable, other firmware versions, other GameSir models, and multiple simultaneous controllers must not be considered compatible until they pass the hardware checklist.

### Protocol discovery and compatibility notice

The current configuration was obtained through **reverse engineering and byte-level analysis of HID traffic on the author's computer**. To identify the commands, mappings were changed manually in GameSir Connect and the captures were compared to determine which bytes changed. The results specifically reflect the GameSir Super Nova controller, keyboard, computer, GameSir Connect version, and firmware used in those tests.

For that reason, this version has been validated and is guaranteed to work only on the author's current computer configuration, with the controller firmware and GameSir Connect version used during capture. There is no guarantee that the same reports will work on another computer, keyboard layout, hardware revision, firmware, or GameSir Connect version. A software or firmware update may change the protocol and require new captures and validation.

The project's long-term goal is to **fully map the GameSir Super Nova protocol**, safely document the behavior of every byte, enable remapping of all supported buttons, and expand automatic profile creation and switching. Until that mapping and testing across different environments are complete, treat NovaProfiles as experimental and carefully validate each feature on your own equipment.

## Important HID warning

The application sends configuration reports directly to the controller. An interruption, incompatible firmware, or two configuration tools writing at the same time may produce an unexpected state.

Before applying a profile:

1. close GameSir Connect;
2. stop the legacy `GameSirAutoProfile` service, if it exists;
3. connect only the controller you intend to configure;
4. export your profiles before a major update;
5. do not disconnect the dongle while data is being written.

NovaProfiles blocks writes when the state of the legacy service is unknown or active. Even so, use it at your own risk and retain an official way to restore the controller configuration.

## Installation

### Portable version

Download `NovaProfiles-<version>-win-x64.zip` from the [Releases](https://github.com/VitorManuel01/NovaProfiles/releases) page, verify the SHA-256 published alongside it, extract the entire folder, and open `NovaProfiles.exe`.

The project does not currently require or provide a code-signing certificate. Windows SmartScreen may therefore display a warning even when the checksum is correct. Do not download executables from outside this repository.

### From source

1. Install a supported x64 CPython version.
2. Clone or download this repository.
3. Run `INSTALAR.cmd`.
4. Run `EXECUTAR.cmd`.

The installer creates `.venv`, installs the exact Windows x64 lock versions, and compiles the translations. It does not perform an unrestricted `pip` upgrade.

## Quick start

1. Select a profile or create a new one.
2. Under **Game executable**, choose the game's `.exe` file.
3. Select the RB, L4, and R4 targets.
4. Click **Apply profile** to write it now.
5. Enable **Automatic profile switching** to switch based on the running process.

The **Active** badge means the driver accepted the complete sequence of reports for this profile during this connection; it does not represent firmware readback. After an active mapping is edited, the interface displays pending changes until the next successful application.

## ABNT2 keyboard and USB HID

Keyboard values represent **USB HID usages**—positions/codes sent to the system—not necessarily the character printed on a key. Letters, numbers, and common controls usually match across layouts. Punctuation and ISO keys, such as those used by ABNT2, may be interpreted differently by Windows or the game.

Check the selected layout label, test first in an application with no important data, and do not assume that `[`, `]`, `/`, `;`, or accented keys will produce the same character under US and ABNT2 layouts.

## Data and privacy

Profiles, settings, and logs are stored in the user data directory selected by Qt. Use **Settings → Open data folder** to open the exact location. NovaProfiles requires no account and sends no telemetry. Game paths and process names may appear in local files; review logs before sharing them in an issue.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Controller disconnected | Use the 2.4 GHz dongle + XInput; reconnect it and close GameSir Connect. |
| Apply is disabled | The legacy service may be active/unknown, or the dongle was not found. |
| Write failure | The state may be partial; reconnect the controller and reapply the intended profile or **Default**. |
| Profile does not switch | Confirm the full `.exe` path and that automatic switching is enabled. |
| Mapping does not match the character | Check the USB HID/ABNT2 layout and the layout configured in Windows/the game. |
| Application does not open | Check `%TEMP%\NovaProfiles-startup-error.log`; when running from source, also use `EXECUTAR_DEBUG.cmd`. |
| Installation fails | Confirm Windows x64, a supported Python version, and PyPI access. Avoid Microsoft Store Python if its launcher is inconsistent. |
| Legacy NSSM service | Run `PARAR_SERVICO_NSSM_ANTIGO.cmd` as Administrator. The script only stops the service; it does not remove it. |

When reporting a problem, include the version, Windows edition, firmware, connection mode, and the last relevant log lines, removing usernames and private paths.

## Development and build

- [Building](docs/BUILDING.en.md)
- [Architecture and invariants](docs/ARCHITECTURE.en.md)
- [Hardware checklist](docs/HARDWARE_TESTING.en.md)
- [Release process](docs/RELEASING.en.md)
- [Contributing](CONTRIBUTING.en.md)
- [Security policy](SECURITY.en.md)
- [Third-party notices](THIRD_PARTY_NOTICES.en.md)
- [Changelog](CHANGELOG.en.md)

The official build uses `NovaProfiles.spec`, `PySide6-Essentials`, disabled UPX, VersionInfo generated from `version.py`, a safe executable smoke test, a CycloneDX SBOM, and a SHA-256 checksum.

## License

NovaProfiles source code is available under the [MIT License](LICENSE). It permits use, copying, modification, distribution, sublicensing, and commercial use, provided that the copyright notice and license text are retained in copies or substantial portions of the project.

Libraries and other third-party components remain subject to their own licenses, described in [THIRD_PARTY_NOTICES.en.md](THIRD_PARTY_NOTICES.en.md).
