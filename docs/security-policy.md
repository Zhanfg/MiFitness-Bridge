# Security and user-control policy

**Scope:** Xiaomi Mi Fitness `com.mi.health` on OnePlus 13 / ColorOS 17, with Zygisk Next. This is a compatibility module, **not** a device-management, anti-root, anti-user or DRM system.

## Protection declaration

MiFitness-Bridge protects **its own compatibility assumptions**, not the app's ability to be installed, uninstalled, updated or downgraded by its owner.

- **Reviewed baseline:** `com.mi.health` versionCode `359002` (3.59.2), APK SHA-256 `112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d`, signing certificate SHA-256 `c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025`. Neither SHA is a secret.
- **Manual upgrade:** allowed; incompatible newer version causes bridge calendar hooks to stop on subsequent process starts and the boot guard reports `upgrade_unsupported`. Nothing is auto-downgraded.
- **Manual downgrade:** allowed; unreviewed older version causes `downgrade_unsupported` and bridge hooks stop. Android itself may reject downgrade attempts or require a clean install; this module never deletes data to make a downgrade succeed.
- **Same version, different bytes:** treated as `apk_bytes_changed` even if the package/version appear identical. Failed checks never force-install an old binary.
- **Uninstall:** permitted. The guard reports `app_removed`, stops its own hooks and disables its own stale systemless overlay on a subsequent reboot, if one was staged.
- **Existing SCEME/systemization:** left alone. The module never disables or modifies a third-party systemizer.
- **Version drift during a running process:** the module checks its signed version/byte identity before installing hooks on process start, and at boot via `guard.sh`. It does not continuously inspect a running process and cannot undo other parties' in-memory modifications in real time.

There is **no claim of an OS-enforced prohibition on upgrading or downgrading**. Android's PackageInstaller update ownership can request user confirmation for updates under specific installer/permission conditions, but cannot retroactively grant this module update ownership over an app installed by another installer. In addition, Root can bypass such mechanisms. Sources: https://source.android.com/docs/setup/create/app-ownership and https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams#setRequestUpdateOwnership(boolean)

## Threat matrix

| Threat/event | What we do | What we cannot claim |
| --- | --- | --- |
| Accidental APK replacement / downgrade / update | Verify package, version, signer at Java initialization and a pinned SHA-256 of active APK. Boot guard records upgrade/downgrade/modified state and pauses our hooks. | Preventing the owner from installing or uninstalling apps |
| Corrupted native library, DEX, module scripts | Check shipped SHA-256 manifest once after boot and before `enable-calendar.sh`; disable our module on the next boot for failed integrity. | Defeating an attacker who has Root and can rewrite both payload and manifest, or who replaces our checks |
| LSPosed/other known injection engine coexistence | Map-based detection of a few known libraries; do not initialize our ART callbacks on detected conflicts. Strict `bridge.conf` parser rejects attempts to set `fail_on_conflict=0`. | Reliably detecting every Zygisk module, hook, hidden loader, instrumentation framework or root-owned process |
| Third-party Java/native hook changes same app | Avoid system-server injection; keep only app-scoped hooks and fail closed on known conflicts. | Per-hook privilege downgrade, blocking other root modules, restoring hostile in-memory patches |
| App-private health records altered or deleted by user/Root | The bridge never modifies, copies, exports or logs health databases. | Detecting all database edits or recovering deleted records without a prior valid backup |
| Module removed by owner | Standard Root manager uninstall/disable always remains available. | Anti-removal, stealth persistence or restricting owner control |

## Data safety and recovery

Health records, device pairing databases, account files and tokens are **not** indexed, hashed, backed up or synchronized by this module. Doing so without explicit user consent would be an inappropriate privacy risk. A future **opt-in** feature should use explicit destination, encryption, retention/rotation and restore verification. It must never commit or upload health data to this public repository or GitHub Actions.

Until such a feature is implemented, the module **cannot restore** deleted data. Avoid claiming a backup exists. Use a user-controlled data backup or sync workflow before experimenting with APK downgrades.

## Operational mode

- First installation: observe-only `native_probe=1`, `calendar_hook=0`.
- Explicit Root-only activation: `enable-calendar.sh` checks module integrity, Android/ROM, installed package SHA and version before setting `calendar_hook=1`.
- Emergency stop: `safe-mode.sh` returns to observe mode for newly started app processes without uninstalling the app.
- Boot check: `service.sh` calls `check-code.sh`, then `guard.sh`. Failures record minimal status codes without paths, personal data or logs containing health content.
- If **our own** systemless APK overlay was staged and becomes incompatible, the module marks **itself** disabled on next reboot, without automatically killing any app process or rebooting. Another systemizer is untouched.
- No continuous polling process is started. Since checks occur at boot and before new app Hook activation, do not call them real-time prevention or anti-tamper protection against Root.

## Security limits

The Root owner controls the device and can change binaries, injection modules, SELinux states, app files and data. SHA-256 manifests are useful for accidental corruption or unsophisticated modifications but are **not a hardware-backed authenticated trust root**. The only sensible high-confidence security boundary against competing Root code is to avoid placing secrets or health data in the bridge, and to keep the bridge narrowly scoped and fail closed.
