# MiFitness-Bridge

Xiaomi Mi Fitness compatibility research for ColorOS / OnePlus using systemless systemization and scoped LSPosed hooks.

> **Experimental / source only.** No APK is bundled or automatically granted privileged permissions. Upstream fetching is still being evaluated; this project does not claim a working official Mi Fitness download endpoint.

## Target

- OnePlus 13 (PJZ110), ColorOS 17 / Android 17
- Xiaomi Smart Band 10 Pro
- Xiaomi Mi Fitness **`com.mi.health`**, baseline 3.59.2
- KernelSU / SukiSU + LSPosed; honor existing SCEME systemization

## Architecture (planned)

1. **Acquisition:** discover candidate APKs from Xiaomi sources; reject mismatched package names and store identities.
2. **Verification:** check package ID, valid APK signature, signing lineage, version code, ABI, and hook compatibility before any installation.
3. **Systemization:** prefer current SCEME/system status; otherwise stage a systemless `/system/app` copy, **not** `priv-app`.
4. **Hooks:** scope only `com.mi.health`; preserve genuine band capability checks; avoid global Xiaomi device spoofing.
5. **Isolation:** keep privileged operations in an independent root-side component. Detection of other injected modules cannot revoke individual hooks' privileges inside a shared process.

## Important source distinction

The Xiaomi App Store's public listing for the historic `com.xiaomi.wearable` build is **not** the same as China's `com.mi.health`. Historic `https://app.mi.com/download/<appId>` scrapers are useful references but **not confirmed working** for `com.mi.health` in 2026.

## Development

Work begins in [feature/bootstrap-apk-source](../../tree/feature/bootstrap-apk-source), with a dry-run Xiaomi-market source probe and offline tests. Previously prepared v0.3 local source is being audited before integration. Do not install an unverified artifact.

## Security/privacy

No proprietary Xiaomi APK, extracted ColorOS system packages, user health records, device identifiers, or account tokens are committed. Signature validation and full Android build/device tests remain release gates.
