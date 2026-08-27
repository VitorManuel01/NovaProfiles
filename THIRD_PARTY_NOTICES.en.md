# Third-party software notices

<p align="center"><a href="THIRD_PARTY_NOTICES.md">Português</a> | <strong>English</strong></p>

NovaProfiles depends on components maintained by third parties. This summary is informational; the texts included in the packages and the upstream repositories are the legal references. A release must preserve the license files collected by PyInstaller and include this document and the CycloneDX SBOM.

The portable package includes `THIRD_PARTY_LICENSES`: license texts declared by runtime and build wheels are collected automatically (including the PyInstaller bootloader license and exception), and the shared GPL/LGPL/Qt licenses maintained under `licenses/` are included in full. Standard texts in that directory come from the SPDX license list; component-specific notices continue to prevail.

## Runtime

| Component | Use | License declared by the project |
|---|---|---|
| [PySide6-Essentials / Qt for Python](https://pypi.org/project/PySide6-Essentials/) | Qt Core, GUI, Widgets, QML, Quick, and Quick Controls | LGPL-3.0-only or GPL-2.0-only or GPL-3.0-only; commercial license also available |
| [shiboken6](https://pypi.org/project/shiboken6/) | Qt binding support | LGPL-3.0-only or GPL-2.0-only or GPL-3.0-only; commercial license also available |
| [hidapi (cython-hidapi)](https://pypi.org/project/hidapi/) | HID access on Windows | options described in the project's `LICENSE.txt`, including BSD/GPL |
| [psutil](https://github.com/giampaolo/psutil) | process enumeration | BSD-3-Clause |

The Essentials package was selected because the application does not use Qt WebEngine. The curated build must therefore not distribute Chromium/Qt WebEngine. The artifact smoke test fails if it finds those modules.

## Build tools

These tools are used to produce the executable and may not be imported runtime libraries. Their texts are also preserved because the executable embeds the PyInstaller bootloader:

| Component | License/project |
|---|---|
| [PyInstaller](https://pyinstaller.org/en/stable/license.html) | GPL-2.0-or-later with an exception for distributing packaged applications |
| [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | see the package/repository license |
| [altgraph](https://github.com/ronaldoussoren/altgraph) | MIT |
| [packaging](https://github.com/pypa/packaging) | Apache-2.0 or BSD-2-Clause |
| [pefile](https://github.com/erocarrera/pefile) | MIT |
| [pywin32-ctypes](https://github.com/enthought/pywin32-ctypes) | BSD-3-Clause |
| [setuptools](https://github.com/pypa/setuptools) | MIT |

Exact versions are listed in `requirements-lock-win-x64.txt`, `requirements-build-lock-win-x64.txt`, and each release's SBOM.

## NovaProfiles code

NovaProfiles' own source code is available under the [MIT License](LICENSE). This document covers third-party components and does not modify the terms of their respective licenses.
