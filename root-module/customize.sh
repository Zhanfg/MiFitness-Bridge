#!/system/bin/sh
# Only stage a vetted installed app; never grant privileged permissions.
[ -n "$MODPATH" ] || exit 1
[ -s "$MODPATH/zygisk/arm64-v8a.so" ] || abort "Native .so missing; use CI-built ZIP"
[ "$(getprop ro.product.cpu.abi)" = arm64-v8a ] || abort "arm64-only test build"
ui_print "- Native Zygisk Next / no LSPosed companion"
system_packages="$(pm list packages -s 2>/dev/null)" || system_packages=""
all_packages="$(pm list packages 2>/dev/null)" || all_packages=""
if [ -z "$all_packages" ]; then
  echo pm-unavailable > "$MODPATH/systemize-state.txt"
  ui_print "- PackageManager unavailable; no systemization attempted"
  exit 0
fi
if printf '%s\n' "$system_packages" | grep -Fxq 'package:com.mi.health'; then
  echo existing-system > "$MODPATH/systemize-state.txt"
  ui_print "- Existing SYSTEM app detected, preserving SCEME"
  exit 0
fi
if ! printf '%s\n' "$all_packages" | grep -Fxq 'package:com.mi.health'; then
  echo app-absent > "$MODPATH/systemize-state.txt"
  ui_print "- App absent; native loader installed, no systemization"
  exit 0
fi
for d in /data/adb/modules/*; do
  [ -d "$d" ] || continue
  [ "$d" = "$MODPATH" ] && continue
  [ -e "$d/disable" ] && continue
  [ -e "$d/remove" ] && continue
  case "$(basename "$d" | tr 'A-Z' 'a-z')" in
    *sceme*|*systemiz*)
      echo existing-systemizer > "$MODPATH/systemize-state.txt"
      ui_print "- Existing systemizer detected; avoiding duplicate mount"
      exit 0 ;;
  esac
done
dumpsys package com.mi.health 2>/dev/null | grep -Eq 'versionCode=359002([^0-9]|$)' || {
  echo version-unverified > "$MODPATH/systemize-state.txt"
  ui_print "- App version not verified at 359002; no mount"
  exit 0
}
paths="$(pm path com.mi.health 2>/dev/null | sed -n 's/^package://p')"
if [ -z "$paths" ]; then
  echo path-unavailable > "$MODPATH/systemize-state.txt"
  ui_print "- pm path failed; no unsafe path guessing"
  exit 0
fi
dest="$MODPATH/system/app/MiFitnessBridge"
mkdir -p "$dest" || abort "Cannot stage APK directory"
count=0; base=0; error=0
while IFS= read -r file; do
  [ -n "$file" ] || continue
  case "$file" in /data/app/*.apk|/system/app/*.apk|/system_ext/app/*.apk|/product/app/*.apk) ;; *) error=1; break ;; esac
  [ -r "$file" ] || { error=1; break; }
  name="$(basename "$file")"
  case "$name" in *.apk) ;; *) error=1; break ;; esac
  case "$name" in ''|*[!A-Za-z0-9_.-]*) error=1; break ;; esac
  [ "$name" = "base.apk" ] && base=$((base+1))
  cp "$file" "$dest/$name" || { error=1; break; }
  chmod 0644 "$dest/$name"
  count=$((count+1))
done <<EOF_APKS
$paths
EOF_APKS
if [ "$error" -ne 0 ] || [ "$count" -eq 0 ]; then
  rm -rf "$MODPATH/system"
  echo stage-failed > "$MODPATH/systemize-state.txt"
  ui_print "- APK staging failed; disabled mount"
  exit 0
fi
if [ "$base" -eq 0 ] && [ "$count" -eq 1 ]; then
  for f in "$dest"/*.apk; do mv "$f" "$dest/base.apk" || abort "Cannot rename base.apk"; done
  base=1
fi
if [ "$base" -ne 1 ]; then
  rm -rf "$MODPATH/system"
  echo uncertain-splits > "$MODPATH/systemize-state.txt"
  ui_print "- Unknown APK split layout; disabled mount"
  exit 0
fi
echo staged-reboot-required > "$MODPATH/systemize-state.txt"
ui_print "- Staged $count APK(s) to system/app only. Requires reboot and mount provider."
