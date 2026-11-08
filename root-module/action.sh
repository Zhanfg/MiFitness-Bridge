#!/system/bin/sh
MODDIR="$(dirname "$0")"
echo "MiFitness Bridge v0.4 diagnostic / C++ native Zygisk Next"
printf 'ROM=%s SDK=%s\n' "$(getprop ro.build.version.oplusrom.display)" "$(getprop ro.build.version.sdk)"
printf 'Systemization: '; cat "$MODDIR/systemize-state.txt" 2>/dev/null || echo unknown
if pm list packages -s 2>/dev/null | grep -Fxq 'package:com.mi.health'; then
  echo 'Mi Fitness SYSTEM=yes, not necessarily PRIVILEGED'
else
  echo 'Mi Fitness SYSTEM=not confirmed'
fi
[ -s "$MODDIR/zygisk/arm64-v8a.so" ] && echo 'Native library present; use logcat to verify loading'
echo 'logcat -d -s MiFitnessBridge:I'
echo 'APK auto-install disabled pending verified official upstream.'
