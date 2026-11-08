#!/system/bin/sh
# One-shot post-boot status reconciliation. No networking, APK installation or daemon.
MODDIR="$(dirname "$0")"
OUT="$MODDIR/boot-status.txt"
state="$(cat "$MODDIR/systemize-state.txt" 2>/dev/null)"
echo "mifitness_bridge_boot_check=started" > "$OUT"
attempt=0
while [ "$(getprop sys.boot_completed)" != "1" ] && [ "$attempt" -lt 30 ]; do
  attempt=$((attempt+1))
  sleep 2
done
if [ "$(getprop sys.boot_completed)" != "1" ]; then
  echo "package_scan=not_ready" >> "$OUT"
  exit 0
fi
all="$(pm list packages 2>/dev/null)"
if [ -z "$all" ]; then
  echo "package_scan=unavailable" >> "$OUT"
  exit 0
fi
if printf '%s\n' "$all" | grep -Fxq 'package:com.mi.health'; then
  echo "target_installed=yes" >> "$OUT"
else
  echo "target_installed=no" >> "$OUT"
fi
system="$(pm list packages -s 2>/dev/null)"
if printf '%s\n' "$system" | grep -Fxq 'package:com.mi.health'; then
  echo "system_app=yes" >> "$OUT"
else
  if [ "$state" = "staged-reboot-required" ]; then
    echo "system_app=not_confirmed_after_stage" >> "$OUT"
  else
    echo "system_app=not_confirmed" >> "$OUT"
  fi
fi
# An overlay must not silently pin a stale APK after the user upgrades Mi Fitness.
# If our own system/app copy was staged, a mismatch disables this module at NEXT boot.
# Never force-stop an application or reboot automatically in a boot service.
version_ok=no
if dumpsys package com.mi.health 2>/dev/null |
    grep -Eq 'versionCode=359002([^0-9]|$)'; then
  version_ok=yes
fi
if [ "$version_ok" = yes ]; then
  echo "app_version_profile=359002_verified" >> "$OUT"
else
  echo "app_version_profile=mismatch_or_unavailable" >> "$OUT"
  if [ "$state" = "staged-reboot-required" ]; then
    if touch "$MODDIR/disable" 2>/dev/null; then
      echo "module_action=disabled_on_next_boot_due_to_version_drift" >> "$OUT"
    else
      echo "module_action=disable_failed_manual_recovery_required" >> "$OUT"
    fi
  fi
fi
echo "hook_state=check_process_log" >> "$OUT"
echo "apk_auto_install=disabled" >> "$OUT"
