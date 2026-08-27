# Release process

<p align="center"><a href="RELEASING.md">Português</a> | <strong>English</strong></p>

The workflow publishes only `v<SemVer>` tags and neither invents nor requires a signing certificate.

## Preparation

1. Decide the version and update only `version.py`.
2. Move relevant notes out of **Unreleased** in `CHANGELOG.md` and `CHANGELOG.en.md`.
3. Update locks on a branch and review every dependency change.
4. Run tests, `qmllint`, the build, and the physical checklist.
5. Confirm that the portable package contains no profiles, logs, personal paths, or Qt WebEngine.
6. Confirm third-party notices/licenses.
7. Confirm that the MIT `LICENSE` file and copyright notices are included in the package.

## Publishing

Create an annotated tag that exactly matches the version:

```powershell
git tag -a v1.2.0 -m "NovaProfiles 1.2.0"
git push origin v1.2.0
```

Automation validates the tag against `version.py`, installs exact locks, compiles translations, tests, builds, and creates:

- `NovaProfiles-<version>-win-x64.zip`;
- `NovaProfiles-<version>-win-x64.sha256`;
- `NovaProfiles-<version>-win-x64.cdx.json`.

The release job receives write permission only after the build, verifies that the tag exists, and publishes those three files. The workflow contains no key or certificate.

## Future signing

If the author obtains a real certificate, signing must be added as an isolated step with a secret protected by an Environment, approval, and issuer/timestamp documentation. Never use a test certificate to imply public trust, and never store a PFX file or password in the repository.
