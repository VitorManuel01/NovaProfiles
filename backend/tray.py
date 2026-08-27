
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
        self.app.deviceConnectedChanged.connect(self.rebuild)
        self.app.autoSwitchEnabledChanged.connect(self.rebuild)
        self.app.legacyServiceStateChanged.connect(self.rebuild)
        self.app.applyInProgressChanged.connect(self.rebuild)
        self.app.pendingChangesChanged.connect(self._update_tooltip)
        self.app.lastErrorChanged.connect(self._update_tooltip)
        self.app.profileApplied.connect(self._profile_applied)
        self.tray.activated.connect(self._activated)

        self.rebuild()
        self.tray.show()

    def rebuild(self):
        self.menu.clear()

        open_action = QAction(self.app.tr("Open Nova Profiles"), self.menu)
        open_action.triggered.connect(self.app.requestShowWindow)
        self.menu.addAction(open_action)

        auto_action = QAction(
            self.app.tr("Pause auto switching")
            if self.app.autoSwitchEnabled
            else self.app.tr("Resume auto switching"),
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
            action.setEnabled(
                self.app.deviceConnected
                and self.app.legacyServiceState == "stopped"
                and not self.app.applyInProgress
            )
            pid = p["id"]
            action.triggered.connect(
                lambda checked=False, profile_id=pid:
                    self.app.applyProfile(profile_id)
            )
            self.menu.addAction(action)

        self.menu.addSeparator()

        default_action = QAction(self.app.tr("Apply Default"), self.menu)
        default_action.triggered.connect(self.app.applyDefault)
        default_action.setEnabled(
            self.app.deviceConnected
            and self.app.legacyServiceState == "stopped"
            and not self.app.applyInProgress
        )
        self.menu.addAction(default_action)

        exit_action = QAction(self.app.tr("Exit"), self.menu)
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
        if self.app.applyInProgress:
            state = self.app.tr("Applying profile…")
        elif self.app.legacyServiceState == "running":
            state = self.app.tr("Blocked by old service")
        elif self.app.legacyServiceState == "unknown":
            state = self.app.tr("Service status unknown")
        else:
            state = (
                self.app.tr("Connected")
                if self.app.deviceConnected
                else self.app.tr("Disconnected")
            )
        suffix = (
            " · " + self.app.tr("Pending changes")
            if self.app.pendingChanges
            else ""
        )
        self.tray.setToolTip(
            self.app.tr("Nova Profiles · {state}\nActive: {active}{suffix}").format(
                state=state,
                active=active,
                suffix=suffix,
            )[:127]
        )

    def _profile_applied(self, name):
        self._update_tooltip()
