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
# User remains free to update, downgrade, or uninstall Mi Fitness.
# Guard reports compatibility state, pauses only our hooks, and never writes to app data.
if [ -r "$MODDIR/guard.sh" ]; then
  sh "$MODDIR/guard.sh" >> "$OUT" 2>/dev/null ||
    echo "package_profile=guard_failed" >> "$OUT"
else
  echo "package_profile=guard_missing" >> "$OUT"
  # If this module cannot run its own guard, refuse active hooks on the next boot.
  touch "$MODDIR/disable" 2>/dev/null ||
    echo "module_action=manual_recovery_required" >> "$OUT"
fi
echo "hook_state=check_process_log" >> "$OUT"
echo "apk_auto_install=disabled" >> "$OUT"
