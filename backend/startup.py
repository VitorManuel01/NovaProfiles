
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "NovaProfiles"

def _startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'

    python = Path(sys.executable)
    if python.name.lower() == "python.exe":
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw

    main = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{python}" "{main}" --background'

def is_enabled() -> bool:
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, APP_RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False

def set_enabled(enabled: bool):
    if os.name != "nt":
        raise RuntimeError("Start with Windows is supported only on Windows.")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(
                key, VALUE_NAME, 0, winreg.REG_SZ, _startup_command()
            )
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
