# Security policy

<p align="center"><a href="SECURITY.md">Português</a> | <strong>English</strong></p>

## Supported versions

Only the latest published version receives security fixes. Local builds and earlier versions may help with diagnosis, but guaranteed backports are not provided.

## Reporting a vulnerability

Do not publish details of an exploitable vulnerability in a regular issue. Use **Report a vulnerability** on the repository's Security tab to create a private [GitHub Security Advisory](https://github.com/VitorManuel01/NovaProfiles/security/advisories/new).

When possible, include:

- version/commit and Windows edition;
- impact and prerequisites;
- minimum reproduction steps;
- only the files, HID reports, or logs that are strictly necessary;
- a suggested fix, if available.

Remove tokens, usernames, personal paths, and game data. Do not test on third-party devices or computers without authorization. The maintainer will acknowledge the report through the advisory and coordinate the fix and disclosure there; no fixed response deadline is promised.

## Sensitive areas

Particularly relevant areas include incorrect HID interface selection, partial or concurrent writes, malformed profile imports, automatic execution at login, unsafe path handling, loading untrusted QML/files, and exposing data in logs.

NovaProfiles should not request administrator privileges during normal use. The script that stops the legacy NSSM service is a separate, explicitly elevated action.
