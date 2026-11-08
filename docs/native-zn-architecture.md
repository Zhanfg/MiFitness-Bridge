# Zygisk Next 原生架构

版本：v0.5.0-dev（实验性，尚未通过真机功能验证）

## 运行机制

- 由 **Zygisk Next** 提供标准 Zygisk API，将 `zygisk/arm64-v8a.so` 加载到 `com.mi.health` 和 `com.mi.health:device`。不使用 LSPosed 框架、Xposed API 或独立 LSPosed APK。
- Zygisk Next 的 `zn_modules.txt` 面向 init 创建的原生 ELF 服务，不能将 `com.mi.health` 当成该模式的注入目标。本项目没有注入 `system_server`、Bluetooth 进程和其他系统进程。
- 由 root 管理器提供 systemless 挂载，SCEME 已系统化时原样保留；只可能在已知单 APK SHA-256 匹配时暂存至 `system/app`，不进入 `priv-app`。
- 用户安装包 `com.mi.health` 的原有签名、数据目录、账号状态和蓝牙配对记录均不在模块内修改。

## 原生功能链

1. ZN 调用 `preAppSpecialize`，只允许上面的两个应用进程。读取 `bridge.conf` 和 `classes.dex`，缓存 `ActivityThread.currentApplication` JNI 方法引用。
2. `postAppSpecialize` 在目标进程内启动一次有上限的应用初始化等待；其他进程自动卸载模块库。
3. 通过 `InMemoryDexClassLoader` 加载项目自己的轻量 Java 回调，不修改小米 APK。
4. 内嵌的独立 ART 引擎使用 **LSPlant + Dobby + xDL** 实现特定 Java 方法 Hook。这里的 LSPlant 是 C++ 原生库，并不是 LSPosed 管理器/API。
5. `TargetResolver` 检查三处日历方法的精确签名、实例/静态性质和手环管理器正确重载。
6. `CalendarHook` 要求 Xiaomi 签名、版本 359002、Android 17、PJZ110、日历 Provider、读取权限及手环本身 `calendar` 能力全部满足。原始判断已经返回 true 时不更改；原本 false 时仅在这些条件下提升。
7. `BackupInvoker` 按 LSPlant 的实际 ABI 调用原方法：备份入口始终为静态方法，对实例方法将原接收对象放在参数数组首位。失败时保留原始异常。
8. 完成目标 Hook 后只对已定位的调用者尝试反内联，并记录成功数量。失败则保持原逻辑并记录具体阶段。

## 兼容性限制

| 项目 | 现状 |
|---|---|
| Android 17 / ColorOS 17 ABI | 静态编译通过，尚待运行时验证 |
| 小米运动健康 | 只支持已分析的 `3.59.2 / 359002` 和已知小米签名 |
| 手环 | 不伪造手环功能；只在设备真实声明 `calendar` 时提升手机端限制 |
| SCEME | 优先复用既有系统应用标志；不重复尝试挂载 |
| 其他 ART 注入器 | 检测到已知竞争库时停止本模块的敏感 Hook，不能撤销其他模块的权限 |
| APK 自动更新 | 未找到经实际验证的官方 `com.mi.health` 下载入口；自动安装关闭 |
| 勿扰、闹钟、录音 | 尚无跨 OEM 原生桥接实现 |
| 性能 | 无真机 BLE 吞吐、CPU 或同步延迟数据，不做性能增益承诺 |

## 测试状态

已通过 GitHub Actions：

- Java 备份调用的静态、实例和异常传播测试
- `TargetResolver` ABI、重载和缺类失败测试
- 日历策略全部 32 种布尔组合测试
- 模拟 SCEME 已系统化、应用缺失、版本变化、拆分包、路径缺失与系统化暂存路径等测试
- ARM64 NDK 编译、`zygisk_module_entry` 导出、DEX 编译、Shell 语法和模块 ZIP 结构检查

**尚未验证**：目标进程中 ART 初始化、实际三处方法命中、后台 `:device` 同步、ColorOS 日历数据读取和 Xiaomi Smart Band 10 Pro 收到日程。任何 CI 通过均不代表真机已完成这些项目。

## 运行时安全边界

模块不得执行全局 ROM 品牌欺骗、批量提升权限、修改系统签名、读取健康数据或使用第三方镜像静默安装未经证书验证的 APK。Root 管理器模块禁用后可撤回注入与 systemless 挂载；应用数据不由本模块删除。出现异常时，应先禁用该模块并重启，再查看经过脱敏的错误日志。

## 来源与许可

- Zygisk Next: https://github.com/Dr-TSNG/ZygiskNext
- 标准 Zygisk API 头文件（0BSD）: https://github.com/topjohnwu/zygisk-module-sample
- LSPlant（LGPL-3.0）: https://github.com/LSPosed/LSPlant
- Dobby: https://github.com/LSPosed/Dobby
- xDL（MIT）: https://github.com/hexhacking/xDL

所有第三方依赖的具体 Git 提交由 `scripts/fetch-native-deps.sh` 固定，构建产物附带许可文本。不要公开提交小米系统 APK、ColorOS 提取文件或敏感日志。
