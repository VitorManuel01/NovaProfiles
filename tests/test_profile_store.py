from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from backend.profile_store import (
    APP_SCHEMA_VERSION,
    ProfileRecoveryError,
    ProfileStore,
    ProfileValidationError,
    UnsupportedSchemaError,
)


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.store = ProfileStore(self.data_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_import(self, payload: dict, name: str = "import.json") -> Path:
        path = self.data_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_public_profiles_are_copies(self):
        profiles = self.store.profiles
        profiles[0]["name"] = "Mutated outside"
        self.assertEqual(self.store.get("default")["name"], "Default")

    def test_mutation_is_transactional_when_atomic_write_fails(self):
        before_memory = self.store.get("default")
        before_disk = self.store.path.read_bytes()
        self.store._atomic_write = Mock(side_effect=OSError("disk full"))

        with self.assertRaises(OSError):
            self.store.set_mapping("default", "RB", "key:04")

        self.assertEqual(self.store.get("default"), before_memory)
        self.assertEqual(self.store.path.read_bytes(), before_disk)

    def test_profile_revision_increments_only_on_real_change(self):
        original = self.store.get("default")
        unchanged = self.store.set_mapping("default", "RB", "gp:04")
        changed = self.store.set_mapping("default", "RB", "key:04")
        self.assertEqual(unchanged["revision"], original["revision"])
        self.assertEqual(changed["revision"], original["revision"] + 1)

    def test_duplicate_copies_mappings_without_copying_executable_match(self):
        source_id = "mass-effect-andromeda"
        self.store.set_executable(
            source_id,
            r"C:\Games\MassEffectAndromeda.exe",
            "MassEffectAndromeda.exe",
        )
        original = self.store.get(source_id)
        duplicate = self.store.duplicate(source_id)
        self.assertEqual(duplicate["mappings"], original["mappings"])
        self.assertEqual(duplicate["exePath"], "")
        self.assertEqual(duplicate["exeName"], "")

    def test_import_rejects_duplicate_ids_without_changing_state(self):
        before = self.store.profiles
        source = self._write_import(
            {
                "schemaVersion": APP_SCHEMA_VERSION,
                "profiles": [
                    {
                        "id": "same",
                        "name": "One",
                        "mappings": {},
                    },
                    {
                        "id": "same",
                        "name": "Two",
                        "mappings": {},
                    },
                ],
            }
        )
        with self.assertRaises(ProfileValidationError):
            self.store.import_file(source)
        self.assertEqual(self.store.profiles, before)

    def test_import_rejects_future_schema(self):
        source = self._write_import(
            {"schemaVersion": APP_SCHEMA_VERSION + 1, "profiles": []}
        )
        with self.assertRaisesRegex(ProfileValidationError, "Unsupported"):
            self.store.preview_import(source)

    def test_import_rejects_boolean_schema_version(self):
        source = self._write_import(
            {"schemaVersion": True, "profiles": []}
        )
        with self.assertRaisesRegex(UnsupportedSchemaError, "Unsupported"):
            self.store.preview_import(source)

    def test_import_preview_digest_protects_reviewed_file(self):
        source = self._write_import(
            {
                "schemaVersion": APP_SCHEMA_VERSION,
                "profiles": [
                    {"id": "new", "name": "New", "mappings": {}}
                ],
            }
        )
        preview = self.store.preview_import(source)
        source.write_text(
            json.dumps(
                {
                    "schemaVersion": APP_SCHEMA_VERSION,
                    "profiles": [
                        {"id": "changed", "name": "Changed", "mappings": {}}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ProfileValidationError, "changed after"):
            self.store.import_file(source, expected_digest=preview.digest)

    def test_confirmed_import_creates_backup_and_one_default(self):
        source = self._write_import(
            {
                "schemaVersion": APP_SCHEMA_VERSION,
                "profiles": [
                    {"id": "new", "name": "New", "mappings": {}}
                ],
            }
        )
        preview = self.store.preview_import(source)
        self.assertEqual(preview.removed_count, 3)
        self.assertEqual(
            set(preview.removed_names),
            {"Mass Effect Andromeda", "Fallout New Vegas", "Grand Chase"},
        )
        backup = self.store.import_file(source, expected_digest=preview.digest)

        self.assertIsNotNone(backup)
        self.assertTrue(backup.is_file())
        ids = [profile["id"] for profile in self.store.profiles]
        self.assertEqual(ids.count("default"), 1)
        self.assertIn("new", ids)

    def test_corrupt_primary_is_preserved_before_defaults_are_restored(self):
        self.store.path.write_text("not json", encoding="utf-8")
        recovered = ProfileStore(self.data_dir)
        self.assertIsNotNone(recovered.get("default"))
        broken = list(self.data_dir.glob("profiles.broken-*.json"))
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].read_text(encoding="utf-8"), "not json")
        self.assertEqual(recovered.recovery_backup_path, broken[0])
        self.assertTrue(recovered.recovery_error)

    def test_recovery_aborts_without_overwriting_when_backup_cannot_be_written(self):
        original = b"not json and must not be lost"
        self.store.path.write_bytes(original)
        atomic_write = ProfileStore._atomic_write

        def fail_only_broken_backup(destination, data):
            if ".broken-" in destination.name:
                raise OSError("backup volume is full")
            return atomic_write(destination, data)

        with (
            unittest.mock.patch.object(
                ProfileStore,
                "_atomic_write",
                new=staticmethod(fail_only_broken_backup),
            ),
            self.assertRaises(ProfileRecoveryError),
        ):
            ProfileStore(self.data_dir)

        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertEqual(list(self.data_dir.glob("profiles.broken-*.json")), [])

    def test_future_primary_schema_is_preserved_and_blocks_downgrade(self):
        payload = {
            "schemaVersion": APP_SCHEMA_VERSION + 1,
            "profiles": [{"id": "future", "name": "Future", "mappings": {}}],
        }
        original = json.dumps(payload).encode("utf-8")
        self.store.path.write_bytes(original)
        with self.assertRaises(UnsupportedSchemaError):
            ProfileStore(self.data_dir)
        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertEqual(list(self.data_dir.glob("profiles.broken-*.json")), [])


if __name__ == "__main__":
    unittest.main()
