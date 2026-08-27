
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "NovaProfiles"

def _startup_command_args() -> list[str]:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if not executable.is_file():
            raise RuntimeError(f"Application executable does not exist: {executable}")
        return [str(executable), "--background"]

    python = Path(sys.executable).resolve()
    if python.name.lower() == "python.exe":
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw

    main = (Path(__file__).resolve().parents[1] / "main.py").resolve()
    if not python.is_file():
        raise RuntimeError(f"Python executable does not exist: {python}")
    if not main.is_file():
        raise RuntimeError(f"Nova Profiles entry point does not exist: {main}")
    return [str(python), str(main), "--background"]


def _startup_command() -> str:
    return subprocess.list2cmdline(_startup_command_args())


def _commands_match(actual: str, expected: str) -> bool:
    # The value is authored by this module, so canonical whitespace and quotes
    # are part of the validation. Case is ignored for Windows paths.
    return actual.strip().casefold() == expected.strip().casefold()

def is_enabled() -> bool:
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, APP_RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            value, value_type = winreg.QueryValueEx(key, VALUE_NAME)
        if value_type not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            return False
        return isinstance(value, str) and _commands_match(value, _startup_command())
    except (OSError, RuntimeError):
        return False

def set_enabled(enabled: bool):
    if os.name != "nt":
        raise RuntimeError("Start with Windows is supported only on Windows.")
    import winreg
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_RUN_KEY) as key:
            command = _startup_command()
            winreg.SetValueEx(
                key, VALUE_NAME, 0, winreg.REG_SZ, command
            )
    else:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                APP_RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            # Disabling an entry that was never created is already success.
            pass
