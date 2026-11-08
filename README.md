# MiFitness-Bridge

Experimental integration for **Xiaomi Mi Fitness** `com.mi.health` (versionCode **359002**) and **Xiaomi Smart Band 10 Pro** on OnePlus 13 / ColorOS 17 / Android 17.

**Public source • no LSPosed framework • original Xiaomi APK remains unmodified.**

## v0.5 development scope

- **Native entrypoint:** Zygisk Next supplies the standard Zygisk API, which loads our C++ `zygisk/arm64-v8a.so`. We target only `com.mi.health` and **`com.mi.health:device`**. The latter hosts device management, BLE and sync services according to the analyzed APK Manifest.
- **ART hooks:** standalone [LSPlant](https://github.com/LSPosed/LSPlant), Dobby and xDL compiled with our native library, **not** an LSPosed module or Xposed/libxposed API.
- **Calendar functionality:** a small in-memory DEX implements the three version-pinned checks `isSupportSyncPhoneSchedule`, `createSyncScheduleItem$lambda$59`, and `isCalendarSyncAndroidVersion`. Hooks call the original first and may only change a returned false after verifying calendar provider, calendar permission, **device calendar feature**, APK version and trusted Xiaomi signer.
- **Systemization:** avoid replacing an existing SCEME installation; when system-app flags are absent and a known unmodified installed version is found, a root-manager install script can stage it into systemless `system/app`. Never `priv-app`; **no** privileged permission grants.
- **Conflict handling:** if a known competing ART injection engine is visible in the target process maps, calendar hooks fail closed. We do not and cannot revoke third-party hooks' privileges in the same process. No global Build property spoofing, no `system_server` hooks, no persistent polling daemon.
- **Acquisition:** the Xiaomi store source probe and certificate pin remain available. Official GetApps pages returned HTTP 200 on the tested ColorOS phone **but did not expose `com.mi.health`**, so no verified direct official APK source has been established. APK auto-download and installation are **disabled**, rather than using an untrusted mirror.

## Build/test gates

1. Run [native C++ + Java calendar bridge CI](.github/workflows/native-build.yml) with pinned LSPlant/Dobby/xDL dependencies, compile callback DEX, verify exported Zygisk symbol and ZIP contents.
2. Verify native ART initialization, exact target process attach, runtime classloader and **three installed hooks** on OnePlus 13 / ColorOS 17 / Xiaomi Mi Fitness 3.59.2.
3. Check one test calendar event reaches Smart Band 10 Pro from the UI **and** after background sync in `:device`. Confirm a genuine band capability absence remains denied.
4. Test unhook/rollback, SCEME coexistence, update suppression when signing/version mismatch, root module disable and reboot recovery.
5. Measure calendar synchronization latency/CPU/BLE traffic before claiming any high-throughput advantage.

**Status:** Source implementation underway. CI compilation alone is not a verified functionality test. Do **not** install the ZIP until all source and safety checks pass and there is a proper device recovery plan.

## Repository

- [Architecture](docs/native-zn-architecture.md)
- [APK source analysis](docs/upstream_sources.md)
- [Offline APK DEX ABI checker](tools/verify_calendar_abi.py): rejects incompatible candidate signatures before any installer can use them
- [Android shell metadata probe](tools/MiFitness_GetApps_Probe_v0.4.0.sh)
- [Pinned dependencies](scripts/fetch-native-deps.sh)
- [Native C++](native/src/entry.cpp) and [Java callbacks](java/src/dev/axymorrsen/mifitness/CalendarHook.java)

## Intellectual property and privacy

Do not commit proprietary Xiaomi or OPlus APKs, extracted OEM JAR files, personal health records, private logs, tokens or identifiers. LSPlant is LGPL-3.0, Dobby uses its own upstream license, xDL is MIT, and the public Zygisk API header is 0BSD. Preserve upstream notices and review redistribution/relinking terms before publishing binaries.
