from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

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


class HIDEnumerationError(SuperNovaError):
    pass


class AmbiguousDeviceError(SuperNovaError):
    pass


class DeviceWriteError(SuperNovaError):
    pass


@dataclass(frozen=True)
class ControllerCapabilities:
    sources: tuple[str, ...]
    destination_kinds: tuple[str, ...]
    report_size: int = 32


@dataclass(frozen=True)
class ControllerDescriptor:
    name: str
    vendor_id: int
    product_id: int
    interface_number: int | None
    usage_page_min: int
    preferred_path_tokens: tuple[str, ...]
    capabilities: ControllerCapabilities


@runtime_checkable
class ControllerProtocol(Protocol):
    """Small protocol boundary for future controller implementations."""

    descriptor: ControllerDescriptor
    default_destinations: Mapping[str, str]

    def reports_for_mappings(
        self,
        mappings: Mapping[str, str],
    ) -> list[bytes]: ...


def _path_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="backslashreplace").lower()
    return str(value or "").lower()


def _path_identity(value: Any) -> str:
    if isinstance(value, bytes):
        return "bytes:" + value.hex()
    return "text:" + str(value)


class GameSirSuperNovaProtocol:
    descriptor = ControllerDescriptor(
        name="GameSir Super Nova",
        vendor_id=VID,
        product_id=PID,
        interface_number=1,
        usage_page_min=0xFF00,
        preferred_path_tokens=("mi_01", "col04"),
        capabilities=ControllerCapabilities(
            sources=tuple(SOURCE_CODES),
            destination_kinds=("gp", "key"),
            report_size=32,
        ),
    )
    default_destinations = DEFAULT_DESTINATIONS

    @staticmethod
    def _parse_destination(destination_key: str) -> tuple[str, int]:
        if not isinstance(destination_key, str) or ":" not in destination_key:
            raise SuperNovaError(f"Invalid destination: {destination_key}")
        kind, raw = destination_key.split(":", 1)
        if kind not in ("gp", "key"):
            raise SuperNovaError(f"Unsupported destination type: {kind}")
        try:
            code = int(raw, 16)
        except (TypeError, ValueError) as exc:
            raise SuperNovaError(f"Invalid HID code: {destination_key}") from exc
        if not 0 <= code <= 0xFF:
            raise SuperNovaError(f"HID code is outside one byte: {destination_key}")
        return kind, code

    @staticmethod
    def _mapping_report(source: int, kind: str, destination: int) -> bytes:
        report = bytearray(32)
        report[0:4] = bytes((0x07, 0x13, 0x05, 0x01))
        report[10] = source
        report[13] = 0x01
        if kind == "gp":
            report[14] = 0x01
            report[15] = 0x01
            report[16] = destination
        else:
            report[14] = 0x02
            report[15] = 0x02
            report[16] = 0x00
            report[17] = destination
        return bytes(report)

    @staticmethod
    def _finalize_report(source: int) -> bytes:
        report = bytearray(32)
        report[0:6] = bytes((0x07, 0x13, 0x01, 0x01, source, 0xFF))
        return bytes(report)

    @staticmethod
    def _sync_report() -> bytes:
        report = bytearray(32)
        report[0:4] = bytes((0x07, 0x03, 0x08, 0x03))
        return bytes(report)

    def reports_for_mappings(
        self,
        mappings: Mapping[str, str],
    ) -> list[bytes]:
        if not isinstance(mappings, Mapping):
            raise SuperNovaError("Mappings must be a mapping object")
        reports: list[bytes] = []
        for source_name in self.descriptor.capabilities.sources:
            source = SOURCE_CODES[source_name]
            destination_key = mappings.get(
                source_name,
                self.default_destinations[source_name],
            )
            kind, code = self._parse_destination(destination_key)
            reports.append(self._mapping_report(source, kind, code))
            if source_name in ("L4", "R4"):
                reports.append(self._finalize_report(source))
        reports.append(self._sync_report())
        return reports


@dataclass(frozen=True)
class DeviceProbe:
    connected: bool
    identity: str = ""
    error: str = ""


class SuperNovaHID:
    """Thread-safe HID transport for an injectable controller protocol."""

    def __init__(
        self,
        *,
        protocol: ControllerProtocol | None = None,
        hid_api: Any = None,
        device_factory: Callable[[], Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        write_delay: float = 0.035,
    ):
        self.protocol = protocol or GameSirSuperNovaProtocol()
        self._hid = hid if hid_api is None else hid_api
        self._device_factory = device_factory or self._hid.device
        self._sleep = sleep
        self._write_delay = max(0.0, float(write_delay))
        self._lock = threading.RLock()

    @property
    def descriptor(self) -> ControllerDescriptor:
        return self.protocol.descriptor

    def enumerate_candidates(self) -> list[dict[str, Any]]:
        descriptor = self.descriptor
        try:
            devices = self._hid.enumerate(
                descriptor.vendor_id,
                descriptor.product_id,
            )
        except Exception as exc:
            raise HIDEnumerationError(
                f"Could not enumerate {descriptor.name} HID interfaces"
            ) from exc
        if devices is None:
            return []
        try:
            return [dict(device) for device in devices]
        except Exception as exc:
            raise HIDEnumerationError("HID enumeration returned invalid data") from exc

    @staticmethod
    def _unique_by_path(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[str, dict[str, Any]] = {}
        for device in devices:
            path = device.get("path")
            if path is not None:
                unique.setdefault(_path_identity(path), device)
        return list(unique.values())

    def _select_unique(
        self,
        candidates: list[dict[str, Any]],
        tier: str,
    ) -> Any | None:
        candidates = self._unique_by_path(candidates)
        if len(candidates) == 1:
            return candidates[0]["path"]
        if len(candidates) > 1:
            raise AmbiguousDeviceError(
                f"Multiple {self.descriptor.name} HID interfaces match {tier}; "
                "disconnect extra controllers and try again"
            )
        return None

    def find_path(self) -> Any | None:
        devices = self.enumerate_candidates()
        descriptor = self.descriptor

        preferred = [
            device
            for device in devices
            if all(
                token in _path_text(device.get("path"))
                for token in descriptor.preferred_path_tokens
            )
        ]
        path = self._select_unique(preferred, "the preferred collection")
        if path is not None:
            return path

        interface_vendor = [
            device
            for device in devices
            if device.get("interface_number") == descriptor.interface_number
            and isinstance(device.get("usage_page"), int)
            and device["usage_page"] >= descriptor.usage_page_min
        ]
        path = self._select_unique(interface_vendor, "interface and usage page")
        if path is not None:
            return path

        # Do not guess from VID/PID + a generic vendor-defined usage alone.
        # The same physical controller can expose unrelated vendor endpoints;
        # writing configuration reports to one of those is unsafe.
        return None

    def probe(self) -> DeviceProbe:
        try:
            path = self.find_path()
            if path is None:
                return DeviceProbe(connected=False)
            return DeviceProbe(
                connected=True,
                identity=_path_identity(path),
            )
        except SuperNovaError as exc:
            return DeviceProbe(connected=False, error=str(exc))

    def available(self) -> bool:
        return self.probe().connected

    def diagnostic_devices(self) -> list[dict[str, Any]]:
        result = []
        for device in self.enumerate_candidates():
            result.append(
                {
                    "path": _path_text(device.get("path")),
                    "interface_number": device.get("interface_number"),
                    "usage_page": device.get("usage_page"),
                    "usage": device.get("usage"),
                    "product_string": device.get("product_string") or "",
                }
            )
        return result

    def _write(self, device: Any, report: bytes):
        expected = self.descriptor.capabilities.report_size
        if len(report) != expected:
            raise ValueError(
                f"{self.descriptor.name} report must be exactly {expected} bytes"
            )
        try:
            written = device.write(report)
        except Exception as exc:
            raise DeviceWriteError("HID report write failed") from exc
        if written != expected:
            raise DeviceWriteError(
                f"Incomplete HID write: expected {expected} bytes, wrote {written!r}"
            )
        if self._write_delay:
            self._sleep(self._write_delay)

    def apply_mappings(self, mappings: Mapping[str, str]) -> str:
        # Validate the complete operation before opening the device, so an
        # invalid destination cannot leave a partially updated controller.
        reports = self.protocol.reports_for_mappings(mappings)
        with self._lock:
            path = self.find_path()
            if path is None:
                raise SuperNovaError(
                    f"{self.descriptor.name} not found. Use the 2.4 GHz dongle "
                    "in XInput mode."
                )

            try:
                device = self._device_factory()
            except Exception as exc:
                raise SuperNovaError("Could not create the HID device handle") from exc

            try:
                device.open_path(path)
                try:
                    device.set_nonblocking(1)
                except Exception:
                    pass
                for report in reports:
                    try:
                        self._write(device, report)
                    except DeviceWriteError as exc:
                        raise DeviceWriteError(
                            f"{exc}. Controller mappings may be partially updated; "
                            "reconnect it and reapply the intended profile or Default."
                        ) from exc
            except SuperNovaError:
                raise
            except Exception as exc:
                raise SuperNovaError(
                    f"Could not open/write the {self.descriptor.name} HID interface. "
                    "Close GameSir Connect and any older auto-profile service."
                ) from exc
            finally:
                try:
                    device.close()
                except Exception:
                    pass
            return _path_identity(path)

    def apply_default(self) -> str:
        return self.apply_mappings(dict(self.protocol.default_destinations))
