"""Synthetic DEX fixture tests. No Xiaomi proprietary APK is distributed."""
import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zipfile

from tools.verify_calendar_abi import parse_dex, inspect, EXPECTED

TARGET = "Lcom/xiaomi/fitness/devicesettings/di/DeviceSettingsSyncHelperImpl;->isCalendarSyncAndroidVersion()Z"
OWNER = "Lcom/xiaomi/fitness/devicesettings/di/DeviceSettingsSyncHelperImpl;"


def fake_dex(flags=1):
    # Minimal DEX metadata fixture. Not executable; sufficient for ABI parser.
    words = [OWNER, "Z", "isCalendarSyncAndroidVersion"]
    base = bytearray(0xB8)
    base[:8] = b"dex\n035\x00"
    struct.pack_into("<II", base, 0x38, 3, 0x70)  # strings
    struct.pack_into("<II", base, 0x40, 2, 0x7C)  # types
    struct.pack_into("<II", base, 0x48, 1, 0x84)  # prototypes
    struct.pack_into("<II", base, 0x58, 1, 0x90)  # methods
    struct.pack_into("<II", base, 0x60, 1, 0x98)  # class defs
    struct.pack_into("<II", base, 0x7C, 0, 1)
    struct.pack_into("<III", base, 0x84, 1, 1, 0)
    struct.pack_into("<HHI", base, 0x90, 0, 0, 2)
    positions = []
    for text in words:
        positions.append(len(base))
        raw = text.encode()
        assert len(raw) < 128
        base.extend(bytes([len(raw)]) + raw + b"\x00")
    for i, position in enumerate(positions):
        struct.pack_into("<I", base, 0x70 + i * 4, position)
    struct.pack_into("<I", base, 0x98 + 24, len(base))
    # class data: no fields, one virtual or direct method.
    if flags & 0x8:
        base.extend(bytes([0, 0, 1, 0, 0, flags, 0]))
    else:
        base.extend(bytes([0, 0, 0, 1, 0, flags, 0]))
    return bytes(base)


class OfflineAbiTest(unittest.TestCase):
    def test_prototype_and_instance_bit(self):
        self.assertEqual(parse_dex(fake_dex()), {TARGET: False})

    def test_changed_static_bit_is_detectable(self):
        self.assertEqual(parse_dex(fake_dex(flags=9)), {TARGET: True})
        self.assertIs(EXPECTED[TARGET], False)

    def test_invalid_dex_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_dex(b"not a dex")
        with self.assertRaises((ValueError, IndexError, struct.error)):
            parse_dex(fake_dex()[:-4])

    def test_apk_reports_partial_abi_instead_of_claiming_compatibility(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "fixture.apk"
            with zipfile.ZipFile(path, "w") as out:
                out.writestr("classes.dex", fake_dex())
            result = inspect(path)
            self.assertFalse(result["abi_match"])
            self.assertEqual(result["found_methods"], 1)
            self.assertEqual(result["required_methods"], 5)
            self.assertFalse(result["trusted_signer_verified"])
            self.assertFalse(result["semantic_compatibility_verified"])

    def test_missing_dex_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "fixture.apk"
            with zipfile.ZipFile(path, "w") as out:
                out.writestr("README.txt", "not an APK")
            with self.assertRaises(ValueError):
                inspect(path)


if __name__ == "__main__":
    unittest.main()
