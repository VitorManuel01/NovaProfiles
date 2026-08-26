
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

class TrayController:
    def __init__(self, app_controller, icon_path: Path, parent=None):
        self.app = app_controller
        self.tray = QSystemTrayIcon(QIcon(str(icon_path)), parent)
        self.tray.setToolTip("Nova Profiles")
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)

        self.app.profilesChanged.connect(self.rebuild)
        self.app.activeProfileChanged.connect(self._update_tooltip)
        self.app.autoSwitchEnabledChanged.connect(self.rebuild)
        self.app.profileApplied.connect(self._profile_applied)
        self.tray.activated.connect(self._activated)

        self.rebuild()
        self.tray.show()

    def rebuild(self):
        self.menu.clear()

        open_action = QAction("Open Nova Profiles", self.menu)
        open_action.triggered.connect(self.app.requestShowWindow)
        self.menu.addAction(open_action)

        auto_action = QAction(
            "Pause auto switching"
            if self.app.autoSwitchEnabled
            else "Resume auto switching",
            self.menu,
        )
        auto_action.triggered.connect(self.app.toggleAutoSwitch)
        self.menu.addAction(auto_action)

        self.menu.addSeparator()

        for p in self.app.profiles:
            label = p["name"]
            if p["id"] == self.app.activeProfileId:
                label = "● " + label
            action = QAction(label, self.menu)
            pid = p["id"]
            action.triggered.connect(
                lambda checked=False, profile_id=pid:
                    self.app.applyProfile(profile_id)
            )
            self.menu.addAction(action)

        self.menu.addSeparator()

        default_action = QAction("Apply Default", self.menu)
        default_action.triggered.connect(self.app.applyDefault)
        self.menu.addAction(default_action)

        exit_action = QAction("Exit", self.menu)
        exit_action.triggered.connect(self.app.quitApplication)
        self.menu.addAction(exit_action)

        self._update_tooltip()

    def _activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.app.requestShowWindow()

    def _update_tooltip(self):
        active = self.app.activeProfileName
        state = "Connected" if self.app.deviceConnected else "Disconnected"
        self.tray.setToolTip(f"Nova Profiles · {state}\nActive: {active}")

    def _profile_applied(self, name):
        self._update_tooltip()
