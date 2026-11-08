#!/system/bin/sh
# User-controlled compatibility guard for com.mi.health.
# Does NOT prevent updates, downgrades, uninstalls, or data edits.
# Detects known profile drift, disables bridge calendar hooks for NEXT process,
# and never reinstalls an old APK, kills the app, or touches app-private data.
MODDIR="$(dirname "$0")"
[ -r "$MODDIR/module.prop" ] && grep -Fxq 'id=mifitness_bridge' "$MODDIR/module.prop" || exit 1
[ "$(id -u 2>/dev/null)" = "0" ] || exit 1
BASELINE=359002
EXPECTED=112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d
result=unavailable
installed="$(pm list packages 2>/dev/null)"
if [ -z "$installed" ]; then
  result=package_manager_unavailable
elif ! printf '%s\n' "$installed" | grep -Fxq 'package:com.mi.health'; then
  result=app_removed
else
  version="$(dumpsys package com.mi.health 2>/dev/null |
    sed -n 's/.*versionCode=\([0-9][0-9]*\).*/\1/p' | head -n 1)"
  case "$version" in
    ''|*[!0-9]*) result=version_unavailable ;;
    *)
      if [ "$version" -gt "$BASELINE" ]; then
        result=upgrade_unsupported
      elif [ "$version" -lt "$BASELINE" ]; then
        result=downgrade_unsupported
      else
        paths="$(pm path com.mi.health 2>/dev/null | sed -n 's/^package://p')"
        count="$(printf '%s\n' "$paths" | sed '/^$/d' | wc -l | tr -d ' ')"
        if [ "$count" != 1 ]; then
          result=package_layout_unknown
        else
          case "$paths" in
            /data/app/*.apk|/system/app/*.apk|/system_ext/app/*.apk|/product/app/*.apk)
              if [ ! -r "$paths" ] ||
                 ! command -v sha256sum >/dev/null 2>&1; then
                result=apk_unreadable
              else
                actual="$(sha256sum "$paths" 2>/dev/null | awk '{print $1}')"
                if [ "$actual" = "$EXPECTED" ]; then
                  result=reviewed_359002
                else
                  result=apk_bytes_changed
                fi
              fi
              ;;
            *) result=package_path_untrusted ;;
          esac
        fi
      fi
      ;;
  esac
fi

# Minimal status, not a health-data or account audit.
# Do not print APK path, app data, tokens, or device identifiers.
tmp="$MODDIR/.version-guard.$$"
if ! printf 'package_profile=%s\n' "$result" > "$tmp"; then
  rm -f "$tmp"; exit 1
fi
chmod 0644 "$tmp" || { rm -f "$tmp"; exit 1; }
mv -f "$tmp" "$MODDIR/version-guard.txt" || { rm -f "$tmp"; exit 1; }
printf 'package_profile=%s\n' "$result"
if [ "$result" = reviewed_359002 ]; then
  printf 'compatibility_hook=permitted_when_user_enabled\n'
  exit 0
fi

# No version state, including temporary PM outage, is grounds to change the APK.
# Only our optional hook config is paused for subsequent process starts.
if [ -r "$MODDIR/bridge.conf" ] &&
   grep -Fxq 'calendar_hook=1' "$MODDIR/bridge.conf"; then
  temp_conf="$MODDIR/.bridge.conf.guard.$$"
  umask 022
  if {
    printf 'native_probe=1\n'
    printf 'calendar_hook=0\n'
    printf 'fail_on_conflict=1\n'
  } > "$temp_conf"; then
    chmod 0644 "$temp_conf" &&
      mv -f "$temp_conf" "$MODDIR/bridge.conf" ||
      { rm -f "$temp_conf"; printf 'hook_action=manual_safe_mode_required\n'; }
    if grep -Fxq 'calendar_hook=0' "$MODDIR/bridge.conf" 2>/dev/null; then
      printf 'hook_action=paused_for_new_processes\n'
    fi
  else
    rm -f "$temp_conf"
    printf 'hook_action=manual_safe_mode_required\n'
  fi
fi

# Only if this module actually staged system/app content: stop its own mount on
# the NEXT reboot for known replacement/removal events, not on transient errors.
stage="$(cat "$MODDIR/systemize-state.txt" 2>/dev/null)"
case "$result" in
  upgrade_unsupported|downgrade_unsupported|apk_bytes_changed|app_removed|package_layout_unknown)
    if [ "$stage" = staged-reboot-required ]; then
      if touch "$MODDIR/disable" 2>/dev/null; then
        printf 'own_overlay=disabled_next_reboot\n'
      else
        printf 'own_overlay=manual_recovery_required\n'
      fi
    fi
    ;;
esac
exit 0
