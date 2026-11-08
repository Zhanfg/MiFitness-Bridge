# Mi Fitness 3.59.2 ART gate ABI verification

This summary was obtained from the user-supplied `com.mi.health` APK 3.59.2 (`versionCode=359002`), with a local read-only DEX parser. No proprietary APK or extracted DEX is committed.

Sample APK SHA-256:
`112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d`

Sample V1 signature certificate SHA-256:
`c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025`

## Exact method prototypes

| Owner and method | DEX return | DEX arguments | Access flags | Verified in |
| --- | --- | --- | --- | --- |
| `com.xiaomi.fitness.device.manager.extensions.DeviceModelExtKt.isSupportSyncPhoneSchedule` | boolean | `WearableDeviceModel` | `0x19` public static final | classes10.dex |
| `com.xiaomi.fitness.devicesettings.di.FeatureItemModule.createSyncScheduleItem$lambda$59` | boolean | `WearableDeviceModel` | `0x1a` private static final | classes11.dex |
| `com.xiaomi.fitness.devicesettings.di.DeviceSettingsSyncHelperImpl.isCalendarSyncAndroidVersion` | boolean | none | `0x1` public **instance** | classes11.dex |
| `com.xiaomi.fitness.device.manager.DeviceModelExtKt.isSupportFeature` | boolean | `DeviceModel`, `java.lang.String` | `0x19` public static final | classes10.dex |
| `com.xiaomi.fitness.device.manager.export.DeviceManagerExtKt.getInstance` | `WearableDeviceManager` | `WearableDeviceManager$Companion` | `0x19` public static final | classes10.dex |

**Two bugs corrected during source review:**

1. `isSupportFeature` takes the **base** `DeviceModel` interface. Reflection with `WearableDeviceModel` would throw `NoSuchMethodException`, preventing all three hooks.
2. `DeviceManagerExtKt.getInstance` is **overloaded** for `DeviceTool`, `WearableProductManager`, `BluetoothPermissionTool`, etc. Selecting the first one-argument method is incorrect. Resolve the overload with the exact `WearableDeviceManager$Companion` type.

## Rules

- Never patch `RomUtils.isXiaomi()` globally; only target the three isolated calendar restrictions.
- Preserve actual device `calendar` feature checks. A phone-side hook must not fabricate the band protocol capability.
- Enable only on the pinned signing cert, `versionCode=359002`, model PJZ110, SDK 37 and available Android CalendarProvider + READ_CALENDAR permission.
- Do not make a claim of functional ColorOS calendar sync until an actual device executes all three hooks and the Smart Band 10 Pro receives a test event.
- For future Mi Fitness builds, re-extract the method ABI and hashes; signature family alone does not guarantee hook compatibility.
