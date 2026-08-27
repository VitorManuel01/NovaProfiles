from __future__ import annotations

import hashlib
import ctypes
import json
import logging
import ntpath
import os
import time
from ctypes import wintypes
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable

import psutil
from PySide6.QtCore import QObject, Property, QSettings, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QSystemTrayIcon

from version import __version__ as APP_VERSION

from . import startup
from .hid_controller import DEFAULT_DESTINATIONS, DeviceProbe, SuperNovaHID
from .keyboard_catalog import DESTINATIONS, destination_label, is_valid_destination
from .profile_store import ImportPreview, ProfileStore

LOGGER = logging.getLogger("NovaProfiles")
SERVICE_NAME = "GameSirAutoProfile"


class LegacyServiceState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceCheck:
    state: LegacyServiceState
    detail: str = ""


@dataclass(frozen=True)
class AppliedState:
    profile_id: str
    profile_revision: int
    mapping_hash: str
    connection_generation: int
    device_identity: str


@dataclass(frozen=True)
class ApplyRequest:
    profile_id: str
    profile_revision: int
    mappings: dict[str, str]
    mapping_hash: str
    automatic: bool
    catalog_generation: int


@dataclass(frozen=True)
class ApplyWorkerResult:
    service: ServiceCheck
    device_identity: str


@dataclass(frozen=True)
class ProcessScanResult:
    wanted_profile_id: str
    conflicting_profile_ids: tuple[str, ...] = ()


@dataclass
class _Job:
    name: str
    future: Future
    callback: Callable[[Any, BaseException | None], None]


class LegacyServiceBlocked(RuntimeError):
    def __init__(self, check: ServiceCheck):
        self.check = check
        super().__init__(check.detail or check.state.value)


class _ServiceStatusProcess(ctypes.Structure):
    _fields_ = [
        ("service_type", wintypes.DWORD),
        ("current_state", wintypes.DWORD),
        ("controls_accepted", wintypes.DWORD),
        ("win32_exit_code", wintypes.DWORD),
        ("service_specific_exit_code", wintypes.DWORD),
        ("check_point", wintypes.DWORD),
        ("wait_hint", wintypes.DWORD),
        ("process_id", wintypes.DWORD),
        ("service_flags", wintypes.DWORD),
    ]


def _service_check_from_windows_state(state: int) -> ServiceCheck:
    if state == 1:  # SERVICE_STOPPED
        return ServiceCheck(LegacyServiceState.STOPPED)
    if state in {2, 3, 4, 5, 6, 7}:
        # Starting, stopping, pausing and paused services may still own the
        # interface. Only SERVICE_STOPPED is safe enough to permit HID writes.
        detail = "" if state == 4 else f"The old service is in state {state}"
        return ServiceCheck(LegacyServiceState.RUNNING, detail)
    return ServiceCheck(
        LegacyServiceState.UNKNOWN,
        f"The old service returned an unknown state code: {state}",
    )


def _query_legacy_service_default() -> ServiceCheck:
    if os.name != "nt":
        return ServiceCheck(LegacyServiceState.STOPPED)

    service_manager = None
    service = None
    try:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        advapi32.OpenSCManagerW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        )
        advapi32.OpenSCManagerW.restype = wintypes.HANDLE
        advapi32.OpenServiceW.argtypes = (
            wintypes.HANDLE,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        )
        advapi32.OpenServiceW.restype = wintypes.HANDLE
        advapi32.QueryServiceStatusEx.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_ubyte),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        )
        advapi32.QueryServiceStatusEx.restype = wintypes.BOOL
        advapi32.CloseServiceHandle.argtypes = (wintypes.HANDLE,)
        advapi32.CloseServiceHandle.restype = wintypes.BOOL

        service_manager = advapi32.OpenSCManagerW(None, None, 0x0001)
        if not service_manager:
            raise ctypes.WinError(ctypes.get_last_error())

        ctypes.set_last_error(0)
        service = advapi32.OpenServiceW(service_manager, SERVICE_NAME, 0x0004)
        if not service:
            error_code = ctypes.get_last_error()
            if error_code == 1060:  # ERROR_SERVICE_DOES_NOT_EXIST
                return ServiceCheck(LegacyServiceState.STOPPED)
            raise ctypes.WinError(error_code)

        status = _ServiceStatusProcess()
        bytes_needed = wintypes.DWORD()
        succeeded = advapi32.QueryServiceStatusEx(
            service,
            0,
            ctypes.cast(ctypes.byref(status), ctypes.POINTER(ctypes.c_ubyte)),
            ctypes.sizeof(status),
            ctypes.byref(bytes_needed),
        )
        if not succeeded:
            raise ctypes.WinError(ctypes.get_last_error())
        return _service_check_from_windows_state(int(status.current_state))
    except Exception as exc:
        return ServiceCheck(
            LegacyServiceState.UNKNOWN,
            f"Could not check the old auto-profile service: {exc}",
        )
    finally:
        if "advapi32" in locals():
            if service:
                advapi32.CloseServiceHandle(service)
            if service_manager:
                advapi32.CloseServiceHandle(service_manager)


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
    legacyServiceStateChanged = Signal()
    pendingChangesChanged = Signal()
    hardwareStateValidChanged = Signal()
    applyInProgressChanged = Signal()
    lastErrorChanged = Signal()
    applyErrorChanged = Signal()
    profileConflictChanged = Signal()
    importPreviewChanged = Signal()
    retryStateChanged = Signal()
    statusChanged = Signal()
    toast = Signal(str)
    showWindowRequested = Signal()
    quitRequested = Signal()
    profileApplied = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        hid: Any | None = None,
        store: ProfileStore | None = None,
        settings: Any | None = None,
        process_iter: Callable[..., Any] | None = None,
        service_query: Callable[[], ServiceCheck | str | bool] | None = None,
        startup_module: Any = startup,
        executor: Executor | None = None,
        start_timers: bool = True,
    ):
        super().__init__(parent)
        self.hid = hid if hid is not None else SuperNovaHID()
        self.store = store if store is not None else ProfileStore()
        self.settings = settings if settings is not None else QSettings()
        self._process_iter = process_iter or psutil.process_iter
        self._service_query = service_query or _query_legacy_service_default
        self._startup_module = startup_module
        self._executor_owned = executor is None
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="NovaProfiles-IO",
        )
        self._jobs: list[_Job] = []

        self._selected_profile_id = "default"
        self._active_profile_id = ""
        self._desired_profile_id = "default"
        self._last_successful_profile_id = ""
        self._applied_state: AppliedState | None = None
        self._device_connected = False
        self._device_identity = ""
        self._connection_generation = 0
        self._auto_switch = self.settings.value("autoSwitch", True, type=bool)
        self._minimize_to_tray = self.settings.value(
            "minimizeToTray", True, type=bool
        )
        self._restore_default_on_exit = self.settings.value(
            "restoreDefaultOnExit", True, type=bool
        )
        self._startup_enabled = self._startup_module.is_enabled()
        self._legacy_service_state = LegacyServiceState.UNKNOWN
        self._legacy_service_detail = ""
        self._process_scan_generation = 0
        self._catalog_generation = 0
        self._shutting_down = False
        self._apply_in_progress = False
        self._queued_apply: tuple[str, bool] | None = None
        self._device_poll_inflight = False
        self._service_poll_inflight = False
        self._process_poll_inflight = False
        self._last_error = ""
        self._apply_error = ""
        self._last_device_error = ""
        self._last_service_error = ""
        self._profile_conflict = ""
        self._import_preview_obj: ImportPreview | None = None
        self._last_backup_path = ""
        self._auto_failure_count = 0
        self._next_auto_retry_at = 0.0

        self.log_path = self.store.data_dir / "NovaProfiles.log"
        self._setup_logging()

        self.work_timer = QTimer(self)
        self.work_timer.setInterval(40)
        self.work_timer.timeout.connect(self._drain_jobs)

        self.process_timer = QTimer(self)
        self.process_timer.setInterval(1000)
        self.process_timer.timeout.connect(self._poll_processes)

        self.device_timer = QTimer(self)
        self.device_timer.setInterval(1500)
        self.device_timer.timeout.connect(self._poll_device)

        self.service_timer = QTimer(self)
        self.service_timer.setInterval(5000)
        self.service_timer.timeout.connect(self._poll_legacy_service)

        if start_timers:
            self.process_timer.start()
            self.device_timer.start()
            self.service_timer.start()
            QTimer.singleShot(0, self._poll_legacy_service)
            QTimer.singleShot(0, self._poll_device)

    def _setup_logging(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        for handler in list(LOGGER.handlers):
            if getattr(handler, "_nova_profiles_handler", False):
                LOGGER.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
        handler = RotatingFileHandler(
            self.log_path,
            maxBytes=1_048_576,
            backupCount=3,
            encoding="utf-8",
        )
        handler._nova_profiles_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False
        LOGGER.info("Nova Profiles %s started", APP_VERSION)
        if self.store.recovery_error:
            backup = str(self.store.recovery_backup_path or self.store.path)
            message = self.tr(
                "Profiles could not be read and defaults were restored. "
                "The original file was preserved at: %1"
            ).replace("%1", backup)
            self._last_error = message
            LOGGER.error("Profile recovery: %s (%s)", message, self.store.recovery_error)
            QTimer.singleShot(0, lambda: self.toast.emit(message))

    @staticmethod
    def _mapping_hash(mappings: dict[str, str]) -> str:
        canonical = json.dumps(
            mappings,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.sha256(canonical).hexdigest()

    def _effective_mappings(self, profile: dict[str, Any]) -> dict[str, str]:
        return {
            source: profile["mappings"].get(
                source,
                DEFAULT_DESTINATIONS[source],
            )
            for source in ("RB", "L4", "R4")
        }

    def _profile_display_name(self, profile: dict[str, Any]) -> str:
        return self.tr("Default") if profile.get("id") == "default" else profile["name"]

    def _is_applied(self, profile_id: str | None = None) -> bool:
        state = self._applied_state
        if state is None or not self._device_connected:
            return False
        if state.connection_generation != self._connection_generation:
            return False
        if state.device_identity != self._device_identity:
            return False
        if self._legacy_service_state is not LegacyServiceState.STOPPED:
            return False
        if profile_id is not None and state.profile_id != profile_id:
            return False
        profile = self.store.get(state.profile_id)
        if profile is None:
            return False
        mappings = self._effective_mappings(profile)
        return self._mapping_hash(mappings) == state.mapping_hash

    def _notify_hardware_state(self):
        previous_active = self._active_profile_id
        self._active_profile_id = (
            self._applied_state.profile_id if self._is_applied() else ""
        )
        if previous_active != self._active_profile_id:
            self.activeProfileChanged.emit()
        self.profilesChanged.emit()
        self.pendingChangesChanged.emit()
        self.hardwareStateValidChanged.emit()
        self.statusChanged.emit()

    def _invalidate_applied_state(self, reason: str):
        if self._applied_state is not None:
            LOGGER.info("Applied state invalidated: %s", reason)
        self._applied_state = None
        self._notify_hardware_state()

    def _set_last_error(self, message: str, *, show_toast: bool = False):
        message = str(message or "")
        changed = message != self._last_error
        self._last_error = message
        if changed:
            self.lastErrorChanged.emit()
            self.statusChanged.emit()
            if message and show_toast:
                self.toast.emit(message)

    def _set_apply_error(self, message: str, *, show_toast: bool = False):
        message = str(message or "")
        previous = self._apply_error
        if message == previous:
            if message and show_toast:
                self._set_last_error(message, show_toast=True)
            return
        self._apply_error = message
        self.applyErrorChanged.emit()
        self.statusChanged.emit()
        if message:
            self._set_last_error(message, show_toast=show_toast)
        elif previous and self._last_error == previous:
            self._set_last_error("")

    def _set_service_error(self, message: str, *, show_toast: bool = False):
        message = str(message or "")
        previous = self._last_service_error
        self._last_service_error = message
        if message:
            self._set_last_error(message, show_toast=show_toast)
        elif previous and self._last_error == previous:
            self._set_last_error("")

    def _set_profile_conflict(self, message: str):
        if message == self._profile_conflict:
            return
        self._profile_conflict = message
        self.profileConflictChanged.emit()
        self.statusChanged.emit()
        if message:
            self.toast.emit(message)

    def _set_apply_in_progress(self, value: bool):
        value = bool(value)
        if value == self._apply_in_progress:
            return
        self._apply_in_progress = value
        self.applyInProgressChanged.emit()
        self.pendingChangesChanged.emit()
        self.statusChanged.emit()

    def _submit(
        self,
        name: str,
        function: Callable[[], Any],
        callback: Callable[[Any, BaseException | None], None],
    ) -> bool:
        if self._shutting_down:
            return False
        try:
            future = self._executor.submit(function)
        except Exception as exc:
            callback(None, exc)
            return False
        self._jobs.append(_Job(name=name, future=future, callback=callback))
        if not self.work_timer.isActive():
            self.work_timer.start()
        return True

    @Slot()
    def _drain_jobs(self):
        remaining: list[_Job] = []
        for job in self._jobs:
            if not job.future.done():
                remaining.append(job)
                continue
            try:
                result = job.future.result()
                error = None
            except BaseException as exc:
                result = None
                error = exc
            try:
                job.callback(result, error)
            except Exception:
                LOGGER.exception("Unhandled completion error for job %s", job.name)
        self._jobs = remaining
        if not remaining:
            self.work_timer.stop()

    @Property(str, constant=True)
    def appVersion(self):
        return APP_VERSION

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self):
        result = []
        for profile in self.store.profiles:
            result.append(
                {
                    "id": profile["id"],
                    "name": self._profile_display_name(profile),
                    "exeName": profile["exeName"],
                    "exePath": profile["exePath"],
                    "revision": profile["revision"],
                    "active": self._is_applied(profile["id"]),
                    "selected": profile["id"] == self._selected_profile_id,
                    "isDefault": profile["id"] == "default",
                }
            )
        return result

    @Property("QVariantMap", notify=selectedProfileChanged)
    def selectedProfile(self):
        profile = self.store.get(self._selected_profile_id) or self.store.get("default")
        if not profile:
            return {}
        effective = self._effective_mappings(profile)
        return {
            "id": profile["id"],
            "name": self._profile_display_name(profile),
            "exeName": profile["exeName"],
            "exePath": profile["exePath"],
            "revision": profile["revision"],
            "isDefault": profile["id"] == "default",
            "rb": effective["RB"],
            "rbLabel": destination_label(effective["RB"]),
            "l4": effective["L4"],
            "l4Label": destination_label(effective["L4"]),
            "r4": effective["R4"],
            "r4Label": destination_label(effective["R4"]),
        }

    @Property("QVariantList", constant=True)
    def destinationCatalog(self):
        result = []
        for item in DESTINATIONS:
            translated = dict(item)
            prefix = self.tr("Gamepad") if item["group"] == "Gamepad" else self.tr("Keyboard")
            technical = item["label"].split(" · ", 1)[-1]
            translated["label"] = f"{prefix} · {technical}"
            translated["group"] = prefix
            result.append(translated)
        return result

    @Property(str, notify=activeProfileChanged)
    def activeProfileId(self):
        return self._active_profile_id

    @Property(str, notify=activeProfileChanged)
    def activeProfileName(self):
        profile = self.store.get(self._active_profile_id)
        return self._profile_display_name(profile) if profile else self.tr("None")

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
        return self._legacy_service_state is LegacyServiceState.RUNNING

    @Property(str, notify=legacyServiceStateChanged)
    def legacyServiceState(self):
        return self._legacy_service_state.value

    @Property(bool, notify=pendingChangesChanged)
    def pendingChanges(self):
        return self._apply_in_progress or not self._is_applied(
            self._selected_profile_id
        )

    @Property(bool, notify=hardwareStateValidChanged)
    def hardwareStateValid(self):
        return self._is_applied()

    @Property(bool, notify=applyInProgressChanged)
    def applyInProgress(self):
        return self._apply_in_progress

    @Property(str, notify=lastErrorChanged)
    def lastError(self):
        return self._last_error

    @Property(str, notify=applyErrorChanged)
    def applyError(self):
        return self._apply_error

    @Property(str, notify=profileConflictChanged)
    def profileConflict(self):
        return self._profile_conflict

    @Property("QVariantMap", notify=importPreviewChanged)
    def importPreview(self):
        if self._import_preview_obj is None:
            return {}
        return self._import_preview_obj.as_dict()

    @Property(str, notify=importPreviewChanged)
    def lastBackupPath(self):
        return self._last_backup_path

    @Property(int, notify=retryStateChanged)
    def retryDelaySeconds(self):
        return max(0, int(self._next_auto_retry_at - time.monotonic() + 0.999))

    @Property(str, constant=True)
    def dataFolder(self):
        return str(self.store.data_dir)

    @Slot()
    def clearLastError(self):
        self._set_last_error("")

    @Slot(str)
    def selectProfile(self, profile_id):
        if self.store.get(profile_id) is None or self._selected_profile_id == profile_id:
            return
        self._selected_profile_id = profile_id
        self.selectedProfileChanged.emit()
        self.profilesChanged.emit()
        self.pendingChangesChanged.emit()

    def _profile_write_failed(self, operation: str, exc: BaseException):
        LOGGER.exception("Profile operation failed: %s", operation)
        message = self.tr("Could not save profiles: %1").replace("%1", str(exc))
        self._set_last_error(message, show_toast=True)
        # Re-publish authoritative data so controls that changed optimistically
        # can restore the persisted value.
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.pendingChangesChanged.emit()

    def _after_profile_mutation(
        self,
        profile_id: str,
        previous_revision: int,
        *,
        mappings_may_have_changed: bool = False,
    ):
        updated = self.store.get(profile_id)
        if updated and updated["revision"] != previous_revision:
            self._process_scan_generation += 1
            if self._applied_state and self._applied_state.profile_id == profile_id:
                updated_hash = self._mapping_hash(self._effective_mappings(updated))
                if updated_hash != self._applied_state.mapping_hash:
                    self._invalidate_applied_state("profile mappings edited")
                else:
                    self._applied_state = replace(
                        self._applied_state,
                        profile_revision=updated["revision"],
                    )
                    self._notify_hardware_state()
            else:
                self.pendingChangesChanged.emit()
            if (
                mappings_may_have_changed
                and self._apply_in_progress
                and self._desired_profile_id == profile_id
            ):
                self._request_apply(profile_id, automatic=False)

    @Slot(str, result=bool)
    def createProfile(self, name):
        try:
            profile = self.store.create(name)
        except Exception as exc:
            self._profile_write_failed("create", exc)
            return False
        self._selected_profile_id = profile["id"]
        self._process_scan_generation += 1
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.pendingChangesChanged.emit()
        self.toast.emit(self.tr("Profile created"))
        return True

    @Slot(str, result=bool)
    def duplicateProfile(self, profile_id):
        try:
            original = self.store.get(profile_id)
            if not original:
                return False
            copy_name = self.tr("%1 Copy").replace(
                "%1", self._profile_display_name(original)
            )
            profile = self.store.duplicate(profile_id, copy_name=copy_name)
        except Exception as exc:
            self._profile_write_failed("duplicate", exc)
            return False
        if not profile:
            return False
        self._selected_profile_id = profile["id"]
        self._process_scan_generation += 1
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.pendingChangesChanged.emit()
        self.toast.emit(self.tr("Profile duplicated"))
        return True

    @Slot(str, result=bool)
    def deleteProfile(self, profile_id):
        was_active = bool(
            self._applied_state and self._applied_state.profile_id == profile_id
        )
        was_desired = self._desired_profile_id == profile_id
        was_last_successful = self._last_successful_profile_id == profile_id
        try:
            deleted = self.store.delete(profile_id)
        except Exception as exc:
            self._profile_write_failed("delete", exc)
            return False
        if not deleted:
            self.toast.emit(self.tr("Default profile cannot be deleted"))
            return False
        self._process_scan_generation += 1
        if self._selected_profile_id == profile_id:
            self._selected_profile_id = "default"
        if was_desired:
            self._desired_profile_id = "default"
        if was_last_successful:
            self._last_successful_profile_id = ""
        if self._queued_apply and self._queued_apply[0] == profile_id:
            self._queued_apply = ("default", False)
        if was_active:
            self._invalidate_applied_state("active profile deleted")
        # A historical success alone must not replace a different profile that
        # is currently being written. Active/desired state is authoritative.
        if self._device_connected and (was_active or was_desired):
            self._request_apply("default", automatic=False)
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.pendingChangesChanged.emit()
        self.toast.emit(self.tr("Profile deleted"))
        return True

    @Slot(str, str, result=bool)
    def renameProfile(self, profile_id, new_name):
        if profile_id == "default":
            return False
        profile = self.store.get(profile_id)
        name = new_name.strip()
        if not profile or not name or profile["name"] == name:
            return bool(profile and name)
        try:
            self.store.rename(profile_id, name)
        except Exception as exc:
            self._profile_write_failed("rename", exc)
            return False
        self._after_profile_mutation(profile_id, profile["revision"])
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        return True

    @Slot(str, result=bool)
    def chooseExecutable(self, profile_id):
        if profile_id == "default":
            return False
        profile = self.store.get(profile_id)
        if not profile:
            return False
        start = profile["exePath"] or str(Path.home())
        filename, _ = QFileDialog.getOpenFileName(
            None,
            self.tr("Choose game executable"),
            start,
            self.tr("Windows executables (*.exe);;All files (*.*)"),
        )
        if not filename:
            return False
        path = Path(filename)
        try:
            self.store.set_executable(profile_id, str(path), path.name)
        except Exception as exc:
            self._profile_write_failed("link executable", exc)
            return False
        self._after_profile_mutation(profile_id, profile["revision"])
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.toast.emit(
            self.tr("Game linked: %1").replace("%1", path.name)
        )
        return True

    @Slot(str, result=bool)
    def clearExecutable(self, profile_id):
        profile = self.store.get(profile_id)
        if not profile or profile_id == "default":
            return False
        try:
            self.store.set_executable(profile_id, "", "")
        except Exception as exc:
            self._profile_write_failed("clear executable", exc)
            return False
        self._after_profile_mutation(profile_id, profile["revision"])
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        return True

    @Slot(str, str, str, result=bool)
    def setMapping(self, profile_id, source, destination_key):
        if source not in ("RB", "L4", "R4"):
            return False
        if not is_valid_destination(destination_key):
            self.toast.emit(self.tr("Unsupported destination"))
            return False
        profile = self.store.get(profile_id)
        if not profile:
            return False
        try:
            self.store.set_mapping(profile_id, source, destination_key)
        except Exception as exc:
            self._profile_write_failed("set mapping", exc)
            return False
        self._after_profile_mutation(
            profile_id,
            profile["revision"],
            mappings_may_have_changed=True,
        )
        self.selectedProfileChanged.emit()
        self.profilesChanged.emit()
        self.toast.emit(
            self.tr("%1 → %2")
            .replace("%1", source)
            .replace("%2", destination_label(destination_key))
        )
        return True

    def _coerce_service_check(self, value: Any) -> ServiceCheck:
        if isinstance(value, ServiceCheck):
            return value
        if isinstance(value, LegacyServiceState):
            return ServiceCheck(value)
        if isinstance(value, bool):
            return ServiceCheck(
                LegacyServiceState.RUNNING if value else LegacyServiceState.STOPPED
            )
        try:
            return ServiceCheck(LegacyServiceState(str(value).lower()))
        except Exception:
            return ServiceCheck(
                LegacyServiceState.UNKNOWN,
                str(value or "Invalid service status result"),
            )

    def _query_service(self) -> ServiceCheck:
        try:
            return self._coerce_service_check(self._service_query())
        except Exception as exc:
            return ServiceCheck(
                LegacyServiceState.UNKNOWN,
                f"Could not check the old auto-profile service: {exc}",
            )

    def _apply_worker(self, request: ApplyRequest) -> ApplyWorkerResult:
        service = self._query_service()
        if service.state is not LegacyServiceState.STOPPED:
            raise LegacyServiceBlocked(service)
        identity = self.hid.apply_mappings(request.mappings)
        return ApplyWorkerResult(
            service=service,
            device_identity=str(identity or self._device_identity),
        )

    def _reset_backoff(self):
        changed = self._auto_failure_count or self._next_auto_retry_at
        self._auto_failure_count = 0
        self._next_auto_retry_at = 0.0
        if changed:
            self.retryStateChanged.emit()

    def _record_apply_failure(self):
        self._auto_failure_count += 1
        if self._auto_failure_count >= 5:
            delay = 60.0
        else:
            delay = min(30.0, float(2 ** (self._auto_failure_count - 1)))
        self._next_auto_retry_at = time.monotonic() + delay
        self.retryStateChanged.emit()

    def _request_apply(self, profile_id: str, *, automatic: bool) -> bool:
        profile = self.store.get(profile_id)
        if not profile:
            return False
        if automatic and time.monotonic() < self._next_auto_retry_at:
            return False
        if self._apply_in_progress:
            self._queued_apply = (profile_id, automatic)
            return True
        if self._is_applied(profile_id):
            return True

        mappings = self._effective_mappings(profile)
        request = ApplyRequest(
            profile_id=profile_id,
            profile_revision=profile["revision"],
            mappings=mappings,
            mapping_hash=self._mapping_hash(mappings),
            automatic=automatic,
            catalog_generation=self._catalog_generation,
        )
        self._desired_profile_id = profile_id
        self._set_apply_error("")
        self._invalidate_applied_state("profile write started")
        self._set_apply_in_progress(True)
        submitted = self._submit(
            "apply-profile",
            lambda: self._apply_worker(request),
            lambda result, error: self._apply_completed(request, result, error),
        )
        if not submitted:
            self._set_apply_in_progress(False)
        return submitted

    @Slot(str, result=bool)
    def applyProfile(self, profile_id):
        return self._request_apply(profile_id, automatic=False)

    @Slot()
    def applyDefault(self):
        self._request_apply("default", automatic=False)

    def _service_block_message(self, state: LegacyServiceState) -> str:
        if state is LegacyServiceState.RUNNING:
            return self.tr("Stop the old NSSM GameSirAutoProfile service first")
        return self.tr(
            "The old auto-profile service status could not be verified; "
            "applying profiles is blocked"
        )

    def _apply_completed(
        self,
        request: ApplyRequest,
        result: ApplyWorkerResult | None,
        error: BaseException | None,
    ):
        if error is not None:
            if isinstance(error, LegacyServiceBlocked):
                self._set_legacy_service_state(error.check)
                message = self._service_block_message(error.check.state)
            else:
                message = str(error) or self.tr("Could not apply profile")
            LOGGER.error(
                "Profile apply failed for %s: %s",
                request.profile_id,
                error,
                exc_info=(type(error), error, error.__traceback__),
            )
            self._invalidate_applied_state("profile apply failed")
            self._record_apply_failure()
            self._set_apply_error(message, show_toast=True)
            self._set_apply_in_progress(False)
            self._run_queued_apply()
            return

        assert result is not None
        self._set_legacy_service_state(result.service)
        self._set_device_state(True, result.device_identity)
        current_profile = self.store.get(request.profile_id)
        request_is_current = bool(
            current_profile
            and self._mapping_hash(self._effective_mappings(current_profile))
            == request.mapping_hash
            and request.catalog_generation == self._catalog_generation
        )
        if not request_is_current:
            # The bytes may have reached the controller, but they no longer
            # represent persisted state. Never advertise that stale revision
            # as active; a mutation/delete normally queued the replacement.
            LOGGER.info(
                "Ignoring stale apply completion for profile %s revision %s",
                request.profile_id,
                request.profile_revision,
            )
            self._invalidate_applied_state("stale profile apply completed")
            if current_profile is None and self._queued_apply is None:
                self._queued_apply = ("default", False)
            self._set_apply_in_progress(False)
            self._run_queued_apply()
            return
        self._applied_state = AppliedState(
            profile_id=request.profile_id,
            profile_revision=current_profile["revision"],
            mapping_hash=request.mapping_hash,
            connection_generation=self._connection_generation,
            device_identity=self._device_identity,
        )
        self._last_successful_profile_id = request.profile_id
        self._reset_backoff()
        self._set_apply_error("")
        self._notify_hardware_state()
        profile = self.store.get(request.profile_id)
        profile_name = self._profile_display_name(profile) if profile else request.profile_id
        LOGGER.info("Applied profile: %s", profile_name)
        self.profileApplied.emit(profile_name)
        self._set_apply_in_progress(False)
        self._run_queued_apply()

    def _run_queued_apply(self):
        queued = self._queued_apply
        self._queued_apply = None
        if queued and not self._shutting_down:
            profile_id, automatic = queued
            if automatic and not self._auto_switch:
                return
            QTimer.singleShot(
                0,
                lambda: self._request_apply(profile_id, automatic=automatic),
            )

    @staticmethod
    def _normalize_executable_path(path: str) -> str:
        if not path:
            return ""
        return ntpath.normcase(ntpath.normpath(path.strip().strip('"')))

    def _scan_running_processes(
        self,
        profiles: list[dict[str, Any]],
    ) -> ProcessScanResult:
        process_rows: list[tuple[str, str]] = []
        for process in self._process_iter(["name", "exe"]):
            try:
                name = (process.info.get("name") or "").casefold()
                executable = process.info.get("exe") or ""
                process_rows.append(
                    (name, self._normalize_executable_path(executable))
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                continue

        matches: set[str] = set()
        for profile in profiles:
            if profile["id"] == "default" or not profile["exeName"]:
                continue
            expected_path = self._normalize_executable_path(profile["exePath"])
            expected_name = profile["exeName"].casefold()
            for running_name, running_path in process_rows:
                if expected_path:
                    # A configured path is authoritative. Never fall back to a
                    # same-named process in another directory.
                    matched = bool(running_path and running_path == expected_path)
                else:
                    matched = running_name == expected_name
                if matched:
                    matches.add(profile["id"])
                    break

        if not matches:
            return ProcessScanResult("default")
        if len(matches) == 1:
            return ProcessScanResult(next(iter(matches)))
        return ProcessScanResult("", tuple(sorted(matches)))

    def _profile_for_running_processes(self) -> str:
        """Synchronous compatibility helper used by diagnostics and tests."""
        return self._scan_running_processes(self.store.profiles).wanted_profile_id

    @Slot()
    def _poll_processes(self):
        if (
            self._shutting_down
            or not self._auto_switch
            or self._process_poll_inflight
        ):
            return
        profiles = self.store.profiles
        generation = self._process_scan_generation
        self._process_poll_inflight = True
        self._submit(
            "scan-processes",
            lambda: self._scan_running_processes(profiles),
            lambda result, error: self._process_scan_completed(
                generation,
                result,
                error,
            ),
        )

    def _process_scan_completed(
        self,
        generation: int,
        result: ProcessScanResult | None,
        error: BaseException | None,
    ):
        self._process_poll_inflight = False
        if (
            self._shutting_down
            or not self._auto_switch
            or generation != self._process_scan_generation
        ):
            return
        if error is not None or result is None:
            LOGGER.warning("Process scan failed: %s", error)
            return
        if result.conflicting_profile_ids:
            names = []
            for profile_id in result.conflicting_profile_ids:
                profile = self.store.get(profile_id)
                names.append(profile["name"] if profile else profile_id)
            message = self.tr("Multiple running games match profiles: %1").replace(
                "%1", ", ".join(names)
            )
            self._set_profile_conflict(message)
            return
        self._set_profile_conflict("")
        if self._device_connected and not self._is_applied(result.wanted_profile_id):
            self._request_apply(result.wanted_profile_id, automatic=True)

    def _probe_device(self) -> DeviceProbe:
        if hasattr(self.hid, "probe"):
            result = self.hid.probe()
            if isinstance(result, DeviceProbe):
                return result
            if hasattr(result, "connected"):
                return DeviceProbe(
                    bool(result.connected),
                    str(getattr(result, "identity", "")),
                    str(getattr(result, "error", "")),
                )
        try:
            return DeviceProbe(bool(self.hid.available()))
        except Exception as exc:
            return DeviceProbe(False, error=str(exc))

    @Slot()
    def _poll_device(self):
        if self._shutting_down or self._device_poll_inflight:
            return
        self._device_poll_inflight = True
        self._submit("probe-device", self._probe_device, self._device_poll_completed)

    def _set_device_state(self, connected: bool, identity: str = "") -> bool:
        connected = bool(connected)
        identity = str(identity or "") if connected else ""
        was_connected = self._device_connected
        old_identity = self._device_identity
        new_connection = connected and (
            not was_connected or (identity and identity != old_identity)
        )
        changed = connected != was_connected

        if new_connection:
            self._connection_generation += 1
            self._reset_backoff()
            self._invalidate_applied_state("controller connected or changed")
        elif not connected and was_connected:
            self._invalidate_applied_state("controller disconnected")

        self._device_connected = connected
        self._device_identity = identity
        if changed or (connected and identity != old_identity):
            self.deviceConnectedChanged.emit()
            self.pendingChangesChanged.emit()
            self.hardwareStateValidChanged.emit()
            self.statusChanged.emit()
        return new_connection

    def _device_poll_completed(
        self,
        probe: DeviceProbe | None,
        error: BaseException | None,
    ):
        self._device_poll_inflight = False
        if error is not None:
            probe = DeviceProbe(False, error=str(error))
        assert probe is not None
        was_connected = self._device_connected
        new_connection = self._set_device_state(probe.connected, probe.identity)
        if probe.error:
            self._last_device_error = probe.error
            self._set_last_error(probe.error, show_toast=probe.error != self._last_error)
        elif self._last_device_error:
            previous_device_error = self._last_device_error
            self._last_device_error = ""
            if self._last_error == previous_device_error:
                self._set_last_error("")
        if probe.connected and (not was_connected or new_connection):
            self.toast.emit(self.tr("Super Nova connected"))
            LOGGER.info("Super Nova connected (generation %s)", self._connection_generation)
            if self._auto_switch:
                self._poll_processes()
            else:
                wanted = self._last_successful_profile_id or self._desired_profile_id
                if wanted:
                    self._request_apply(wanted, automatic=False)
        elif not probe.connected and was_connected:
            self.toast.emit(self.tr("Super Nova disconnected"))
            LOGGER.info("Super Nova disconnected")

    def _set_legacy_service_state(self, check: ServiceCheck):
        old_state = self._legacy_service_state
        detail_changed = check.detail != self._legacy_service_detail
        self._legacy_service_detail = check.detail
        if check.state is old_state:
            if check.state is LegacyServiceState.UNKNOWN and detail_changed:
                message = (
                    self.tr("Could not verify the old service status: %1").replace(
                        "%1", check.detail
                    )
                    if check.detail
                    else self._service_block_message(check.state)
                )
                self._set_service_error(message, show_toast=True)
            return
        old_running = old_state is LegacyServiceState.RUNNING
        self._legacy_service_state = check.state
        self.legacyServiceStateChanged.emit()
        if old_running != (check.state is LegacyServiceState.RUNNING):
            self.legacyServiceRunningChanged.emit()
        self._reset_backoff()
        self._invalidate_applied_state("legacy service state changed")
        if check.state is LegacyServiceState.RUNNING:
            self._set_service_error("")
            self.toast.emit(self.tr("Old GameSirAutoProfile service is running"))
        elif check.state is LegacyServiceState.UNKNOWN:
            message = (
                self.tr("Could not verify the old service status: %1").replace(
                    "%1", check.detail
                )
                if check.detail
                else self._service_block_message(check.state)
            )
            self._set_service_error(message, show_toast=True)
        elif check.state is LegacyServiceState.STOPPED and self._device_connected:
            self._set_service_error("")
            if self._auto_switch:
                self._poll_processes()
            else:
                wanted = self._last_successful_profile_id or self._desired_profile_id
                if wanted:
                    self._request_apply(wanted, automatic=False)
        elif check.state is LegacyServiceState.STOPPED:
            self._set_service_error("")

    @Slot()
    def _poll_legacy_service(self):
        if self._shutting_down or self._service_poll_inflight:
            return
        self._service_poll_inflight = True
        self._submit("query-legacy-service", self._query_service, self._service_poll_completed)

    def _service_poll_completed(
        self,
        check: ServiceCheck | None,
        error: BaseException | None,
    ):
        self._service_poll_inflight = False
        if error is not None:
            check = ServiceCheck(LegacyServiceState.UNKNOWN, str(error))
        assert check is not None
        self._set_legacy_service_state(check)

    def _initial_apply(self):
        """Compatibility entry point retained for older integrations."""
        self._poll_legacy_service()
        self._poll_device()

    @Slot(bool, result=bool)
    def setAutoSwitchEnabled(self, value):
        value = bool(value)
        if value == self._auto_switch:
            return True
        if not self._persist_setting(
            "autoSwitch",
            value,
            "_auto_switch",
            self.autoSwitchEnabledChanged,
        ):
            return False
        self._process_scan_generation += 1
        if not value:
            if self._queued_apply and self._queued_apply[1]:
                self._queued_apply = None
            self._set_profile_conflict("")
        self.statusChanged.emit()
        if value:
            self._poll_processes()
        return True

    @Slot()
    def toggleAutoSwitch(self):
        self.setAutoSwitchEnabled(not self._auto_switch)

    def _persist_setting(self, key: str, value: bool, attribute: str, signal) -> bool:
        old_value = bool(getattr(self, attribute))
        try:
            self.settings.setValue(key, bool(value))
            sync = getattr(self.settings, "sync", None)
            if callable(sync):
                sync()
            status_method = getattr(self.settings, "status", None)
            status = status_method() if callable(status_method) else 0
            if status not in (0, QSettings.Status.NoError):
                raise OSError(f"QSettings status {status}")
        except Exception as exc:
            try:
                self.settings.setValue(key, old_value)
            except Exception:
                pass
            setattr(self, attribute, old_value)
            signal.emit()
            message = self.tr("Could not save settings: %1").replace("%1", str(exc))
            self._set_last_error(message, show_toast=True)
            return False
        setattr(self, attribute, bool(value))
        signal.emit()
        return True

    @Slot(bool, result=bool)
    def setMinimizeToTray(self, value):
        value = bool(value)
        if value == self._minimize_to_tray:
            return True
        return self._persist_setting(
            "minimizeToTray",
            value,
            "_minimize_to_tray",
            self.minimizeToTrayChanged,
        )

    @Slot(bool, result=bool)
    def setRestoreDefaultOnExit(self, value):
        value = bool(value)
        if value == self._restore_default_on_exit:
            return True
        return self._persist_setting(
            "restoreDefaultOnExit",
            value,
            "_restore_default_on_exit",
            self.restoreDefaultOnExitChanged,
        )

    @Slot(bool, result=bool)
    def setStartupEnabled(self, value):
        try:
            self._startup_module.set_enabled(bool(value))
            self._startup_enabled = self._startup_module.is_enabled()
            self.startupEnabledChanged.emit()
            self.toast.emit(
                self.tr("Starts with Windows")
                if self._startup_enabled
                else self.tr("Windows startup disabled")
            )
            return True
        except Exception as exc:
            # The switch in QML changes optimistically. Always publish the
            # authoritative registry state again when the write fails so the
            # control cannot remain visually enabled by mistake.
            try:
                self._startup_enabled = self._startup_module.is_enabled()
            except Exception:
                self._startup_enabled = False
            self.startupEnabledChanged.emit()
            self._set_last_error(str(exc), show_toast=True)
            return False

    @Slot()
    def exportProfiles(self):
        filename, _ = QFileDialog.getSaveFileName(
            None,
            self.tr("Export profiles"),
            str(Path.home() / "NovaProfiles-profiles.json"),
            self.tr("JSON (*.json)"),
        )
        if not filename:
            return
        try:
            self.store.export_file(Path(filename))
            self.toast.emit(self.tr("Profiles exported"))
        except Exception as exc:
            message = self.tr("Export failed: %1").replace("%1", str(exc))
            self._set_last_error(message, show_toast=True)

    @Slot(str, result=bool)
    def prepareImportFile(self, filename):
        try:
            preview = self.store.preview_import(Path(filename))
        except Exception as exc:
            message = self.tr("Import preview failed: %1").replace("%1", str(exc))
            self._set_last_error(message, show_toast=True)
            return False
        self._import_preview_obj = preview
        self._last_backup_path = ""
        self.importPreviewChanged.emit()
        return True

    @Slot()
    def importProfiles(self):
        filename, _ = QFileDialog.getOpenFileName(
            None,
            self.tr("Import profiles"),
            str(Path.home()),
            self.tr("JSON (*.json)"),
        )
        if filename:
            self.prepareImportFile(filename)

    @Slot(result=bool)
    def confirmImportProfiles(self):
        preview = self._import_preview_obj
        if preview is None:
            return False
        try:
            backup = self.store.import_file(
                preview.source,
                expected_digest=preview.digest,
            )
        except Exception as exc:
            message = self.tr("Import failed: %1").replace("%1", str(exc))
            self._set_last_error(message, show_toast=True)
            return False

        self._last_backup_path = str(backup or "")
        self._import_preview_obj = None
        self._selected_profile_id = "default"
        self._desired_profile_id = "default"
        self._last_successful_profile_id = ""
        self._queued_apply = None
        self._catalog_generation += 1
        self._process_scan_generation += 1
        self._set_profile_conflict("")
        self._invalidate_applied_state("profiles imported")
        self.profilesChanged.emit()
        self.selectedProfileChanged.emit()
        self.importPreviewChanged.emit()
        self.toast.emit(self.tr("Profiles imported; previous profiles were backed up"))
        if self._device_connected and self._auto_switch:
            self._poll_processes()
        return True

    @Slot()
    def cancelImportProfiles(self):
        if self._import_preview_obj is None:
            return
        self._import_preview_obj = None
        self.importPreviewChanged.emit()

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
        try:
            devices = self.hid.diagnostic_devices()
        except Exception as exc:
            devices = [{"error": str(exc)}]
        return json.dumps(devices, ensure_ascii=False, indent=2)

    @Slot()
    def requestShowWindow(self):
        self.showWindowRequested.emit()

    @Slot()
    def quitApplication(self):
        self.quitRequested.emit()

    def shutdown(self, *, restore_default: bool = True):
        if self._shutting_down:
            return
        self._shutting_down = True
        self.process_timer.stop()
        self.device_timer.stop()
        self.service_timer.stop()
        self.work_timer.stop()

        if self._executor_owned:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                LOGGER.exception("Could not stop the background worker")

        if restore_default and self._restore_default_on_exit and self._device_connected:
            service = self._query_service()
            if service.state is LegacyServiceState.STOPPED:
                try:
                    self.hid.apply_default()
                    LOGGER.info("Default restored on exit")
                except Exception:
                    LOGGER.exception("Could not restore Default on exit")
            else:
                LOGGER.warning(
                    "Default was not restored because legacy service state is %s",
                    service.state.value,
                )

        # Release the rotating file handler explicitly. On Windows an open
        # handler keeps the log file locked, which also prevents clean portable
        # shutdowns, upgrades and isolated test-directory cleanup.
        for handler in list(LOGGER.handlers):
            if getattr(handler, "_nova_profiles_handler", False):
                LOGGER.removeHandler(handler)
                try:
                    handler.flush()
                    handler.close()
                except Exception:
                    pass
