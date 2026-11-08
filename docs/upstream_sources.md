# Xiaomi APK acquisition study (2026-11-08)

Package required by MiFitness-Bridge: **com.mi.health**. Do not use **com.xiaomi.wearable** (separate international/legacy app).

## Investigated GitHub clients

| Project | Evidence | Result |
| --- | --- | --- |
| harismuneer/Android-Apps-Downloader | https://github.com/harismuneer/Android-Apps-Downloader | Historic `http://app.mi.com/download/<appId>` scheme. Referenced as protocol research, not copied. No evidence `com.mi.health` is listed today. |
| zichuan-liu/ShopDemo | https://github.com/zichuan-liu/ShopDemo | `/details?id=...`, `/download/{id}`. README says actual APK URL scraping is incomplete. **Not** production ready. |
| fantasywow/ApkCrawler | https://github.com/fantasywow/ApkCrawler | 2017 crawler; README warns URLs may break. GPL-3.0, not imported. |
| nuaays/ApkCrawler | https://github.com/nuaays/ApkCrawler | General market crawler, old approach; reference only. |
| EFForg/apkeep issue #187 | https://github.com/EFForg/apkeep/issues/187 | Xiaomi store support requested, not established; reports maintenance download UI for many apps. |

## Other maintained options (not direct GetApps downloads)

- [andersonlucasg3/hyperos-updater-android](https://github.com/andersonlucasg3/hyperos-updater-android): contemporary multi-source updater (including MemeOS, Tencent MyApp and mirrors). It does **not** establish an official GetApps endpoint for `com.mi.health`; useful as a model for pluggable sources and installation UX.
- [XiaomiFirmwareUpdater/miui-updates-tracker](https://github.com/XiaomiFirmwareUpdater/miui-updates-tracker) and [YuKongA/Updater-KMP](https://github.com/YuKongA/Updater-KMP): obtain official ROM information. APK extraction from ROM partitions may provide an authenticity-oriented fallback, but downloading entire ROMs on a phone at module install time is inappropriate.
- [BolunHan/miui.eu.localization](https://github.com/BolunHan/miui.eu.localization/blob/main/extract-linux.md): documents extraction of HyperOS system APKs from official fastboot ROMs.

## Observations

- Xiaomi's current website lists legacy `com.xiaomi.wearable` 2.16.4 with appID 926314 and a maintenance notice (https://app.mi.com/details?id=com.xiaomi.wearable).
- Current `com.mi.health` public Xiaomi store listing and supported direct URL have **not been verified**.
- Xiaomi's *developer app upload* API is for publishers pushing APKs to the store, not for anonymous customers downloading packages.
- Community ROM-extracted mirrors list newer `com.mi.health` releases (e.g. 3.59.9) but must not be treated as trusted automatable upstream merely because the site claims unchanged signatures.
- `hao1196561270/MiFitnessAdAway` (https://github.com/hao1196561270/MiFitnessAdAway) demonstrates modern libxposed API 102 techniques and reports Smart Band 10 Pro use. Evaluate as separate Hook reference under Apache-2.0, not an APK source.

## Safe acquisition policy

1. Fetch Xiaomi metadata over HTTPS and require the **exact** requested package name.
2. Reject maintenance pages, malformed IDs, cross-domain or HTTP redirects.
3. Accept ZIP/APK content *only* as a candidate. Use Android SDK `aapt` and `apksigner` to verify the actual APK package, version and trusted signing certificate before promoting the file.
4. The local sample of `com.mi.health` 3.59.2 has V1 signing certificate SHA-256 `c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025`. This is **not** a whole-file hash. Future signing-certificate rotation would require careful lineage verification before approval.
5. No automatic `pm install` in this initial probe. Updating beyond 3.59.2 also requires an explicit compatibility gate for the LSPosed hook locations; do not assume 3.59.9 is compatible.
6. Never upload downloaded Xiaomi APKs or extracted system software into the public repository/Actions artifacts.

## Commands

```sh
python3 -m unittest discover -s tests -v
python3 tools/xiaomi_market_probe.py
# Only on a host with Android SDK aapt + apksigner:
python3 tools/xiaomi_market_probe.py --download /tmp/com.mi.health.candidate.apk
```

Default operation retrieves metadata only and prints JSON. When a Xiaomi entry cannot be verified, it reports no candidate. An opt-in APK download is **staged**, checked and never installed automatically.

## Newly identified 2026 options (verified research references)

- [ZSXB2468 小米应用商店 APK 下载](https://greasyfork.org/zh-CN/scripts/593509-%E5%B0%8F%E7%B1%B3%E5%BA%94%E7%94%A8%E5%95%86%E5%BA%97-apk-%E4%B8%8B%E8%BD%BD) (MIT, Aug 29 2026) reconstructs the mobile GetApps download path using the page's **interactive captcha**. This may restore user-mediated downloads from official infrastructure, **not** trustworthy fully unattended installation. Do not bypass or solve verification challenges automatically. We have not verified it against `com.mi.health`.
- [MiaM1ku/Miband-OPlusBridge](https://github.com/MiaM1ku/Miband-OPlusBridge) documents ColorOS Device Space, OPPO Health and Xiaomi Smart Band **10 Pro** integration. It uses **libxposed API 102** and is therefore **not** directly reusable as our required Zygisk-Next-native runtime. Useful for understanding device/ColorOS interface boundaries. Independently audit license and avoid importing third-party keys, user data or device pairing credentials.
- [batareya16/MiWearBridge](https://github.com/batareya16/MiWearBridge) provides watch-interconnect research, but depends on Xposed and may target `com.xiaomi.wearable` instead of CN `com.mi.health`; never silently equate their APIs.

The APK source remains an open engineering gate: **an HTTP 200 Xiaomi Store web page without target package metadata does not authorize guessing an appId, downloading an unvetted archive or enabling unattended `pm install`.**

## Offline ABI gate for future APK releases

`tools/verify_calendar_abi.py` parses local DEX method definitions without using network access. It compares five exact Mi Fitness 3.59.2 signatures (three feature gates, `isSupportFeature(DeviceModel,String)` and the `WearableDeviceManager$Companion` factory). Run on the **developer's machine** with a candidate APK:

```sh
python3 tools/verify_calendar_abi.py /path/to/verified-com.mi.health.apk
```

This tool writes only a JSON summary to stdout. It never extracts a proprietary DEX to the repository or uploads the candidate. The script rejects malformed DEX files, missing methods and changes to the static/instance ABI. A passing ABI test **does not** prove the caller semantics, signature trust, installed package identity or actual functionality. `aapt` and `apksigner` remain mandatory before considering an APK update.

The experimental `xiaomi_market_probe.py --download` code now **requires**: exact package `com.mi.health`, trusted Xiaomi signing certificate, `versionCode=359002` and a matching DEX ABI. It refuses versions above 359002 until a separate method/behavior review is completed. Do not interpret this as a verified latest-version update channel.

## 2026-11-08 official GetApps API follow-up

- Xiaomi's developer FAQ explains `mimarket://details?id=<package>&startDownload=true` as **launching a preinstalled GetApps** on supported Xiaomi devices, not as a direct APK download API. Source: https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2296
- Xiaomi's updated store self-update guidance (2026-10-27) uses `market://details?id=pkgName` to **delegate installation to the store**. It does not expose a standalone APK URL suitable for our root module. Source: https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2006
- The maintained `andersonlucasg3/hyperos-updater-android` explicitly declined direct GetApps support after `app.market.xiaomi.com/apm/app` returned HTTP 400 requiring undocumented parameters/signatures. This independently supports keeping our direct auto-installer disabled. Source: https://github.com/andersonlucasg3/hyperos-updater-android
- The Xiaomi store developer automatic release API is **for publishers uploading APKs**, not a consumer download endpoint: https://dev.mi.com/distribute/doc/details?pId=1134

**Decision:** Do not disguise GetApps' user-mediated `market://` intent or publisher upload endpoints as unattended APK fetching. No third-party APK is mounted into `system/app` without checking package, signing lineage, trusted version and hook ABI/semantics.
