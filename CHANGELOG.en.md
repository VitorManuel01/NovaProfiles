# Changelog

<p align="center"><a href="CHANGELOG.md">Português</a> | <strong>English</strong></p>

All notable NovaProfiles changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-08-27

### Added

- applied state based on profile revision and connection generation;
- pending-change indication and safe reapplication after reconnection;
- work queue for HID/service operations without blocking the interface;
- transactional profile validation, import preview, and backups;
- game matching by full path when configured;
- responsive, accessible interface translated into Brazilian Portuguese;
- automated tests for persistence, protocol, matching, and reconnection;
- Windows CI with tests, `qmllint`, and portable build;
- release artifacts with VersionInfo, SHA-256 checksum, and CycloneDX SBOM;
- third-party licenses collected in the portable package and safe QML executable smoke test;
- single Windows instance with restoration of the already-running window;
- build, release, security, and physical-validation documentation.

### Changed

- reduced the Qt dependency from `PySide6` to `PySide6-Essentials`;
- legacy service state is now explicit (`running`, `stopped`, or `unknown`), and a query failure blocks writes;
- HID writes require a complete report and provide specific errors;
- `.cmd` scripts preserve exit codes;
- the build uses exact locks, does not freely upgrade `pip`, and disables UPX;
- the build isolates `PATH` and removes unused QML styles/modules;
- legacy service queries use the language-independent numeric Windows API;
- corrupted profiles are preserved before recovery, and future schemas are not overwritten;
- the version now has a single source in `version.py`.

### Security

- concurrent writes with the legacy NSSM service are blocked when it cannot be proven to be stopped;
- imports no longer replace data before validation and confirmation.

## [1.1.0] - 2026-08-26

### Added

- first public version of the QML interface, automatic profiles, and HID writes for GameSir Super Nova.

[Unreleased]: https://github.com/VitorManuel01/NovaProfiles/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/VitorManuel01/NovaProfiles/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/VitorManuel01/NovaProfiles/releases/tag/v1.1.0
