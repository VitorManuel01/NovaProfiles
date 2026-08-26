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

from PySide6.QtCore import QCoreApplication, QUrl, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from backend.app_controller import AppController
from backend.tray import TrayController

_MUTEX_HANDLE = None
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
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def acquire_single_instance() -> bool:
    global _MUTEX_HANDLE
    if os.name != "nt":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _MUTEX_HANDLE = kernel32.CreateMutexW(
        None, False, "Local\\NovaProfiles_SuperNova_AutoProfiles"
    )
    return kernel32.GetLastError() != 183


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
    STARTUP_LOG.write_text("Nova Profiles startup log\n", encoding="utf-8")
    qInstallMessageHandler(qt_message_handler)

    QCoreApplication.setOrganizationName("NovaProfiles")
    QCoreApplication.setOrganizationDomain("local.novaprofiles")
    QCoreApplication.setApplicationName("NovaProfiles")
    QCoreApplication.setApplicationVersion("1.1.0")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(resource_path("assets/NovaProfiles.png"))))

    try:
        controller = AppController()
        tray = TrayController(
            controller,
            resource_path("assets/NovaProfiles.png"),
            app,
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
            window.show()
            window.raise_()
            window.requestActivate()

        controller.showWindowRequested.connect(show_window)
        controller.quitRequested.connect(app.quit)
        app.aboutToQuit.connect(controller.shutdown)

        def request_quit(*_):
            app.quit()

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, request_quit)
                except Exception:
                    pass

        if not background:
            show_window()

        _append_startup_log("Startup completed successfully.")
        return app.exec()

    except Exception:
        detail = traceback.format_exc()
        show_fatal_error("Nova Profiles failed to start", detail)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--background", action="store_true")
    args, _ = parser.parse_known_args()

    if not acquire_single_instance():
        # An existing instance can be hidden in the tray. Do not report this as a crash.
        return 0

    try:
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


if __name__ == "__main__":
    raise SystemExit(main())
