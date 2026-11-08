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

## v0.5.2 兼容性保护声明

**用户始终可以自主升级、降级、卸载或修改小米运动健康。** 本模块不会阻止 PackageManager 安装、禁止卸载、自动降级恢复、向用户数据目录写入限制文件，或强制撤销其他 Zygisk 模块的权限。

模块保护的是 **已审计 3.59.2 的 Hook 兼容性**：

- 一次性启动校验版本、签名及 APK SHA-256，运行时不反复读取 APK，也不读取健康记录。
- 开机按 `upgrade_unsupported`、`downgrade_unsupported`、`apk_bytes_changed` 等状态报告变更，并对新进程停用我们的日历 Hook。
- 若由本模块暂存了系统 APK，检测到明确的版本漂移，则只将本模块标记为下次重启停用；既有 SCEME 不受影响。
- 对本模块原生库、DEX 和脚本执行安装清单 SHA-256 检测，文件变动或缺失时安全停用。**这不是可以抵抗 Root 修改者的加密防篡改系统**，因为 Root 同样可以更改校验逻辑和清单。
- 仅统计其他启用的 Zygisk 模块数量，报告共存风险。不能仅凭模块存在便认定其注入小米运动健康，更不能保证发现所有 Hook。
- 健康记录、蓝牙配对和账号数据库没有被本模块自动备份或扫描。用户删除或修改这些数据后，如无事先可信备份，模块无法恢复。

完整威胁模型及安全边界见 [Security Policy](docs/security-policy.md)。

## 两阶段启动策略（v0.5 实验性）

初次安装时的 `bridge.conf` 默认配置是：

```ini
native_probe=1
calendar_hook=0
fail_on_conflict=1
```

因此第一次启动只报告 Zygisk Next 是否进入 `com.mi.health` 或 `com.mi.health:device`，不会初始化 LSPlant/Dobby，也不会修改日历逻辑。只有明确运行无参数 Root Shell 脚本 `root-module/enable-calendar.sh`，且已安装 APK 与经审计的 **3.59.2 SHA-256** 完全一致、设备为 PJZ110 / Android 17 时，后续新进程才启用三个日历 Hook。启用脚本不自动杀死应用或修改任何权限。

出现异常时运行 `root-module/safe-mode.sh`，后续新进程恢复观察模式。已有应用进程必须退出后才会重新读取模块配置。两个脚本都不接触应用数据库、账号、蓝牙配对信息。

这仍只是 **降低首次真机测试风险的分阶段机制**，并不证明 ColorOS 17 的 ART 运行时已兼容，更不能替代真机端到端日历同步测试。

## 安装与恢复安全说明

- KernelSU 将 `customize.sh` **导入当前安装器 Shell**。所有可跳过的分支必须从函数中 `return`，不得 `exit` 整个安装器。CI 含模拟 source 测试。
- KernelSU 默认在执行 `customize.sh` **之前**完成权限与 SELinux 标记。因此当脚本创建新的 `system/app` 暂存文件时，必须重新执行属主、目录权限及 `system_file` 上下文设置；任何一步失败立即清理暂存文件。
- 优先保留 SCEME。仅对字节完全匹配的 3.59.2 单 APK 考虑系统化；未知版本、拆分包、缺少挂载条件或缺少上下文工具时拒绝修改。
- 若本模块暂存了 APK，开机后发现版本不再匹配，将写入本模块的 `disable` 标记，**下次重启**停用；不会擅自重启、卸载或清除应用。
- `root-module/safe-mode.sh` 是无需参数的 Root Shell 退出方案，只将 `calendar_hook` 置为 0；下次目标应用启动生效，不自动杀死应用进程，也不影响账号与手环数据。
- 原生启动线程使用 `pthread_create` 返回码检查；ART 符号解析的只读 ELF 映射及前缀结果在进程内复用，降低重复符号扫描开销。性能效果仍需实机基准测试。

KernelSU 安装器参考：https://github.com/tiann/KernelSU/blob/main/userspace/ksud/src/installer.sh ，模块规范：https://github.com/tiann/KernelSU/blob/main/website/docs/guide/module.md 。

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
