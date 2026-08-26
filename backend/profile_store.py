
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .keyboard_catalog import is_valid_destination

APP_SCHEMA_VERSION = 1

DEFAULT_PROFILES = [
    {
        "id": "default",
        "name": "Default",
        "exePath": "",
        "exeName": "",
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
        "mappings": {
            "RB": "gp:04",
            "L4": "key:04",
            "R4": "key:16",
        },
    },
]

class ProfileStore:
    def __init__(self):
        app_data = Path(
            QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        )
        app_data.mkdir(parents=True, exist_ok=True)
        self.data_dir = app_data
        self.path = app_data / "profiles.json"
        self._profiles = []
        self.load()

    @property
    def profiles(self):
        return self._profiles

    def _normalized_profile(self, profile: dict) -> dict:
        pid = str(profile.get("id") or uuid.uuid4())
        name = str(profile.get("name") or "New Profile").strip() or "New Profile"
        exe_path = str(profile.get("exePath") or "")
        exe_name = str(profile.get("exeName") or "")
        mappings_in = profile.get("mappings") or {}
        mappings = {}
        for source in ("RB", "L4", "R4"):
            value = mappings_in.get(source)
            if value and is_valid_destination(str(value)):
                mappings[source] = str(value)
        return {
            "id": pid,
            "name": name,
            "exePath": exe_path,
            "exeName": exe_name,
            "mappings": mappings,
        }

    def _ensure_default(self):
        found = None
        for p in self._profiles:
            if p["id"] == "default":
                found = p
                break

        if found is None:
            self._profiles.insert(0, self._normalized_profile(DEFAULT_PROFILES[0]))
        else:
            found["name"] = "Default"
            found["exePath"] = ""
            found["exeName"] = ""
            defaults = DEFAULT_PROFILES[0]["mappings"]
            for source, value in defaults.items():
                found["mappings"].setdefault(source, value)

        self._profiles.sort(key=lambda p: (p["id"] != "default", p["name"].lower()))

    def load(self):
        if not self.path.exists():
            self._profiles = [
                self._normalized_profile(p) for p in DEFAULT_PROFILES
            ]
            self._ensure_default()
            self.save()
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_profiles = payload.get("profiles", [])
            self._profiles = [
                self._normalized_profile(p)
                for p in raw_profiles
                if isinstance(p, dict)
            ]
            self._ensure_default()
        except Exception:
            backup = self.path.with_suffix(".broken.json")
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                pass
            self._profiles = [
                self._normalized_profile(p) for p in DEFAULT_PROFILES
            ]
            self._ensure_default()
            self.save()

    def save(self):
        payload = {
            "schemaVersion": APP_SCHEMA_VERSION,
            "profiles": self._profiles,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def get(self, profile_id: str):
        return next((p for p in self._profiles if p["id"] == profile_id), None)

    def create(self, name: str):
        profile = {
            "id": str(uuid.uuid4()),
            "name": name.strip() or "New Profile",
            "exePath": "",
            "exeName": "",
            "mappings": {},
        }
        profile = self._normalized_profile(profile)
        self._profiles.append(profile)
        self._ensure_default()
        self.save()
        return profile

    def duplicate(self, profile_id: str):
        original = self.get(profile_id)
        if not original:
            return None
        profile = {
            "id": str(uuid.uuid4()),
            "name": f"{original['name']} Copy",
            "exePath": original["exePath"],
            "exeName": original["exeName"],
            "mappings": dict(original["mappings"]),
        }
        profile = self._normalized_profile(profile)
        self._profiles.append(profile)
        self._ensure_default()
        self.save()
        return profile

    def delete(self, profile_id: str) -> bool:
        if profile_id == "default":
            return False
        before = len(self._profiles)
        self._profiles = [p for p in self._profiles if p["id"] != profile_id]
        changed = len(self._profiles) != before
        if changed:
            self._ensure_default()
            self.save()
        return changed

    def import_file(self, source: Path):
        payload = json.loads(source.read_text(encoding="utf-8"))
        raw_profiles = payload.get("profiles")
        if not isinstance(raw_profiles, list):
            raise ValueError("Invalid profiles file")
        imported = [
            self._normalized_profile(p)
            for p in raw_profiles
            if isinstance(p, dict)
        ]
        if not imported:
            raise ValueError("No profiles found")
        self._profiles = imported
        self._ensure_default()
        self.save()

    def export_file(self, destination: Path):
        payload = {
            "schemaVersion": APP_SCHEMA_VERSION,
            "profiles": self._profiles,
        }
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
