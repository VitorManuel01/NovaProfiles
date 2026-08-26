
from __future__ import annotations

import time
import hid

VID = 0x3537
PID = 0x103E

SOURCE_CODES = {
    "RB": 0x04,
    "L4": 0x24,
    "R4": 0x25,
}

DEFAULT_DESTINATIONS = {
    "RB": "gp:04",
    "L4": "gp:24",
    "R4": "gp:25",
}

class SuperNovaError(RuntimeError):
    pass

def _path_text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").lower()
    return str(value or "").lower()

class SuperNovaHID:
    def enumerate_candidates(self):
        return list(hid.enumerate(VID, PID))

    def find_path(self):
        devices = self.enumerate_candidates()

        # Exact interface/collection observed on the Super Nova setup.
        for dev in devices:
            p = _path_text(dev.get("path"))
            if "mi_01" in p and "col04" in p:
                return dev["path"]

        # Fallback to interface 1 + vendor-defined usage page.
        for dev in devices:
            iface = dev.get("interface_number")
            usage_page = dev.get("usage_page")
            if iface == 1 and isinstance(usage_page, int) and usage_page >= 0xFF00:
                return dev["path"]

        # Last safe fallback: vendor-defined collection on same VID/PID.
        for dev in devices:
            usage_page = dev.get("usage_page")
            if isinstance(usage_page, int) and usage_page >= 0xFF00:
                return dev["path"]

        return None

    def available(self) -> bool:
        return self.find_path() is not None

    def diagnostic_devices(self):
        result = []
        for dev in self.enumerate_candidates():
            result.append({
                "path": _path_text(dev.get("path")),
                "interface_number": dev.get("interface_number"),
                "usage_page": dev.get("usage_page"),
                "usage": dev.get("usage"),
                "product_string": dev.get("product_string") or "",
            })
        return result

    @staticmethod
    def _write(dev, report: bytearray):
        if len(report) != 32:
            raise ValueError("GameSir report must be exactly 32 bytes")
        written = dev.write(bytes(report))
        if written <= 0:
            raise SuperNovaError("hid.write() failed to send the report")
        time.sleep(0.035)

    def _map_gamepad(self, dev, source: int, destination: int):
        r = bytearray(32)
        r[0:4] = bytes((0x07, 0x13, 0x05, 0x01))
        r[10] = source
        r[13] = 0x01
        r[14] = 0x01
        r[15] = 0x01
        r[16] = destination
        self._write(dev, r)

    def _map_keyboard(self, dev, source: int, keycode: int):
        r = bytearray(32)
        r[0:4] = bytes((0x07, 0x13, 0x05, 0x01))
        r[10] = source
        r[13] = 0x01
        r[14] = 0x02
        r[15] = 0x02
        r[16] = 0x00
        r[17] = keycode
        self._write(dev, r)

    def _finalize_back_button(self, dev, source: int):
        r = bytearray(32)
        r[0:6] = bytes((0x07, 0x13, 0x01, 0x01, source, 0xFF))
        self._write(dev, r)

    def _sync(self, dev):
        r = bytearray(32)
        r[0:4] = bytes((0x07, 0x03, 0x08, 0x03))
        self._write(dev, r)

    @staticmethod
    def _parse_destination(destination_key: str):
        if ":" not in destination_key:
            raise SuperNovaError(f"Invalid destination: {destination_key}")
        kind, raw = destination_key.split(":", 1)
        try:
            code = int(raw, 16)
        except ValueError as exc:
            raise SuperNovaError(f"Invalid HID code: {destination_key}") from exc
        if kind not in ("gp", "key"):
            raise SuperNovaError(f"Unsupported destination type: {kind}")
        return kind, code

    def apply_mappings(self, mappings: dict[str, str]):
        path = self.find_path()
        if path is None:
            raise SuperNovaError(
                "Super Nova not found. Use the 2.4 GHz dongle in XInput mode."
            )

        dev = hid.device()
        try:
            dev.open_path(path)
            try:
                dev.set_nonblocking(1)
            except Exception:
                pass

            for source_name in ("RB", "L4", "R4"):
                source = SOURCE_CODES[source_name]
                destination_key = mappings.get(
                    source_name, DEFAULT_DESTINATIONS[source_name]
                )
                kind, code = self._parse_destination(destination_key)

                if kind == "gp":
                    self._map_gamepad(dev, source, code)
                else:
                    self._map_keyboard(dev, source, code)

                if source_name in ("L4", "R4"):
                    self._finalize_back_button(dev, source)

            self._sync(dev)
        except OSError as exc:
            raise SuperNovaError(
                "Could not open/write the Super Nova HID interface. "
                "Close GameSir Connect and any older auto-profile service."
            ) from exc
        finally:
            try:
                dev.close()
            except Exception:
                pass

    def apply_default(self):
        self.apply_mappings(DEFAULT_DESTINATIONS.copy())
