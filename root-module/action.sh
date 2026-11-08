#!/system/bin/sh
# Read-only module manager action. Never prints accounts, tokens or health data.
MODDIR="$(dirname "$0")"
echo 'MiFitness Bridge v0.5.0-dev / Zygisk Next native status'
printf 'ROM=%s SDK=%s ABI=%s\n' \
  "$(getprop ro.build.version.oplusrom.display)" \
  "$(getprop ro.build.version.sdk)" \
  "$(getprop ro.product.cpu.abi)"
printf 'Systemization: '
cat "$MODDIR/systemize-state.txt" 2>/dev/null || echo 'unknown'
if [ -r "$MODDIR/boot-status.txt" ]; then
  echo 'Post-boot scan:'
  cat "$MODDIR/boot-status.txt"
fi
if pm list packages -s 2>/dev/null | grep -Fxq 'package:com.mi.health'; then
  echo 'Mi Fitness SYSTEM=yes (does not imply PRIVILEGED)'
else
  echo 'Mi Fitness SYSTEM=not confirmed'
fi
if [ -s "$MODDIR/zygisk/arm64-v8a.so" ]; then
  echo 'Zygisk native library=present; not proof of active injection'
else
  echo 'Zygisk native library=missing'
fi

# Module inventory is informational only; not proof ZN successfully injected.
provider=unknown
for root in /data/adb/modules /data/adb/ksu/modules; do
  [ -d "$root" ] || continue
  for dir in "$root"/*; do
    [ -r "$dir/module.prop" ] || continue
    [ -e "$dir/disable" ] && continue
    [ -e "$dir/remove" ] && continue
    if grep -Eiq '^(id|name)=.*zygisk.?next' "$dir/module.prop"; then
      provider=installed
      break
    fi
  done
  [ "$provider" = installed ] && break
done
echo "Zygisk Next module inventory=$provider"
echo 'APK auto-update=disabled until a trusted, compatible official source exists'

if command -v logcat >/dev/null 2>&1; then
  last="$(logcat -d -s MiFitnessBridge:I 2>/dev/null | tail -n 12)"
  if [ -n "$last" ]; then
    echo 'Recent MiFitnessBridge logcat (may be from an earlier app process):'
    printf '%s\n' "$last"
  else
    echo 'No retained MiFitnessBridge logs; start com.mi.health and recheck'
  fi
fi
