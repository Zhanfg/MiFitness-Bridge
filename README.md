# MiFitness-Bridge

Public research: Xiaomi Mi Fitness `com.mi.health` on OnePlus 13 (PJZ110) / ColorOS 17 / Xiaomi Smart Band 10 Pro.

**v0.4.0 is a diagnostic native prototype — NOT a finished unlocker.**

## Architecture

- No LSPosed, no Xposed API. A native `zygisk/arm64-v8a.so` is loaded through the **standard Zygisk API provided by Zygisk Next** in the `com.mi.health` Android app.
- Native ZN (`zn_modules.txt`) is for init-exec native processes, not Android app processes. No Native ZN system services are targeted.
- A root-manager systemless `system/app` overlay is staged only for known installed 3.59.2 builds when no existing SCEME/systemizer is detected. Does not use `priv-app` or grant any privileges.
- Single `native_probe=1` flag is read before app specialization; no ART hooks are installed yet.
- Official Xiaomi GetApps pages returned HTTP 200 on-device but none exposed the literal `com.mi.health`; verified unattended APK download/install remains disabled.

## Test

Use the `Build native Zygisk Next diagnostic` GitHub Actions artifact ZIP. Install through KernelSU/SukiSU manager; enable existing Zygisk Next provider, reboot and open Mi Fitness. Check `logcat -d -s MiFitnessBridge:I` for the target-only attach log. If missing, inspect ZN module inventory first. This milestone does not unlock calendar or alter BLE synchronization.

## Progress

Native entry and systemless staging: experimental, compile/device verification pending. Calendar, alarm, DND, injection conflicts and upstream auto-update: not yet implemented.

See [native design](docs/native-zn-architecture.md) and [APK source analysis](docs/upstream_sources.md).

## Licensing

Public Zygisk API header from topjohnwu/zygisk-module-sample is 0BSD. Zygisk Next proprietary loader binaries and OEM system packages are NOT distributed here.
