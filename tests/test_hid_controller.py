from __future__ import annotations

import unittest

from backend.hid_controller import (
    AmbiguousDeviceError,
    DeviceWriteError,
    GameSirSuperNovaProtocol,
    HIDEnumerationError,
    SuperNovaError,
    SuperNovaHID,
)


PREFERRED = {
    "path": b"hid#vid_3537&pid_103e&mi_01#col04",
    "interface_number": 1,
    "usage_page": 0xFF00,
}


class FakeDevice:
    def __init__(self, write_result=32):
        self.write_result = write_result
        self.opened_path = None
        self.writes = []
        self.closed = False

    def open_path(self, path):
        self.opened_path = path

    def set_nonblocking(self, value):
        self.nonblocking = value

    def write(self, report):
        self.writes.append(bytes(report))
        return self.write_result

    def close(self):
        self.closed = True


class FakeHID:
    def __init__(self, devices=None, device=None, enumerate_error=None):
        self.devices = list(devices or [])
        self.created_device = device or FakeDevice()
        self.enumerate_error = enumerate_error

    def enumerate(self, vendor_id, product_id):
        if self.enumerate_error:
            raise self.enumerate_error
        self.enumerated = (vendor_id, product_id)
        return self.devices

    def device(self):
        return self.created_device


class HIDControllerTests(unittest.TestCase):
    def test_protocol_builds_expected_atomic_report_sequence(self):
        protocol = GameSirSuperNovaProtocol()
        reports = protocol.reports_for_mappings(
            {"RB": "key:04", "L4": "gp:04", "R4": "key:1F"}
        )
        self.assertEqual(len(reports), 6)
        self.assertTrue(all(len(report) == 32 for report in reports))
        self.assertEqual(reports[0][10], 0x04)
        self.assertEqual(reports[0][14:18], bytes((0x02, 0x02, 0x00, 0x04)))
        self.assertEqual(reports[-1][0:4], bytes((0x07, 0x03, 0x08, 0x03)))

    def test_apply_validates_every_full_write_and_closes_device(self):
        device = FakeDevice()
        api = FakeHID([PREFERRED], device)
        controller = SuperNovaHID(hid_api=api, sleep=lambda _: None)
        identity = controller.apply_default()
        self.assertTrue(identity.startswith("bytes:"))
        self.assertEqual(len(device.writes), 6)
        self.assertTrue(device.closed)

    def test_partial_write_is_failure(self):
        device = FakeDevice(write_result=1)
        controller = SuperNovaHID(
            hid_api=FakeHID([PREFERRED], device),
            sleep=lambda _: None,
        )
        with self.assertRaisesRegex(DeviceWriteError, "partially updated"):
            controller.apply_default()
        self.assertTrue(device.closed)

    def test_unrecognized_vendor_collection_is_never_selected(self):
        wrong_collection = {
            "path": b"hid#vid_3537&pid_103e&mi_03#col01",
            "interface_number": 3,
            "usage_page": 0xFF00,
        }
        api = FakeHID([wrong_collection])
        controller = SuperNovaHID(hid_api=api)
        self.assertIsNone(controller.find_path())
        self.assertFalse(controller.probe().connected)

    def test_ambiguous_preferred_collections_are_not_guessed(self):
        second = dict(PREFERRED, path=b"other#mi_01#col04")
        controller = SuperNovaHID(hid_api=FakeHID([PREFERRED, second]))
        with self.assertRaises(AmbiguousDeviceError):
            controller.find_path()
        self.assertFalse(controller.probe().connected)
        self.assertIn("Multiple", controller.probe().error)

    def test_duplicate_enumeration_row_for_same_path_is_safe(self):
        controller = SuperNovaHID(hid_api=FakeHID([PREFERRED, dict(PREFERRED)]))
        self.assertEqual(controller.find_path(), PREFERRED["path"])

    def test_enumeration_errors_are_wrapped(self):
        controller = SuperNovaHID(
            hid_api=FakeHID(enumerate_error=OSError("driver unavailable"))
        )
        with self.assertRaises(HIDEnumerationError) as raised:
            controller.enumerate_candidates()
        self.assertIsInstance(raised.exception.__cause__, OSError)

    def test_invalid_mapping_is_rejected_before_device_is_created(self):
        api = FakeHID([PREFERRED])
        created = []
        controller = SuperNovaHID(
            hid_api=api,
            device_factory=lambda: created.append(True),
        )
        with self.assertRaises(SuperNovaError):
            controller.apply_mappings({"RB": "invalid"})
        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main()
