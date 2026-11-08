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
# Run the bundled code/DEX/scripts integrity check before any other module helper.
# A mismatched/missing module file means this module cannot safely claim trusted code.
if [ -r "$MODDIR/check-code.sh" ]; then
  integrity="$(sh "$MODDIR/check-code.sh" 2>/dev/null)"
  check_result=$?
else
  integrity="code_integrity=checker_missing"
  check_result=2
fi
printf '%s\n' "$integrity" >> "$OUT"
if [ "$check_result" -ne 0 ]; then
  # Stop arming new ART hooks, without touching Mi Fitness's own data.
  tmp="$MODDIR/.bridge.conf.integrity.$"
  if {
    printf 'native_probe=1\n'
    printf 'calendar_hook=0\n'
    printf 'fail_on_conflict=1\n'
  } > "$tmp"; then
    chmod 0644 "$tmp" &&
      mv -f "$tmp" "$MODDIR/bridge.conf" ||
      rm -f "$tmp"
  else
    rm -f "$tmp"
  fi
  if touch "$MODDIR/disable" 2>/dev/null; then
    echo "module_action=disabled_next_boot_due_to_code_integrity" >> "$OUT"
  else
    echo "module_action=manual_recovery_required" >> "$OUT"
  fi
  exit 0
fi

# Inventory other Zygisk modules without inspecting their contents or names.
if [ -r "$MODDIR/hook-audit.sh" ]; then
  sh "$MODDIR/hook-audit.sh" >> "$OUT" 2>/dev/null ||
    echo "injection_inventory=unavailable" >> "$OUT"
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
