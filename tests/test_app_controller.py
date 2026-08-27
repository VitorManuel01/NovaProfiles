from __future__ import annotations

import json
import os
import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from backend.app_controller import (
    AppController,
    LegacyServiceState,
    ServiceCheck,
    _service_check_from_windows_state,
)
from backend.hid_controller import DeviceProbe, SuperNovaError
from backend.profile_store import APP_SCHEMA_VERSION, ProfileStore


QT_APP = QApplication.instance() or QApplication([])


class InlineExecutor:
    def submit(self, function):
        future = Future()
        try:
            future.set_result(function())
        except BaseException as exc:
            future.set_exception(exc)
        return future


class HoldingExecutor:
    def __init__(self):
        self.pending = []

    def submit(self, function):
        future = Future()
        self.pending.append((function, future))
        return future

    def run_next(self):
        function, future = self.pending.pop(0)
        try:
            future.set_result(function())
        except BaseException as exc:
            future.set_exception(exc)


class FakeSettings:
    def __init__(self):
        self.values = {
            "autoSwitch": True,
            "minimizeToTray": True,
            "restoreDefaultOnExit": False,
        }

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value):
        self.values[key] = value


class FakeStartup:
    enabled = False

    @classmethod
    def is_enabled(cls):
        return cls.enabled

    @classmethod
    def set_enabled(cls, value):
        cls.enabled = bool(value)


class FailingStartup:
    @staticmethod
    def is_enabled():
        return False

    @staticmethod
    def set_enabled(_value):
        raise OSError("registry write denied")


class FailingSettings(FakeSettings):
    def setValue(self, key, value):
        raise OSError("settings are read-only")


class FakeHID:
    def __init__(self):
        self.connected = True
        self.identity = "device-one"
        self.applied = []
        self.error = None

    def probe(self):
        return DeviceProbe(self.connected, self.identity if self.connected else "")

    def available(self):
        return self.connected

    def apply_mappings(self, mappings):
        if self.error:
            raise self.error
        self.applied.append(dict(mappings))
        return self.identity

    def apply_default(self):
        self.applied.append({"default": True})

    def diagnostic_devices(self):
        return []


class FakeProcess:
    def __init__(self, name, executable):
        self.info = {"name": name, "exe": executable}


class AppControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.temp_dir.name))
        self.hid = FakeHID()
        self.service_state = LegacyServiceState.STOPPED
        self.service_checks = 0
        self.processes = []

        def service_query():
            self.service_checks += 1
            return ServiceCheck(self.service_state)

        self.controller = AppController(
            hid=self.hid,
            store=self.store,
            settings=FakeSettings(),
            process_iter=lambda _attrs: list(self.processes),
            service_query=service_query,
            startup_module=FakeStartup,
            executor=InlineExecutor(),
            start_timers=False,
        )
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.STOPPED)
        )
        self.controller._set_device_state(True, self.hid.identity)

    def tearDown(self):
        self.controller.shutdown()
        self.temp_dir.cleanup()

    def _apply(self, profile_id="default"):
        self.assertTrue(self.controller.applyProfile(profile_id))
        self.controller._drain_jobs()

    def test_applied_state_tracks_revision_hash_and_connection_generation(self):
        self._apply()
        state = self.controller._applied_state
        self.assertEqual(self.controller.activeProfileId, "default")
        self.assertTrue(self.controller.hardwareStateValid)
        self.assertEqual(state.connection_generation, 1)
        self.assertEqual(state.profile_revision, self.store.get("default")["revision"])
        self.assertEqual(len(state.mapping_hash), 64)

    def test_mapping_edit_invalidates_active_hardware_state(self):
        self._apply()
        self.controller.setMapping("default", "RB", "key:04")
        self.assertEqual(self.controller.activeProfileId, "")
        self.assertFalse(self.controller.hardwareStateValid)
        self.assertTrue(self.controller.pendingChanges)

    def test_metadata_edit_does_not_invalidate_confirmed_hardware_mapping(self):
        profile_id = "mass-effect-andromeda"
        self._apply(profile_id)
        self.assertTrue(self.controller.renameProfile(profile_id, "MEA Custom"))
        profile = self.store.get(profile_id)
        self.store.set_executable(profile_id, r"C:\Games\MEA.exe", "MEA.exe")
        self.controller._after_profile_mutation(profile_id, profile["revision"])
        self.assertTrue(self.controller.hardwareStateValid)
        self.assertEqual(self.controller.activeProfileId, profile_id)

    def test_current_profile_is_queued_while_another_write_is_in_progress(self):
        self._apply("default")
        holding = HoldingExecutor()
        self.controller._executor = holding
        self.assertTrue(
            self.controller._request_apply("mass-effect-andromeda", automatic=False)
        )
        self.assertFalse(self.controller.hardwareStateValid)
        self.assertTrue(self.controller.applyInProgress)
        self.assertTrue(self.controller._request_apply("default", automatic=True))
        self.assertEqual(self.controller._queued_apply, ("default", True))

    def test_deleting_historical_profile_does_not_override_inflight_apply(self):
        historical_id = "mass-effect-andromeda"
        self._apply(historical_id)
        holding = HoldingExecutor()
        self.controller._executor = holding

        self.assertTrue(self.controller.applyProfile("default"))
        self.assertEqual(self.controller._desired_profile_id, "default")
        self.assertTrue(self.controller.deleteProfile(historical_id))
        self.assertIsNone(self.controller._queued_apply)

        holding.run_next()
        self.controller._drain_jobs()
        self.assertEqual(self.controller.activeProfileId, "default")
        self.assertTrue(self.controller.hardwareStateValid)

    def test_disconnect_and_reconnect_force_same_profile_to_be_reapplied(self):
        self._apply()
        original_generation = self.controller._connection_generation
        self.controller._set_device_state(False)
        self.assertEqual(self.controller.activeProfileId, "")
        self.controller._set_device_state(True, self.hid.identity)
        self.assertGreater(self.controller._connection_generation, original_generation)
        self._apply()
        self.assertEqual(len(self.hid.applied), 2)
        self.assertEqual(self.controller.activeProfileId, "default")

    def test_clean_disconnected_probe_clears_previous_enumeration_error(self):
        self.controller._device_poll_completed(
            DeviceProbe(False, error="enumeration failed"),
            None,
        )
        self.assertEqual(self.controller.lastError, "enumeration failed")
        self.controller._device_poll_completed(DeviceProbe(False), None)
        self.assertEqual(self.controller.lastError, "")
        self.assertEqual(self.controller._last_device_error, "")

    def test_service_is_checked_immediately_before_every_hid_apply(self):
        self._apply()
        self.controller._invalidate_applied_state("test")
        self._apply()
        self.assertEqual(self.service_checks, 2)
        self.assertEqual(len(self.hid.applied), 2)

    def test_unknown_service_state_fails_closed(self):
        self.service_state = LegacyServiceState.UNKNOWN
        self._apply()
        self.assertEqual(self.hid.applied, [])
        self.assertEqual(self.controller.legacyServiceState, "unknown")
        self.assertFalse(self.controller.hardwareStateValid)
        self.assertIn("could not be verified", self.controller.lastError)

    def test_windows_service_numeric_states_are_locale_independent(self):
        self.assertEqual(
            _service_check_from_windows_state(1).state,
            LegacyServiceState.STOPPED,
        )
        for state in (2, 3, 4, 5, 6, 7):
            self.assertEqual(
                _service_check_from_windows_state(state).state,
                LegacyServiceState.RUNNING,
            )
        self.assertEqual(
            _service_check_from_windows_state(999).state,
            LegacyServiceState.UNKNOWN,
        )

    def test_service_transition_invalidates_previous_application(self):
        self._apply()
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.RUNNING)
        )
        self.assertEqual(self.controller.activeProfileId, "")
        self.assertFalse(self.controller.hardwareStateValid)

    def test_repeated_failures_open_retry_circuit(self):
        self.hid.error = SuperNovaError("write failed")
        for _ in range(5):
            self.assertTrue(self.controller.applyProfile("default"))
            self.controller._drain_jobs()
        self.assertGreaterEqual(self.controller.retryDelaySeconds, 59)
        self.assertEqual(self.controller.lastError, "write failed")

    def test_configured_executable_path_never_falls_back_to_name(self):
        profile = self.store.get("mass-effect-andromeda")
        self.store.set_executable(
            profile["id"],
            r"C:\Games\MassEffectAndromeda.exe",
            "MassEffectAndromeda.exe",
        )
        self.processes = [
            FakeProcess(
                "MassEffectAndromeda.exe",
                r"D:\Other\MassEffectAndromeda.exe",
            )
        ]
        result = self.controller._scan_running_processes(self.store.profiles)
        self.assertEqual(result.wanted_profile_id, "default")

    def test_multiple_matching_profiles_are_reported_as_conflict(self):
        self.store.set_executable(
            "fallout-new-vegas",
            "",
            "MassEffectAndromeda.exe",
        )
        self.processes = [FakeProcess("MassEffectAndromeda.exe", "")]
        result = self.controller._scan_running_processes(self.store.profiles)
        self.assertEqual(result.wanted_profile_id, "")
        self.assertEqual(len(result.conflicting_profile_ids), 2)

    def test_completed_scan_is_ignored_after_auto_switch_is_disabled(self):
        self.processes = [
            FakeProcess("MassEffectAndromeda.exe", "")
        ]
        self.controller._poll_processes()
        self.controller.setAutoSwitchEnabled(False)
        self.controller._drain_jobs()
        self.assertEqual(self.hid.applied, [])
        self.assertFalse(self.controller.applyInProgress)

    def test_disabling_auto_switch_clears_stale_conflict(self):
        self.controller._set_profile_conflict("Two games match")
        self.assertTrue(self.controller.setAutoSwitchEnabled(False))
        self.assertEqual(self.controller.profileConflict, "")

    def test_completed_scan_is_ignored_after_profile_matching_changes(self):
        profile_id = "mass-effect-andromeda"
        profile = self.store.get(profile_id)
        self.processes = [FakeProcess("MassEffectAndromeda.exe", "")]
        self.controller._poll_processes()
        self.store.set_executable(profile_id, "", "")
        self.controller._after_profile_mutation(profile_id, profile["revision"])
        self.controller._drain_jobs()
        self.assertEqual(self.hid.applied, [])

    def test_initial_unknown_service_detail_is_not_lost(self):
        self.controller._legacy_service_state = LegacyServiceState.UNKNOWN
        self.controller._legacy_service_detail = ""
        self.controller._set_last_error("")
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.UNKNOWN, "access denied")
        )
        self.assertIn("access denied", self.controller.lastError)

    def test_resolved_service_error_is_cleared_after_successful_retry(self):
        self.assertTrue(self.controller.setAutoSwitchEnabled(False))
        self.service_state = LegacyServiceState.UNKNOWN
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.UNKNOWN, "access denied")
        )
        self._apply()
        self.assertIn("could not be verified", self.controller.lastError)
        self.assertEqual(self.hid.applied, [])

        self.service_state = LegacyServiceState.STOPPED
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.STOPPED)
        )
        self.controller._drain_jobs()
        self.assertEqual(len(self.hid.applied), 1)
        self.assertTrue(self.controller.hardwareStateValid)
        self.assertEqual(self.controller.lastError, "")

    def test_service_stop_retries_first_desired_profile_when_auto_switch_is_off(self):
        self.assertTrue(self.controller.setAutoSwitchEnabled(False))
        self.service_state = LegacyServiceState.RUNNING
        self._apply()
        self.assertEqual(self.hid.applied, [])
        self.assertEqual(self.controller._last_successful_profile_id, "")

        self.service_state = LegacyServiceState.STOPPED
        self.controller._set_legacy_service_state(
            ServiceCheck(LegacyServiceState.STOPPED)
        )
        self.controller._drain_jobs()
        self.assertEqual(len(self.hid.applied), 1)
        self.assertEqual(self.controller.activeProfileId, "default")

    def test_deleted_profile_is_not_reapplied_after_reconnect(self):
        profile_id = "mass-effect-andromeda"
        self._apply(profile_id)
        self.controller.setAutoSwitchEnabled(False)
        self.controller._set_device_state(False)
        self.controller.deleteProfile(profile_id)
        self.assertEqual(self.controller._desired_profile_id, "default")
        self.assertNotEqual(
            self.controller._last_successful_profile_id,
            profile_id,
        )

        self.controller._device_poll_completed(
            DeviceProbe(True, self.hid.identity),
            None,
        )
        self.controller._drain_jobs()
        self.assertEqual(self.controller.activeProfileId, "default")
        self.assertTrue(self.controller.hardwareStateValid)

    def test_startup_toggle_reverts_to_authoritative_state_on_failure(self):
        self.controller._startup_module = FailingStartup
        changes = []
        self.controller.startupEnabledChanged.connect(lambda: changes.append(True))
        self.controller.setStartupEnabled(True)
        self.assertFalse(self.controller.startupEnabled)
        self.assertEqual(changes, [True])
        self.assertIn("registry write denied", self.controller.lastError)

    def test_qsettings_failure_reverts_switch_and_reports_error(self):
        self.controller.settings = FailingSettings()
        changes = []
        self.controller.minimizeToTrayChanged.connect(lambda: changes.append(True))
        self.assertFalse(self.controller.setMinimizeToTray(False))
        self.assertTrue(self.controller.minimizeToTray)
        self.assertEqual(changes, [True])
        self.assertIn("settings are read-only", self.controller.lastError)

    def test_import_requires_preview_and_invalidates_hardware_state(self):
        self._apply()
        self.controller._last_successful_profile_id = "mass-effect-andromeda"
        self.controller._desired_profile_id = "mass-effect-andromeda"
        self.controller._queued_apply = ("mass-effect-andromeda", True)
        source = Path(self.temp_dir.name) / "incoming.json"
        source.write_text(
            json.dumps(
                {
                    "schemaVersion": APP_SCHEMA_VERSION,
                    "profiles": [
                        {"id": "imported", "name": "Imported", "mappings": {}}
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.assertTrue(self.controller.prepareImportFile(str(source)))
        self.assertEqual(self.controller.importPreview["profileCount"], 2)
        self.assertTrue(self.controller.confirmImportProfiles())
        self.assertFalse(self.controller.hardwareStateValid)
        self.assertEqual(self.controller._desired_profile_id, "default")
        self.assertEqual(self.controller._last_successful_profile_id, "")
        self.assertIsNone(self.controller._queued_apply)
        self.assertTrue(Path(self.controller.lastBackupPath).is_file())


if __name__ == "__main__":
    unittest.main()
