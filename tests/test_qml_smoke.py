from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow


ROOT = Path(__file__).resolve().parents[1]


class MockController(QObject):
    toast = Signal(str)
    lastErrorChanged = Signal()
    importPreviewChanged = Signal()

    def __init__(self):
        super().__init__()
        self._last_error = ""

    @Property(str, constant=True)
    def appVersion(self):
        return "test"

    @Property("QVariantList", constant=True)
    def profiles(self):
        return [
            {
                "id": "default",
                "name": "Default",
                "exeName": "",
                "exePath": "",
                "selected": True,
                "active": True,
                "isDefault": True,
            }
        ]

    @Property("QVariantMap", constant=True)
    def selectedProfile(self):
        return {
            "id": "default",
            "name": "Default",
            "exeName": "",
            "exePath": "",
            "isDefault": True,
            "rb": "gp:04",
            "l4": "gp:24",
            "r4": "gp:25",
        }

    @Property("QVariantList", constant=True)
    def destinationCatalog(self):
        return [
            {"key": "gp:04", "label": "RB"},
            {"key": "gp:24", "label": "L4"},
            {"key": "gp:25", "label": "R4"},
        ]

    @Property(str, constant=True)
    def activeProfileId(self):
        return "default"

    @Property(str, constant=True)
    def activeProfileName(self):
        return "Default"

    @Property(bool, constant=True)
    def deviceConnected(self):
        return True

    @Property(bool, constant=True)
    def pendingChanges(self):
        return False

    @Property(bool, constant=True)
    def applyInProgress(self):
        return False

    @Property(bool, constant=True)
    def hardwareStateValid(self):
        return True

    @Property(str, notify=lastErrorChanged)
    def lastError(self):
        return self._last_error

    def set_last_error(self, message):
        self._last_error = message
        self.lastErrorChanged.emit()

    @Property(str, constant=True)
    def profileConflict(self):
        return ""

    @Property("QVariantMap", notify=importPreviewChanged)
    def importPreview(self):
        return {}

    @Property(str, constant=True)
    def legacyServiceState(self):
        return "stopped"

    @Property(bool, constant=True)
    def legacyServiceRunning(self):
        return False

    @Property(bool, constant=True)
    def autoSwitchEnabled(self):
        return True

    @Property(bool, constant=True)
    def startupEnabled(self):
        return False

    @Property(bool, constant=True)
    def minimizeToTray(self):
        return True

    @Property(bool, constant=True)
    def restoreDefaultOnExit(self):
        return True

    @Property(bool, constant=True)
    def trayAvailable(self):
        return True

    @Slot(str, result=bool)
    def applyProfile(self, _profile_id):
        return True

    @Slot(str)
    def selectProfile(self, _profile_id):
        pass

    @Slot(str)
    def createProfile(self, _name):
        pass

    @Slot(str, str)
    def renameProfile(self, _profile_id, _name):
        pass

    @Slot(str, str, str)
    def setMapping(self, _profile_id, _source, _destination):
        pass

    @Slot(bool)
    def setAutoSwitchEnabled(self, _enabled):
        pass

    @Slot()
    def quitApplication(self):
        pass


class QmlSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

    def test_main_window_loads_at_minimum_size_without_qml_warnings(self):
        messages = []

        def handler(mode, context, message):
            source = str(getattr(context, "file", "") or "")
            if source.lower().endswith(".qml"):
                messages.append((mode, source, int(getattr(context, "line", 0)), message))

        previous_handler = qInstallMessageHandler(handler)
        try:
            controller = MockController()
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("app", controller)
            engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
            self.assertTrue(engine.rootObjects(), messages)

            window = engine.rootObjects()[0]
            window.setWidth(900)
            window.setHeight(620)
            window.show()
            for _ in range(5):
                self.qt_app.processEvents()

            self.assertEqual(window.property("mappingState"), "active")
            main_scroll = window.findChild(QObject, "mainScroll")
            main_column = window.findChild(QObject, "mainColumn")
            sidebar = window.findChild(QObject, "sidebar")
            self.assertIsNotNone(main_scroll)
            self.assertIsNotNone(main_column)
            self.assertIsNotNone(sidebar)
            self.assertLessEqual(
                float(main_scroll.property("contentWidth")),
                float(main_scroll.property("width")) + 1.0,
            )
            self.assertLessEqual(
                float(main_column.property("width")),
                float(main_scroll.property("width")) + 1.0,
            )
            self.assertGreaterEqual(float(sidebar.property("width")), 236.0)

            toast_box = window.findChild(QObject, "toastBox")
            toast_timer = window.findChild(QObject, "toastTimer")
            self.assertIsNotNone(toast_box)
            self.assertIsNotNone(toast_timer)
            controller.set_last_error("Persistent diagnostic")
            self.qt_app.processEvents()
            self.assertTrue(bool(toast_box.property("visible")))
            self.assertFalse(bool(toast_timer.property("running")))
            controller.set_last_error("")
            self.qt_app.processEvents()
            self.assertFalse(bool(toast_box.property("visible")))

            screenshot_path = os.environ.get("NOVA_QML_SCREENSHOT")
            if screenshot_path:
                # Keep the assertions above at the supported minimum size, but
                # publish a roomier documentation image of the same UI state.
                window.setWidth(1120)
                window.setHeight(740)
                for _ in range(3):
                    self.qt_app.processEvents()
                screenshot = Path(screenshot_path)
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                image = QQuickWindow.grabWindow(window)
                self.assertFalse(image.isNull())
                self.assertTrue(image.save(str(screenshot)))

            self.assertFalse(messages, messages)
            window.close()
            engine.deleteLater()
        finally:
            qInstallMessageHandler(previous_handler)


if __name__ == "__main__":
    unittest.main()
