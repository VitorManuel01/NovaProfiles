# Contributing to NovaProfiles

<p align="center"><a href="CONTRIBUTING.md">Português</a> | <strong>English</strong></p>

Thank you for your interest. Small, testable changes backed by hardware evidence are easier to review.

## Setup

1. Use Windows x64 and CPython 3.11 through 3.14 x64.
2. Run `INSTALAR.cmd` for runtime dependencies or `packaging\install.ps1 -BuildTools` for build dependencies.
3. Create a short-lived branch and do not include `.venv`, `build`, `dist`, personal profiles, or logs.
4. Read [docs/BUILDING.en.md](docs/BUILDING.en.md).

## Before opening a pull request

Run:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -File packaging\lint_qml.ps1
BUILD_EXE.cmd -SkipDependencyInstall
```

For HID changes, also complete [docs/HARDWARE_TESTING.en.md](docs/HARDWARE_TESTING.en.md) and report the firmware, connection, and results. USB captures may contain identifiers; sanitize them before attaching.

## Change rules

- Preserve the safety rule: never write when the legacy service is `running` or `unknown`.
- Do not broaden VID/PID, collections, or HID commands based only on assumptions.
- Keep persistence copy-on-write and validate imports before replacement.
- Update tests when fixing a bug or changing a format.
- User-visible strings must use translations and keep English/pt-BR synchronized.
- Update `CHANGELOG.md` and `CHANGELOG.en.md` for user-facing changes.
- Do not change versions in multiple files; edit only `version.py`.
- Do not add certificates, keys, tokens, or personal profiles to the repository.

## Pull requests

Explain the problem, solution, risk, and validation. Keep refactors separate from protocol changes whenever possible. CI must complete the tests, `qmllint`, and build.

By contributing, you agree that your contribution will be made available under the project's [MIT License](LICENSE). Confirm that you have the right to submit the code and preserve applicable third-party notices.
