# Native Zygisk Next migration — v0.4.0 experimental

## Fundamental distinction (Android 17 / ColorOS 17)

- Zygisk Next's **standard Zygisk interface** loads `zygisk/arm64-v8a.so` into an ordinary Android Zygote-forked `com.mi.health` app. This is our app injection method. It uses C++ and JNI but **not** LSPosed.
- Zygisk Next's distinct **Native ZN API** (`zn_modules.txt`) targets init-forked dynamically-linked native ELF executables. Android `com.mi.health` is **not** such a target; declaring `name=com.mi.health ...` in `zn_modules.txt` does not achieve APK process injection. Native ZN may be used later only if we ship a separately audited native helper and have a reason to inject that helper. Do not inject into Bluetooth/system_server or unrelated OEM services.
- Systemless mount (`system/app`) is provided by KernelSU/other root manager's mount provider (and in KernelSU may require a compatible metamodule), not by ZN. Current SCEME systemization takes precedence.

Sources: https://github.com/5ec1cff/ZygiskNextModuleSample and https://github.com/topjohnwu/zygisk-module-sample (0BSD API header), https://github.com/Dr-TSNG/ZygiskNext.

## Implementation in this PR

- One `zygisk/arm64-v8a.so` native C++ library registered through public `zygisk.hpp` API.
- Exact process name match `com.mi.health`. All other apps are ignored and library unloaded promptly.
- Reads a single `native_probe=1` flag from module directory in pre-specialization. Logs *one harmless milestone line* for target app after specialization. No root shell from app process, no Java/ART hook yet, no private health data accessed.
- Uses `DLCLOSE_MODULE_LIBRARY` because diagnostic stage installs no hooks. Future hook phase must remove this option while any hook remains active.
- No `xposed_init`, no LSPosed APK, no LSPosed grant/scoping steps, no native ZN target manifest.
- Public original Zygisk API header from the 0BSD sample is kept intact with original attribution. Do **not** vend or modify the Zygisk Next proprietary implementation.
- Keeps APK downloader separate; failed discovery cannot lead to auto installation.

## Test acceptance criteria

1. Build through native CI with Android NDK and inspect output `zygisk/arm64-v8a.so`.
2. On stock-equivalent ColorOS 17 installed with active Zygisk Next, reboot.
3. Start `com.mi.health`; in root shell run `logcat -d -s MiFitnessBridge:I | tail -n 20` and expect the marker. No message does not prove ZN is broken: first inspect ZN module status and whether the target app launched.
4. Check `pm list packages -s` and `action.sh` to determine if SCEME already systemized it. Never add duplicate `system/app` overlays if SYSTEM flag is present.
5. Create one test calendar event only when actual calendar Hook code lands. This milestone **does not** unlock calendar or improve BLE throughput.
6. No blanket privilege grants, no app-data edits, no platform signature bypass; to recover, disable module and reboot.

## Throughput and lifecycle

A native injection loader removes LSPosed dependency but is **not in itself a faster BLE channel**. Follow-up bridge design: bounded asynchronous queues; avoid blocking main/UI/Binder callbacks; use one-off calls into Android CalendarProvider; isolate Root work; measure end-to-end scheduling latency, IPC/BLE throughput and device CPU before making performance claims.

## Known limitations

This is an experimental diagnostic payload, not a full Mi Fitness unlocker. Automatic APK installation is intentionally deferred because GetApps pages responded HTTP 200 but did not advertise the `com.mi.health` package on the user's device probe (2026-11-08). Native fast-path calendar/ART method patches require explicit versioned symbol verification and on-device tests.
