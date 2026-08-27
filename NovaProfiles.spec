# -*- mode: python ; coding: utf-8 -*-
"""Curated, reproducible PyInstaller definition for NovaProfiles."""

import os
from pathlib import Path


ROOT = Path(SPECPATH).resolve()
VERSION_INFO = Path(
    os.environ.get(
        "NOVAPROFILES_VERSION_INFO",
        ROOT / "build" / "version_info.txt",
    )
).resolve()

if not VERSION_INFO.is_file():
    raise SystemExit(
        "VersionInfo ausente. Execute BUILD_EXE.cmd ou "
        "packaging/generate_version_info.py antes do PyInstaller."
    )

# Modules from PySide6-Addons are not used. Keeping them excluded also protects
# local builds made in an environment that still has the old PySide6 metapackage.
EXCLUDED_MODULES = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQuick3D",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "tkinter",
]

# Qt's PyInstaller hook intentionally collects a broad QML installation. The
# application fixes Controls to the Basic style and imports only the modules
# below, so shipping the other styles, Virtual Keyboard, dialogs and tooling
# would add tens of megabytes without providing a reachable feature.
UNUSED_QT_DLLS = {
    "qt6labsanimation.dll",
    "qt6labsfolderlistmodel.dll",
    "qt6labsplatform.dll",
    "qt6labsqmlmodels.dll",
    "qt6labssettings.dll",
    "qt6labssharedimage.dll",
    "qt6labsstylekit.dll",
    "qt6labsstylekitimpl.dll",
    "qt6labssynchronizer.dll",
    "qt6labswavefrontmesh.dll",
    "qt6qmllocalstorage.dll",
    "qt6qmlxmllistmodel.dll",
    "qt6quickcontrols2fluentwinui3styleimpl.dll",
    "qt6quickcontrols2fusion.dll",
    "qt6quickcontrols2fusionstyleimpl.dll",
    "qt6quickcontrols2imagine.dll",
    "qt6quickcontrols2imaginestyleimpl.dll",
    "qt6quickcontrols2material.dll",
    "qt6quickcontrols2materialstyleimpl.dll",
    "qt6quickcontrols2universal.dll",
    "qt6quickcontrols2universalstyleimpl.dll",
    "qt6quickcontrols2windowsstyleimpl.dll",
    "qt6quickdialogs2.dll",
    "qt6quickdialogs2quickimpl.dll",
    "qt6quickdialogs2utils.dll",
    "qt6quickeffects.dll",
    "qt6quickparticles.dll",
    "qt6quickshapesdesignhelpers.dll",
    "qt6quicktest.dll",
    "qt6quicktimeline.dll",
    "qt6quicktimelineblendtrees.dll",
    "qt6quickvectorimage.dll",
    "qt6quickvectorimagegenerator.dll",
    "qt6quickvectorimagehelpers.dll",
    "qt6sql.dll",
    "qt6test.dll",
}

ALLOWED_QML_SUBDIRECTORIES = (
    "qtqml/models/",
    "qtqml/workerscript/",
    "qtquick/controls/basic/",
    "qtquick/controls/impl/",
    "qtquick/layouts/",
    "qtquick/shapes/",
    "qtquick/templates/",
    "qtquick/window/",
)


def _keep_qt_entry(entry):
    """Keep only Qt binaries and QML modules reachable by this application."""
    destination = str(entry[0]).replace("\\", "/").lower()
    filename = destination.rsplit("/", 1)[-1]
    if filename in UNUSED_QT_DLLS or "/plugins/qmltooling/" in destination:
        return False

    marker = "pyside6/qml/"
    if marker not in destination:
        return True
    relative = destination.split(marker, 1)[1]
    if any(relative.startswith(prefix) for prefix in ALLOWED_QML_SUBDIRECTORIES):
        return True

    # Preserve the files at each module root (qmldir, plugins and type info)
    # while rejecting every unlisted nested module.
    return (
        relative.startswith("qtqml/") and relative.count("/") == 1
    ) or (
        relative.startswith("qtquick/") and relative.count("/") == 1
    ) or (
        relative.startswith("qtquick/controls/") and relative.count("/") == 2
    )


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "qml"), "qml"),
        (str(ROOT / "assets"), "assets"),
        (str(ROOT / "translations"), "translations"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
    optimize=1,
)

a.binaries = [entry for entry in a.binaries if _keep_qt_entry(entry)]
a.datas = [entry for entry in a.datas if _keep_qt_entry(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NovaProfiles",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / "assets" / "NovaProfiles.ico")],
    version=str(VERSION_INFO),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="NovaProfiles",
)
