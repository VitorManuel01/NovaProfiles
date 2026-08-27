from __future__ import annotations

import contextlib
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

import main
from version import __version__


class MainEntryPointTests(unittest.TestCase):
    def test_run_app_reaches_qml_bootstrap_and_event_loop(self):
        qt_app = MagicMock()
        qt_app.exec.return_value = 23
        controller = MagicMock()
        engine = MagicMock()
        window = MagicMock()
        engine.rootObjects.return_value = [window]

        with (
            patch.object(main, "STARTUP_LOG", MagicMock()),
            patch.object(main, "qInstallMessageHandler"),
            patch.object(main.QCoreApplication, "setOrganizationName"),
            patch.object(main.QCoreApplication, "setOrganizationDomain"),
            patch.object(main.QCoreApplication, "setApplicationName"),
            patch.object(main.QCoreApplication, "setApplicationVersion"),
            patch.object(main, "QApplication", return_value=qt_app),
            patch.object(main, "install_translations", return_value=[]),
            patch.object(main, "QIcon"),
            patch.object(main, "AppController", return_value=controller),
            patch.object(main.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
            patch.object(main, "QQmlApplicationEngine", return_value=engine),
            patch.object(main.signal, "signal"),
        ):
            self.assertEqual(main.run_app(background=False), 23)

        engine.load.assert_called_once()
        window.showNormal.assert_called_once()
        qt_app.exec.assert_called_once_with()

    def test_version_exits_before_single_instance_or_qt_startup(self):
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["NovaProfiles", "--version"]),
            patch.object(main, "acquire_single_instance") as acquire,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main.main(), 0)
        acquire.assert_not_called()
        self.assertEqual(output.getvalue().strip(), __version__)

    def test_version_is_safe_when_windowed_stdout_is_absent(self):
        with (
            patch.object(sys, "argv", ["NovaProfiles", "--version"]),
            patch.object(sys, "stdout", None),
        ):
            self.assertEqual(main.main(), 0)

    def test_smoke_test_exits_before_single_instance_or_real_controller(self):
        with (
            patch.object(sys, "argv", ["NovaProfiles", "--smoke-test"]),
            patch.object(main, "run_qml_smoke", return_value=7) as smoke,
            patch.object(main, "acquire_single_instance") as acquire,
            patch.object(main, "AppController") as controller,
        ):
            self.assertEqual(main.main(), 7)
        smoke.assert_called_once_with()
        acquire.assert_not_called()
        controller.assert_not_called()


if __name__ == "__main__":
    unittest.main()
