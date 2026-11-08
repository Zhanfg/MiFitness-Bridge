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
