
from __future__ import annotations

GAMEPAD_DESTINATIONS = [
    {"key": "gp:04", "label": "Gamepad · RB", "group": "Gamepad", "code": 0x04},
    {"key": "gp:24", "label": "Gamepad · L4", "group": "Gamepad", "code": 0x24},
    {"key": "gp:25", "label": "Gamepad · R4", "group": "Gamepad", "code": 0x25},
]

def _key(code: int, label: str) -> dict:
    return {
        "key": f"key:{code:02X}",
        "label": f"Keyboard · {label}",
        "group": "Keyboard",
        "code": code,
    }

KEYBOARD_DESTINATIONS = []

# Letters A-Z (USB HID 0x04-0x1D)
for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=0x04):
    KEYBOARD_DESTINATIONS.append(_key(i, letter))

# Number row 1-0 (USB HID 0x1E-0x27)
for code, label in zip(range(0x1E, 0x28), ["1","2","3","4","5","6","7","8","9","0"]):
    KEYBOARD_DESTINATIONS.append(_key(code, label))

KEYBOARD_DESTINATIONS += [
    _key(0x28, "Enter"),
    _key(0x29, "Escape"),
    _key(0x2A, "Backspace"),
    _key(0x2B, "Tab"),
    _key(0x2C, "Space"),
    _key(0x2D, "- / _"),
    _key(0x2E, "= / +"),
    _key(0x2F, "[  (HID 2F)"),
    _key(0x30, "]  (HID 30)"),
    _key(0x31, "\\\\"),
    _key(0x33, "; / :"),
    _key(0x34, "' / quote"),
    _key(0x35, "` / grave"),
    _key(0x36, ", / <"),
    _key(0x37, ". / >"),
    _key(0x38, "/ / ?"),
    _key(0x39, "Caps Lock"),
]

for code, label in zip(range(0x3A, 0x46), [f"F{i}" for i in range(1, 13)]):
    KEYBOARD_DESTINATIONS.append(_key(code, label))

KEYBOARD_DESTINATIONS += [
    _key(0x46, "Print Screen"),
    _key(0x47, "Scroll Lock"),
    _key(0x48, "Pause"),
    _key(0x49, "Insert"),
    _key(0x4A, "Home"),
    _key(0x4B, "Page Up"),
    _key(0x4C, "Delete"),
    _key(0x4D, "End"),
    _key(0x4E, "Page Down"),
    _key(0x4F, "Right Arrow"),
    _key(0x50, "Left Arrow"),
    _key(0x51, "Down Arrow"),
    _key(0x52, "Up Arrow"),
    _key(0x53, "Num Lock"),
    _key(0x54, "Numpad /"),
    _key(0x55, "Numpad *"),
    _key(0x56, "Numpad -"),
    _key(0x57, "Numpad +"),
    _key(0x58, "Numpad Enter"),
    _key(0x59, "Numpad 1"),
    _key(0x5A, "Numpad 2"),
    _key(0x5B, "Numpad 3"),
    _key(0x5C, "Numpad 4"),
    _key(0x5D, "Numpad 5"),
    _key(0x5E, "Numpad 6"),
    _key(0x5F, "Numpad 7"),
    _key(0x60, "Numpad 8"),
    _key(0x61, "Numpad 9"),
    _key(0x62, "Numpad 0"),
    _key(0x63, "Numpad ."),
    _key(0x65, "Application/Menu"),
    _key(0xE0, "Left Ctrl"),
    _key(0xE1, "Left Shift"),
    _key(0xE2, "Left Alt"),
    _key(0xE3, "Left Windows"),
    _key(0xE4, "Right Ctrl"),
    _key(0xE5, "Right Shift"),
    _key(0xE6, "Right Alt"),
    _key(0xE7, "Right Windows"),
]

DESTINATIONS = GAMEPAD_DESTINATIONS + KEYBOARD_DESTINATIONS
DESTINATION_BY_KEY = {item["key"]: item for item in DESTINATIONS}

def destination_label(key: str) -> str:
    item = DESTINATION_BY_KEY.get(key)
    if item:
        return item["label"].replace("Keyboard · ", "").replace("Gamepad · ", "")
    return key

def is_valid_destination(key: str) -> bool:
    return key in DESTINATION_BY_KEY
