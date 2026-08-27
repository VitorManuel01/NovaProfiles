from __future__ import annotations

import argparse
import ctypes
import os
import signal
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QLocale,
    QTimer,
    QTranslator,
    QUrl,
    qInstallMessageHandler,
)
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from backend.app_controller import AppController
from backend.tray import TrayController
from version import __version__

_MUTEX_HANDLE = None
_WAKE_EVENT_HANDLE = None
_KERNEL32 = None
_ERROR_ALREADY_EXISTS = 183
_WAIT_OBJECT_0 = 0
STARTUP_LOG = Path(tempfile.gettempdir()) / "NovaProfiles-startup-error.log"


def _append_startup_log(text: str):
    try:
        with STARTUP_LOG.open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except Exception:
        pass


def qt_message_handler(mode, context, message):
    # Keep QML/Qt diagnostics even in --windowed PyInstaller builds.
    location = ""
    try:
        if context and context.file:
            location = f" ({context.file}:{context.line})"
    except Exception:
        pass
    line = f"[Qt] {message}{location}"
    _append_startup_log(line)
    try:
        print(line, file=sys.stderr, flush=True)
    except Exception:
        pass


def resource_path(relative: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative

    source_path = Path(__file__).resolve().parent / relative
    if source_path.exists():
        return source_path

    installed_path = Path(sys.prefix) / "share" / "novaprofiles" / relative
    return installed_path if installed_path.exists() else source_path


def install_translations(app: QApplication) -> list[QTranslator]:
    """Load the best available app and Qt catalogs for the system locale."""
    locale = QLocale.system()
    QLocale.setDefault(locale)
    loaded: list[QTranslator] = []

    candidates = [locale.name()]
    language = locale.name().split("_", 1)[0]
    if language not in candidates:
        candidates.append(language)

    app_translations = resource_path("translations")
    qt_translations = Path(
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    for prefix, directory in (
        ("novaprofiles_", app_translations),
        ("qtbase_", qt_translations),
    ):
        for suffix in candidates:
            translator = QTranslator(app)
            if translator.load(str(directory / f"{prefix}{suffix}.qm")):
                app.installTranslator(translator)
                loaded.append(translator)
                break

    return loaded


def acquire_single_instance() -> bool:
    global _MUTEX_HANDLE, _WAKE_EVENT_HANDLE, _KERNEL32
    if os.name != "nt":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = (
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    )
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.SetEvent.argtypes = (ctypes.c_void_p,)
    kernel32.SetEvent.restype = ctypes.c_bool
    kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_bool

    _KERNEL32 = kernel32
    ctypes.set_last_error(0)
    _MUTEX_HANDLE = kernel32.CreateMutexW(
        None, False, "Local\\NovaProfiles_SuperNova_AutoProfiles"
    )
    if not _MUTEX_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())

    already_running = ctypes.get_last_error() == _ERROR_ALREADY_EXISTS
    _WAKE_EVENT_HANDLE = kernel32.CreateEventW(
        None, False, False, "Local\\NovaProfiles_ShowExistingWindow"
    )
    if not _WAKE_EVENT_HANDLE:
        error = ctypes.get_last_error()
        kernel32.CloseHandle(_MUTEX_HANDLE)
        _MUTEX_HANDLE = None
        raise ctypes.WinError(error)
    return not already_running


def notify_existing_instance():
    if os.name == "nt" and _KERNEL32 and _WAKE_EVENT_HANDLE:
        _KERNEL32.SetEvent(_WAKE_EVENT_HANDLE)


def release_single_instance_handles():
    global _MUTEX_HANDLE, _WAKE_EVENT_HANDLE
    if os.name != "nt" or not _KERNEL32:
        return
    for handle_name in ("_WAKE_EVENT_HANDLE", "_MUTEX_HANDLE"):
        handle = globals().get(handle_name)
        if handle:
            try:
                _KERNEL32.CloseHandle(handle)
            except Exception:
                pass
            globals()[handle_name] = None


def show_fatal_error(title: str, detail: str):
    _append_startup_log(f"\n=== {title} ===\n{detail}\n")
    try:
        QMessageBox.critical(
            None,
            title,
            f"{detail}\n\nStartup log:\n{STARTUP_LOG}",
        )
    except Exception:
        pass


def run_app(background: bool) -> int:
    try:
        STARTUP_LOG.write_text("Nova Profiles startup log\n", encoding="utf-8")
    except OSError:
        # Diagnostics must never become a startup dependency.
        pass
    qInstallMessageHandler(qt_message_handler)

    QCoreApplication.setOrganizationName("NovaProfiles")
    QCoreApplication.setOrganizationDomain("local.novaprofiles")
    QCoreApplication.setApplicationName("NovaProfiles")
    QCoreApplication.setApplicationVersion(__version__)

    # Application flags are consumed above; do not expose arbitrary remaining
    # command-line options to Qt's own argument parser.
    app = QApplication(sys.argv[:1])
    # Keep explicit references for the full application lifetime.
    app._novaprofiles_translators = install_translations(app)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(resource_path("assets/NovaProfiles.png"))))

    controller = None
    try:
        controller = AppController()
        app.aboutToQuit.connect(controller.shutdown)
        tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        tray = (
            TrayController(
                controller,
                resource_path("assets/NovaProfiles.png"),
                app,
            )
            if tray_available
            else None
        )

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("app", controller)
        qml_file = resource_path("qml/Main.qml")
        _append_startup_log(f"Loading QML: {qml_file}")
        engine.load(QUrl.fromLocalFile(str(qml_file)))

        if not engine.rootObjects():
            raise RuntimeError(
                "Main.qml could not be created. See the Qt messages above."
            )

        window = engine.rootObjects()[0]

        def show_window():
            window.showNormal()
            window.raise_()
            window.requestActivate()

        controller.showWindowRequested.connect(show_window)
        controller.quitRequested.connect(app.quit)

        def request_quit(*_):
            app.quit()

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, request_quit)
                except Exception:
                    pass

        wake_timer = None
        if os.name == "nt" and _KERNEL32 and _WAKE_EVENT_HANDLE:
            wake_timer = QTimer(app)
            wake_timer.setInterval(200)

            def poll_show_request():
                if (
                    _KERNEL32.WaitForSingleObject(_WAKE_EVENT_HANDLE, 0)
                    == _WAIT_OBJECT_0
                ):
                    controller.requestShowWindow()

            wake_timer.timeout.connect(poll_show_request)
            wake_timer.start()

        if not background or not tray_available:
            show_window()
            if background and not tray_available:
                controller.toast.emit(
                    "System tray is unavailable, so Nova Profiles was opened normally"
                )

        _append_startup_log("Startup completed successfully.")
        return app.exec()

    except Exception:
        detail = traceback.format_exc()
        if controller is not None:
            try:
                controller.shutdown(restore_default=False)
            except Exception:
                detail += "\nCleanup failure:\n" + traceback.format_exc()
        show_fatal_error("Nova Profiles failed to start", detail)
        return 2


def run_qml_smoke() -> int:
    """Load the packaged UI without profiles, process scans or HID access."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QCoreApplication.setOrganizationName("NovaProfiles")
    QCoreApplication.setApplicationName("NovaProfilesSmoke")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app._novaprofiles_translators = install_translations(app)
    qml_messages: list[str] = []

    def smoke_message_handler(mode, context, message):
        source = str(getattr(context, "file", "") or "")
        if source.casefold().endswith(".qml"):
            qml_messages.append(
                f"{source}:{int(getattr(context, 'line', 0) or 0)}: {message}"
            )

    previous_handler = qInstallMessageHandler(smoke_message_handler)
    try:
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("app", None)
        engine.load(QUrl.fromLocalFile(str(resource_path("qml/Main.qml"))))
        if not engine.rootObjects():
            _append_startup_log(
                "Packaged QML smoke could not create the root window.\n"
                + "\n".join(qml_messages)
            )
            return 2
        for _ in range(3):
            app.processEvents()
        if qml_messages:
            _append_startup_log("Packaged QML smoke warnings:\n" + "\n".join(qml_messages))
            return 3
        return 0
    finally:
        qInstallMessageHandler(previous_handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Nova Profiles")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args, _ = parser.parse_known_args()

    if args.version:
        # A windowed PyInstaller executable has sys.stdout=None. argparse's
        # built-in version action attempts to write to it and opens an unseen
        # crash dialog instead of exiting, so handle this flag explicitly.
        if sys.stdout is not None:
            print(__version__)
        return 0
    if args.smoke_test:
        return run_qml_smoke()

    try:
        if not acquire_single_instance():
            # Bring a hidden/tray instance forward instead of failing silently.
            notify_existing_instance()
            return 0
        return run_app(args.background)
    except Exception:
        detail = traceback.format_exc()
        _append_startup_log(detail)
        # QApplication may not exist yet, so console/log is the safe fallback here.
        try:
            print(detail, file=sys.stderr)
            print(f"Startup log: {STARTUP_LOG}", file=sys.stderr)
        except Exception:
            pass
        return 3
    finally:
        release_single_instance_handles()


if __name__ == "__main__":
    raise SystemExit(main())
