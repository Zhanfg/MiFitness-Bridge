#!/usr/bin/env python3
"""Offline, read-only DEX ABI gate for Xiaomi Mi Fitness 3.59.2 calendar hooks.

This is NOT a package/signature verifier and does NOT approve a new APK version.
Pass the candidate through aapt/apksigner and review call semantics separately.
Only the expected owner + method + prototype + static/instance flag are checked.
No proprietary APK or DEX content is saved or uploaded by this tool.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

MAX_APK = 512 * 1024 * 1024
MAX_DEX = 64 * 1024 * 1024
MAX_TOTAL_DEX = 384 * 1024 * 1024
DEX_NAME = re.compile(r"classes(?:[2-9][0-9]*)?\.dex\Z")

W = "Lcom/xiaomi/fitness/device/manager/export/WearableDeviceModel;"
D = "Lcom/xiaomi/fitness/device/manager/DeviceModel;"
MANAGER = "Lcom/xiaomi/fitness/device/manager/export/WearableDeviceManager;"
EXPECTED = {
    f"Lcom/xiaomi/fitness/device/manager/extensions/DeviceModelExtKt;->isSupportSyncPhoneSchedule({W})Z": True,
    f"Lcom/xiaomi/fitness/devicesettings/di/FeatureItemModule;->createSyncScheduleItem$lambda$59({W})Z": True,
    "Lcom/xiaomi/fitness/devicesettings/di/DeviceSettingsSyncHelperImpl;->isCalendarSyncAndroidVersion()Z": False,
    f"Lcom/xiaomi/fitness/device/manager/DeviceModelExtKt;->isSupportFeature({D}Ljava/lang/String;)Z": True,
    f"Lcom/xiaomi/fitness/device/manager/export/DeviceManagerExtKt;->getInstance({MANAGER[:-1]}$Companion;){MANAGER}": True,
}


def checked(data, offset, length):
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError(f"DEX offset/length out of bounds: {offset}/{length}")
    return offset


def u2(data, offset):
    return struct.unpack_from("<H", data, checked(data, offset, 2))[0]


def u4(data, offset):
    return struct.unpack_from("<I", data, checked(data, offset, 4))[0]


def leb(data, pos):
    value = 0
    for shift in (0, 7, 14, 21, 28):
        checked(data, pos, 1)
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
    raise ValueError("Invalid DEX ULEB128")


def parse_dex(data):
    if len(data) < 0x70 or data[:4] != b"dex\n":
        raise ValueError("Invalid DEX magic")
    nstr, ostr = u4(data, 0x38), u4(data, 0x3C)
    ntyp, otyp = u4(data, 0x40), u4(data, 0x44)
    npro, opro = u4(data, 0x48), u4(data, 0x4C)
    nmet, omet = u4(data, 0x58), u4(data, 0x5C)
    ncls, ocls = u4(data, 0x60), u4(data, 0x64)
    for n, off, stride in (
        (nstr, ostr, 4), (ntyp, otyp, 4), (npro, opro, 12),
        (nmet, omet, 8), (ncls, ocls, 32)
    ):
        checked(data, off, n * stride)
    strings = []
    for i in range(nstr):
        off = u4(data, ostr + 4 * i)
        _, pos = leb(data, off)
        end = data.find(b"\x00", pos)
        if end < 0:
            raise ValueError("Unterminated DEX string")
        strings.append(data[pos:end].decode("utf-8", errors="replace"))
    types = [strings[u4(data, otyp + 4 * i)] for i in range(ntyp)]
    protos = []
    for i in range(npro):
        off = opro + i * 12
        ret = types[u4(data, off + 4)]
        params_off = u4(data, off + 8)
        params = []
        if params_off:
            n = u4(data, params_off)
            if n > 256:
                raise ValueError("Unexpectedly long prototype")
            checked(data, params_off + 4, n * 2)
            params = [types[u2(data, params_off + 4 + 2 * j)]
                      for j in range(n)]
        protos.append("(" + "".join(params) + ")" + ret)
    methods = []
    for i in range(nmet):
        off = omet + i * 8
        owner = types[u2(data, off)]
        proto = protos[u2(data, off + 2)]
        name = strings[u4(data, off + 4)]
        methods.append(owner + "->" + name + proto)

    defined = {}
    for i in range(ncls):
        off = ocls + i * 32
        owner = types[u4(data, off)]
        class_data = u4(data, off + 24)
        if not class_data:
            continue
        sizes = []
        pos = class_data
        for _ in range(4):
            value, pos = leb(data, pos)
            sizes.append(value)
        if any(value > 1000000 for value in sizes):
            raise ValueError("Unreasonably large class data list")
        for _ in range(sizes[0] + sizes[1]):
            _, pos = leb(data, pos)
            _, pos = leb(data, pos)
        for n in (sizes[2], sizes[3]):
            idx = 0
            for _ in range(n):
                delta, pos = leb(data, pos)
                flags, pos = leb(data, pos)
                _, pos = leb(data, pos)
                idx += delta
                if idx >= len(methods):
                    raise ValueError("Invalid class method index")
                signature = methods[idx]
                if not signature.startswith(owner + "->"):
                    raise ValueError("Method/class owner mismatch")
                if signature in EXPECTED:
                    if signature in defined:
                        raise ValueError("Duplicate DEX method definition")
                    defined[signature] = bool(flags & 0x8)
    return defined


def inspect(path):
    if not path.is_file() or path.stat().st_size > MAX_APK:
        raise ValueError("APK not found or exceeds 512 MiB")
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    found = {}
    with zipfile.ZipFile(path) as archive:
        entries = [entry for entry in archive.infolist()
                   if DEX_NAME.fullmatch(entry.filename)]
        if not entries or len(entries) > 32:
            raise ValueError("No valid DEX entries or more than 32 DEX files")
        if any(entry.file_size > MAX_DEX for entry in entries) or \
                sum(entry.file_size for entry in entries) > MAX_TOTAL_DEX:
            raise ValueError("DEX size limit exceeded")
        for entry in entries:
            one = parse_dex(archive.read(entry))
            for signature, value in one.items():
                if signature in found:
                    raise ValueError("Duplicate method across DEX files")
                found[signature] = value
    missing = [sig for sig in EXPECTED if sig not in found]
    wrong_kind = [sig for sig in EXPECTED
                  if sig in found and found[sig] != EXPECTED[sig]]
    return {
        "target_baseline": "com.mi.health/359002",
        "apk_sha256": digest.hexdigest(),
        "dex_count": len(entries),
        "abi_match": not missing and not wrong_kind,
        "found_methods": len(found),
        "required_methods": len(EXPECTED),
        "missing": missing,
        "wrong_static_instance": wrong_kind,
        "trusted_signer_verified": False,
        "semantic_compatibility_verified": False,
        "note": "ABI match alone never authorizes update or Hook activation on a new release",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path, help="Local candidate APK (never uploaded)")
    args = parser.parse_args()
    try:
        result = inspect(args.apk)
    except (ValueError, OSError, zipfile.BadZipFile, IndexError, struct.error) as err:
        print(json.dumps({"abi_match": False, "error": str(err)},
                         ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["abi_match"] else 1


if __name__ == "__main__":
    sys.exit(main())
