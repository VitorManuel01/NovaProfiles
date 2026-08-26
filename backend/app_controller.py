
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path

import psutil
from PySide6.QtCore import (
    QObject, Property, QSettings, QTimer, QUrl, Signal, Slot
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QSystemTrayIcon

from .hid_controller import (
    DEFAULT_DESTINATIONS,
    SuperNovaError,
    SuperNovaHID,
)
from .keyboard_catalog import (
    DESTINATIONS,
    destination_label,
    is_valid_destination,
)
from .profile_store import ProfileStore
from . import startup

APP_VERSION = "1.1.0"

class AppController(QObject):
    profilesChanged = Signal()
    selectedProfileChanged = Signal()
    activeProfileChanged = Signal()
    deviceConnectedChanged = Signal()
    autoSwitchEnabledChanged = Signal()
    startupEnabledChanged = Signal()
    minimizeToTrayChanged = Signal()
    restoreDefaultOnExitChanged = Signal()
    legacyServiceRunningChanged = Signal()
    toast = Signal(str)
    showWindowRequested = Signal()
    quitRequested = Signal()
    profileApplied = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hid = SuperNovaHID()
        self.store = ProfileStore()
        self.settings = QSettings()

        self._selected_profile_id = "default"
        self._active_profile_id = ""
        self._device_connected = self.hid.available()
        self._auto_switch = self.settings.value(
            "autoSwitch", True, type=bool
        )
        self._minimize_to_tray = self.settings.value(
            "minimizeToTray", True, type=bool
        )
        self._restore_default_on_exit = self.settings.value(
            "restoreDefaultOnExit", True, type=bool
        )
        self._startup_enabled = startup.is_enabled()
        self._legacy_service_running = False
        self._shutting_down = False
        self._last_device_error = ""
        self._last_device_poll = 0.0

        self.log_path = self.store.data_dir / "NovaProfiles.log"
        self._setup_logging()

        self.process_timer = QTimer(self)
        self.process_timer.setInterval(1000)
        self.process_timer.timeout.connect(self._poll_processes)
        self.process_timer.start()

        self.device_timer = QTimer(self)
        self.device_timer.setInterval(1500)
        self.device_timer.timeout.connect(self._poll_device)
        self.device_timer.start()

        self.service_timer = QTimer(self)
        self.service_timer.setInterval(5000)
        self.service_timer.timeout.connect(self._poll_legacy_service)
        self.service_timer.start()

        QTimer.singleShot(100, self._poll_legacy_service)
        QTimer.singleShot(250, self._initial_apply)

    def _setup_logging(self):
        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            encoding="utf-8",
        )
        logging.info("Nova Profiles %s started", APP_VERSION)

    @Property(str, constant=True)
    def appVersion(self):
        return APP_VERSION

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self):
        result = []
        for p in self.store.profiles:
            result.append({
                "id": p["id"],
                "name": p["name"],
                "exeName": p["exeName"],
                "exePath": p["exePath"],
                "active": p["id"] == self._active_profile_id,
                "selected": p["id"] == self._selected_profile_id,
                "isDefault": p["id"] == "default",
            })
        return result

    @Property("QVariantMap", notify=selectedProfileChanged)
    def selectedProfile(self):
        p = self.store.get(self._selected_profile_id) or self.store.get("default")
        if not p:
            return {}
        effective = {
            source: p["mappings"].get(source, DEFAULT_DESTINATIONS[source])
            for source in ("RB", "L4", "R4")
        }
        return {
            "id": p["id"],
            "name": p["name"],
            "exeName": p["exeName"],
            "exePath": p["exePath"],
            "isDefault": p["id"] == "default",
            "rb": effective["RB"],
            "rbLabel": destination_label(effective["RB"]),
            "l4": effective["L4"],
            "l4Label": destination_label(effective["L4"]),
            "r4": effective["R4"],
            "r4Label": destination_label(effective["R4"]),
        }

    @Property("QVariantList", constant=True)
    def destinationCatalog(self):
        return DESTINATIONS

    @Property(str, notify=activeProfileChanged)
    def activeProfileId(self):
        return self._active_profile_id

    @Property(str, notify=activeProfileChanged)
    def activeProfileName(self):
        p = self.store.get(self._active_profile_id)
        return p["name"] if p else "None"

    @Property(bool, notify=deviceConnectedChanged)
    def deviceConnected(self):
        return self._device_connected

    @Property(bool, notify=autoSwitchEnabledChanged)
    def autoSwitchEnabled(self):
        return self._auto_switch

    @Property(bool, notify=startupEnabledChanged)
    def startupEnabled(self):
        return self._startup_enabled

    @Property(bool, notify=minimizeToTrayChanged)
    def minimizeToTray(self):
        return self._minimize_to_tray

    @Property(bool, notify=restoreDefaultOnExitChanged)
    def restoreDefaultOnExit(self):
        return self._restore_default_on_exit

    @Property(bool, constant=True)
    def trayAvailable(self):
        return QSystemTrayIcon.isSystemTrayAvailable()

    @Property(bool, notify=legacyServiceRunningChanged)
    def legacyServiceRunning(self):
        return self._legacy_service_running

    @Property(str, constant=True)
    def dataFolder(self):
        return str(self.store.data_dir)

    @Slot(str)
    def selectProfile(self, profile_id):
        if self.store.get(profile_id) is None:
            return
        if self._selected_profile_id == profile_id:
            return
        self._selected_profile_id = profile_id
        self.selectedProfileChanged.emit()
        self.profilesChanged.emit()

    @Slot(str)
    def createProfile(self, name):
        p = self.store.create(name)
        self._selected_profile_id = p["id"]
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.toast.emit("Profile created")

    @Slot(str)
    def duplicateProfile(self, profile_id):
        p = self.store.duplicate(profile_id)
        if not p:
            return
        self._selected_profile_id = p["id"]
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.toast.emit("Profile duplicated")

    @Slot(str)
    def deleteProfile(self, profile_id):
        if not self.store.delete(profile_id):
            self.toast.emit("Default profile cannot be deleted")
            return
        if self._selected_profile_id == profile_id:
            self._selected_profile_id = "default"
        if self._active_profile_id == profile_id:
            self.applyProfile("default")
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.toast.emit("Profile deleted")

    @Slot(str, str)
    def renameProfile(self, profile_id, new_name):
        if profile_id == "default":
            return
        p = self.store.get(profile_id)
        name = new_name.strip()
        if not p or not name or p["name"] == name:
            return
        p["name"] = name
        self.store.save()
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()

    @Slot(str)
    def chooseExecutable(self, profile_id):
        if profile_id == "default":
            return
        p = self.store.get(profile_id)
        if not p:
            return
        start = p["exePath"] or str(Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            None,
            "Choose game executable",
            start,
            "Windows executables (*.exe);;All files (*.*)",
        )
        if not filename:
            return
        path = Path(filename)
        p["exePath"] = str(path)
        p["exeName"] = path.name
        self.store.save()
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.toast.emit(f"Game linked: {path.name}")

    @Slot(str)
    def clearExecutable(self, profile_id):
        p = self.store.get(profile_id)
        if not p or profile_id == "default":
            return
        p["exePath"] = ""
        p["exeName"] = ""
        self.store.save()
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()

    @Slot(str, str, str)
    def setMapping(self, profile_id, source, destination_key):
        if source not in ("RB", "L4", "R4"):
            return
        if not is_valid_destination(destination_key):
            self.toast.emit("Unsupported destination")
            return
        p = self.store.get(profile_id)
        if not p:
            return
        p["mappings"][source] = destination_key
        self.store.save()
        self.selectedProfileChanged.emit()
        self.toast.emit(f"{source} → {destination_label(destination_key)}")

    def _effective_mappings(self, p):
        return {
            source: p["mappings"].get(source, DEFAULT_DESTINATIONS[source])
            for source in ("RB", "L4", "R4")
        }

    @Slot(str, result=bool)
    def applyProfile(self, profile_id):
        p = self.store.get(profile_id)
        if not p:
            return False
        if self._legacy_service_running:
            self.toast.emit("Stop the old NSSM GameSirAutoProfile service first")
            return False

        try:
            self.hid.apply_mappings(self._effective_mappings(p))
            self._device_connected = True
            self.deviceConnectedChanged.emit()
            self._active_profile_id = profile_id
            self.activeProfileChanged.emit()
            self.profilesChanged.emit()
            logging.info("Applied profile: %s", p["name"])
            self.profileApplied.emit(p["name"])
            return True
        except Exception as exc:
            logging.exception("Profile apply failed")
            new_connected = self.hid.available()
            if new_connected != self._device_connected:
                self._device_connected = new_connected
                self.deviceConnectedChanged.emit()
            message = str(exc)
            if message != self._last_device_error:
                self.toast.emit(message)
                self._last_device_error = message
            return False

    @Slot()
    def applyDefault(self):
        self.applyProfile("default")

    def _profile_for_running_processes(self):
        process_rows = []
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                exe = proc.info.get("exe") or ""
                exe_norm = os.path.normcase(os.path.abspath(exe)) if exe else ""
                process_rows.append((name, exe_norm))
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue

        for p in self.store.profiles:
            if p["id"] == "default" or not p["exeName"]:
                continue

            expected_name = p["exeName"].lower()
            expected_path = (
                os.path.normcase(os.path.abspath(p["exePath"]))
                if p["exePath"] else ""
            )

            for running_name, running_path in process_rows:
                if expected_path and running_path and expected_path == running_path:
                    return p["id"]
                if running_name == expected_name:
                    return p["id"]

        return "default"

    def _poll_processes(self):
        if self._shutting_down or not self._auto_switch:
            return
        wanted = self._profile_for_running_processes()
        if wanted != self._active_profile_id and self._device_connected:
            self.applyProfile(wanted)

    def _poll_device(self):
        if self._shutting_down:
            return
        connected = self.hid.available()
        changed = connected != self._device_connected
        if changed:
            self._device_connected = connected
            self.deviceConnectedChanged.emit()
            if connected:
                self.toast.emit("Super Nova connected")
                logging.info("Super Nova connected")
            else:
                self.toast.emit("Super Nova disconnected")
                logging.info("Super Nova disconnected")

        if connected and changed:
            self._last_device_error = ""
            if self._auto_switch:
                QTimer.singleShot(250, self._poll_processes)
            elif self._active_profile_id:
                QTimer.singleShot(
                    250, lambda: self.applyProfile(self._active_profile_id)
                )

    def _poll_legacy_service(self):
        running = False
        if os.name == "nt":
            try:
                cp = subprocess.run(
                    ["sc", "query", "GameSirAutoProfile"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                output = (cp.stdout or "") + (cp.stderr or "")
                running = "RUNNING" in output.upper()
            except Exception:
                running = False
        if running != self._legacy_service_running:
            self._legacy_service_running = running
            self.legacyServiceRunningChanged.emit()

    def _initial_apply(self):
        if self._legacy_service_running:
            return
        if self._device_connected and self._auto_switch:
            self._poll_processes()

    @Slot(bool)
    def setAutoSwitchEnabled(self, value):
        value = bool(value)
        if value == self._auto_switch:
            return
        self._auto_switch = value
        self.settings.setValue("autoSwitch", value)
        self.autoSwitchEnabledChanged.emit()
        if value:
            QTimer.singleShot(50, self._poll_processes)

    @Slot()
    def toggleAutoSwitch(self):
        self.setAutoSwitchEnabled(not self._auto_switch)

    @Slot(bool)
    def setMinimizeToTray(self, value):
        value = bool(value)
        if value == self._minimize_to_tray:
            return
        self._minimize_to_tray = value
        self.settings.setValue("minimizeToTray", value)
        self.minimizeToTrayChanged.emit()

    @Slot(bool)
    def setRestoreDefaultOnExit(self, value):
        value = bool(value)
        if value == self._restore_default_on_exit:
            return
        self._restore_default_on_exit = value
        self.settings.setValue("restoreDefaultOnExit", value)
        self.restoreDefaultOnExitChanged.emit()

    @Slot(bool)
    def setStartupEnabled(self, value):
        try:
            startup.set_enabled(bool(value))
            self._startup_enabled = startup.is_enabled()
            self.startupEnabledChanged.emit()
            self.toast.emit(
                "Starts with Windows" if self._startup_enabled
                else "Windows startup disabled"
            )
        except Exception as exc:
            self.toast.emit(str(exc))

    @Slot()
    def exportProfiles(self):
        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Export profiles",
            str(Path.home() / "NovaProfiles-profiles.json"),
            "JSON (*.json)",
        )
        if not filename:
            return
        try:
            self.store.export_file(Path(filename))
            self.toast.emit("Profiles exported")
        except Exception as exc:
            self.toast.emit(f"Export failed: {exc}")

    @Slot()
    def importProfiles(self):
        filename, _ = QFileDialog.getOpenFileName(
            None,
            "Import profiles",
            str(Path.home()),
            "JSON (*.json)",
        )
        if not filename:
            return
        try:
            self.store.import_file(Path(filename))
            self._selected_profile_id = "default"
            self.profilesChanged.emit()
            self.selectedProfileChanged.emit()
            self.toast.emit("Profiles imported")
        except Exception as exc:
            self.toast.emit(f"Import failed: {exc}")

    @Slot()
    def openDataFolder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.data_dir)))

    @Slot()
    def openLogFile(self):
        if not self.log_path.exists():
            self.log_path.touch()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_path)))

    @Slot(result=str)
    def deviceDiagnostics(self):
        return json.dumps(
            self.hid.diagnostic_devices(),
            ensure_ascii=False,
            indent=2,
        )

    @Slot()
    def requestShowWindow(self):
        self.showWindowRequested.emit()

    @Slot()
    def quitApplication(self):
        self.quitRequested.emit()

    def shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        self.process_timer.stop()
        self.device_timer.stop()
        self.service_timer.stop()
        if (
            self._restore_default_on_exit
            and self._device_connected
            and not self._legacy_service_running
        ):
            try:
                self.hid.apply_default()
                logging.info("Default restored on exit")
            except Exception:
                logging.exception("Could not restore Default on exit")
