from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PySide6.QtCore import QStandardPaths

from .keyboard_catalog import is_valid_destination

APP_SCHEMA_VERSION = 1
PROFILE_SOURCES = ("RB", "L4", "R4")


class ProfileStoreError(RuntimeError):
    """Base error for profile persistence and validation failures."""


class ProfileValidationError(ProfileStoreError, ValueError):
    """Raised when a profile document is malformed or unsupported."""


class UnsupportedSchemaError(ProfileValidationError):
    """Raised when profiles were written by an incompatible app version."""


class ProfileRecoveryError(ProfileStoreError):
    """Raised when invalid profile data cannot first be preserved safely."""


@dataclass(frozen=True)
class ImportPreview:
    source: Path
    digest: str
    profiles: tuple[dict[str, Any], ...]
    profile_count: int
    new_count: int
    replaced_count: int
    removed_count: int
    names: tuple[str, ...]
    removed_names: tuple[str, ...]
    backup_will_be_created: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "fileName": self.source.name,
            "sourcePath": str(self.source),
            "digest": self.digest,
            "profileCount": self.profile_count,
            "newCount": self.new_count,
            "replacedCount": self.replaced_count,
            "removedCount": self.removed_count,
            "names": list(self.names),
            "removedNames": list(self.removed_names),
            "backupWillBeCreated": self.backup_will_be_created,
        }


DEFAULT_PROFILES = [
    {
        "id": "default",
        "name": "Default",
        "exePath": "",
        "exeName": "",
        "revision": 1,
        "mappings": {
            "RB": "gp:04",
            "L4": "gp:24",
            "R4": "gp:25",
        },
    },
    {
        "id": "mass-effect-andromeda",
        "name": "Mass Effect Andromeda",
        "exePath": "",
        "exeName": "MassEffectAndromeda.exe",
        "revision": 1,
        "mappings": {
            "RB": "key:2B",
            "L4": "gp:04",
            "R4": "key:1F",
        },
    },
    {
        "id": "fallout-new-vegas",
        "name": "Fallout New Vegas",
        "exePath": "",
        "exeName": "FalloutNV.exe",
        "revision": 1,
        "mappings": {
            "RB": "gp:04",
            "L4": "key:2F",
            "R4": "key:30",
        },
    },
    {
        "id": "grand-chase",
        "name": "Grand Chase",
        "exePath": "",
        "exeName": "grandchase.exe",
        "revision": 1,
        "mappings": {
            "RB": "gp:04",
            "L4": "key:04",
            "R4": "key:16",
        },
    },
]


class ProfileStore:
    """Validated, copy-on-write profile storage.

    Public reads return copies. Every mutation is written atomically before it
    becomes visible in memory, preventing the UI and profiles.json from
    diverging after a failed write.
    """

    def __init__(self, data_dir: Path | str | None = None):
        if data_dir is None:
            data_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "profiles.json"
        self._profiles: list[dict[str, Any]] = []
        self.recovery_backup_path: Path | None = None
        self.recovery_error = ""
        self.load()

    @property
    def profiles(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._profiles)

    @staticmethod
    def _default_profiles() -> list[dict[str, Any]]:
        return copy.deepcopy(DEFAULT_PROFILES)

    @staticmethod
    def _revision(value: Any) -> int:
        if value is None:
            return 1
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ProfileValidationError("Profile revision must be a positive integer")
        return value

    @classmethod
    def _normalized_profile(
        cls,
        profile: dict[str, Any],
        *,
        require_id: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(profile, dict):
            raise ProfileValidationError("Every profile must be a JSON object")

        raw_id = profile.get("id")
        if raw_id is None and not require_id:
            raw_id = str(uuid.uuid4())
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ProfileValidationError("Every profile must have a non-empty string id")
        profile_id = raw_id.strip()

        raw_name = profile.get("name", "New Profile")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ProfileValidationError(
                f"Profile '{profile_id}' must have a non-empty name"
            )
        name = raw_name.strip()

        exe_path = profile.get("exePath", "")
        exe_name = profile.get("exeName", "")
        if not isinstance(exe_path, str) or not isinstance(exe_name, str):
            raise ProfileValidationError(
                f"Profile '{profile_id}' has an invalid executable"
            )

        mappings_in = profile.get("mappings", {})
        if not isinstance(mappings_in, dict):
            raise ProfileValidationError(
                f"Profile '{profile_id}' mappings must be an object"
            )
        mappings: dict[str, str] = {}
        unknown_sources = set(mappings_in) - set(PROFILE_SOURCES)
        if unknown_sources:
            unknown = ", ".join(sorted(map(str, unknown_sources)))
            raise ProfileValidationError(
                f"Profile '{profile_id}' contains unknown controls: {unknown}"
            )
        for source, value in mappings_in.items():
            if not isinstance(value, str) or not is_valid_destination(value):
                raise ProfileValidationError(
                    f"Profile '{profile_id}' has an invalid {source} destination"
                )
            mappings[source] = value

        normalized = {
            "id": profile_id,
            "name": name,
            "exePath": exe_path.strip(),
            "exeName": exe_name.strip(),
            "revision": cls._revision(profile.get("revision")),
            "mappings": mappings,
        }
        if profile_id == "default":
            normalized["name"] = "Default"
            normalized["exePath"] = ""
            normalized["exeName"] = ""
            for source, value in DEFAULT_PROFILES[0]["mappings"].items():
                normalized["mappings"].setdefault(source, value)
        return normalized

    @classmethod
    def _validated_profiles(
        cls,
        raw_profiles: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        profiles = [cls._normalized_profile(p) for p in raw_profiles]
        if not profiles:
            raise ProfileValidationError("No profiles found")

        ids = [p["id"] for p in profiles]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for profile_id in ids:
            if profile_id in seen:
                duplicates.add(profile_id)
            seen.add(profile_id)
        if duplicates:
            raise ProfileValidationError(
                "Duplicate profile ids: " + ", ".join(sorted(duplicates))
            )

        if "default" not in ids:
            profiles.insert(0, cls._normalized_profile(DEFAULT_PROFILES[0]))

        profiles.sort(key=lambda p: (p["id"] != "default", p["name"].casefold()))
        return profiles

    @classmethod
    def _decode_document(cls, data: bytes) -> list[dict[str, Any]]:
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProfileValidationError("Invalid JSON profiles file") from exc
        if not isinstance(payload, dict):
            raise ProfileValidationError("Profiles file must contain a JSON object")

        schema_version = payload.get("schemaVersion", APP_SCHEMA_VERSION)
        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != APP_SCHEMA_VERSION
        ):
            raise UnsupportedSchemaError(
                f"Unsupported profiles schema version: {schema_version!r}"
            )
        raw_profiles = payload.get("profiles")
        if not isinstance(raw_profiles, list):
            raise ProfileValidationError("Profiles file is missing a profiles list")
        return cls._validated_profiles(raw_profiles)

    @staticmethod
    def _payload(profiles: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schemaVersion": APP_SCHEMA_VERSION,
            "profiles": profiles,
        }

    @classmethod
    def _serialized(cls, profiles: list[dict[str, Any]]) -> bytes:
        return (
            json.dumps(
                cls._payload(profiles),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _atomic_write(destination: Path, data: bytes):
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with tmp.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, destination)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _commit(self, candidate: list[dict[str, Any]]):
        validated = self._validated_profiles(candidate)
        self._atomic_write(self.path, self._serialized(validated))
        self._profiles = validated

    def _broken_backup_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return self.data_dir / f"profiles.broken-{stamp}.json"

    def load(self):
        if not self.path.exists():
            self._commit(self._default_profiles())
            return
        try:
            data = self.path.read_bytes()
        except OSError:
            # A file that could not be read must never be replaced as if it
            # merely contained invalid JSON.
            raise
        try:
            profiles = self._decode_document(data)
        except UnsupportedSchemaError:
            # A newer app may understand data this version does not. Preserve
            # the primary file byte-for-byte and require an explicit upgrade
            # instead of replacing it with defaults.
            raise
        except Exception as exc:
            backup_path = self._broken_backup_path()
            try:
                # Write the exact bytes already read through the same durable,
                # atomic path used for profiles. If preservation fails, abort
                # recovery and leave the primary byte-for-byte untouched.
                self._atomic_write(backup_path, data)
            except Exception as backup_exc:
                raise ProfileRecoveryError(
                    "Profiles are invalid and the original file could not be "
                    f"preserved at '{backup_path}': {backup_exc}"
                ) from backup_exc
            self.recovery_backup_path = backup_path
            self.recovery_error = str(exc)
            self._commit(self._default_profiles())
            return

        # Persist migrations such as the per-profile revision field.
        migrated = self._serialized(profiles)
        if migrated != data:
            self._atomic_write(self.path, migrated)
        self._profiles = profiles

    def save(self):
        """Compatibility method; prefer the transactional mutation methods."""
        self._commit(copy.deepcopy(self._profiles))

    def get(self, profile_id: str) -> dict[str, Any] | None:
        profile = next(
            (p for p in self._profiles if p["id"] == profile_id),
            None,
        )
        return copy.deepcopy(profile) if profile is not None else None

    def create(self, name: str) -> dict[str, Any]:
        profile = self._normalized_profile(
            {
                "id": str(uuid.uuid4()),
                "name": name.strip() or "New Profile",
                "exePath": "",
                "exeName": "",
                "revision": 1,
                "mappings": {},
            }
        )
        candidate = self.profiles
        candidate.append(profile)
        self._commit(candidate)
        return self.get(profile["id"])

    def duplicate(
        self,
        profile_id: str,
        copy_name: str | None = None,
    ) -> dict[str, Any] | None:
        original = self.get(profile_id)
        if not original:
            return None
        profile = self._normalized_profile(
            {
                "id": str(uuid.uuid4()),
                "name": copy_name or f"{original['name']} Copy",
                # A duplicate is a mapping template, not a second automatic
                # matcher for the same process. Linking is intentionally an
                # explicit follow-up action.
                "exePath": "",
                "exeName": "",
                "revision": 1,
                "mappings": original["mappings"],
            }
        )
        candidate = self.profiles
        candidate.append(profile)
        self._commit(candidate)
        return self.get(profile["id"])

    def delete(self, profile_id: str) -> bool:
        if profile_id == "default" or self.get(profile_id) is None:
            return False
        candidate = [p for p in self.profiles if p["id"] != profile_id]
        self._commit(candidate)
        return True

    def update(self, profile_id: str, **changes: Any) -> dict[str, Any] | None:
        allowed = {"name", "exePath", "exeName", "mappings"}
        unknown = set(changes) - allowed
        if unknown:
            raise ProfileValidationError(
                "Unsupported profile fields: " + ", ".join(sorted(unknown))
            )
        candidate = self.profiles
        index = next(
            (i for i, p in enumerate(candidate) if p["id"] == profile_id),
            None,
        )
        if index is None:
            return None
        if profile_id == "default" and any(
            key in changes for key in ("name", "exePath", "exeName")
        ):
            raise ProfileValidationError("The Default profile identity is fixed")
        updated = copy.deepcopy(candidate[index])
        changed = False
        for key, value in changes.items():
            if updated.get(key) != value:
                updated[key] = copy.deepcopy(value)
                changed = True
        if not changed:
            return self.get(profile_id)
        updated["revision"] = int(updated.get("revision", 1)) + 1
        candidate[index] = self._normalized_profile(updated)
        self._commit(candidate)
        return self.get(profile_id)

    def rename(self, profile_id: str, name: str) -> dict[str, Any] | None:
        clean_name = name.strip()
        if not clean_name:
            raise ProfileValidationError("Profile name cannot be empty")
        return self.update(profile_id, name=clean_name)

    def set_executable(
        self,
        profile_id: str,
        exe_path: str,
        exe_name: str,
    ) -> dict[str, Any] | None:
        return self.update(
            profile_id,
            exePath=exe_path,
            exeName=exe_name,
        )

    def set_mapping(
        self,
        profile_id: str,
        source: str,
        destination: str,
    ) -> dict[str, Any] | None:
        if source not in PROFILE_SOURCES:
            raise ProfileValidationError(f"Unsupported source control: {source}")
        if not is_valid_destination(destination):
            raise ProfileValidationError(f"Unsupported destination: {destination}")
        profile = self.get(profile_id)
        if profile is None:
            return None
        mappings = profile["mappings"]
        mappings[source] = destination
        return self.update(profile_id, mappings=mappings)

    def preview_import(self, source: Path | str) -> ImportPreview:
        source_path = Path(source)
        data = source_path.read_bytes()
        imported = self._decode_document(data)
        existing_ids = {p["id"] for p in self._profiles}
        imported_ids = {p["id"] for p in imported}
        removed_ids = existing_ids - imported_ids
        return ImportPreview(
            source=source_path,
            digest=hashlib.sha256(data).hexdigest(),
            profiles=tuple(copy.deepcopy(imported)),
            profile_count=len(imported),
            new_count=len(imported_ids - existing_ids),
            replaced_count=len(imported_ids & existing_ids),
            removed_count=len(removed_ids),
            names=tuple(p["name"] for p in imported),
            removed_names=tuple(
                p["name"] for p in self._profiles if p["id"] in removed_ids
            ),
            backup_will_be_created=self.path.exists(),
        )

    def _backup_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return self.data_dir / f"profiles.backup-{stamp}.json"

    def import_file(
        self,
        source: Path | str,
        *,
        expected_digest: str | None = None,
    ) -> Path | None:
        preview = self.preview_import(source)
        if expected_digest is not None and preview.digest != expected_digest:
            raise ProfileValidationError(
                "The import file changed after it was reviewed; preview it again"
            )

        backup: Path | None = None
        if self.path.exists():
            backup = self._backup_path()
            shutil.copy2(self.path, backup)
        self._commit([copy.deepcopy(p) for p in preview.profiles])
        return backup

    def export_file(self, destination: Path | str):
        destination_path = Path(destination)
        self._atomic_write(destination_path, self._serialized(self._profiles))
