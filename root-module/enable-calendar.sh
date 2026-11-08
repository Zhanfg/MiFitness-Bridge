#!/system/bin/sh
# Zero-argument, root-only activation of the reviewed Mi Fitness 3.59.2 calendar gates.
# Does not install APKs, change granted permissions, or force-stop the app.
MODDIR="$(dirname "$0")"
if [ "$(id -u 2>/dev/null)" != 0 ]; then
  echo 'Root Shell required' >&2
  exit 1
fi
if [ ! -r "$MODDIR/module.prop" ] ||
   ! grep -Fxq 'id=mifitness_bridge' "$MODDIR/module.prop"; then
  echo 'Unexpected module path; refusing update' >&2
  exit 1
fi
if [ "$(getprop ro.build.version.sdk)" != 37 ] ||
   [ "$(getprop ro.product.model)" != PJZ110 ]; then
  echo 'Unsupported Android version or device model' >&2
  exit 1
fi
if ! dumpsys package com.mi.health 2>/dev/null |
     grep -Eq 'versionCode=359002([^0-9]|$)'; then
  echo 'Installed Xiaomi Mi Fitness is not the reviewed 3.59.2 version' >&2
  exit 1
fi
paths="$(pm path com.mi.health 2>/dev/null | sed -n 's/^package://p')"
if [ "$(printf '%s\n' "$paths" | sed '/^$/d' | wc -l | tr -d ' ')" != 1 ]; then
  echo 'Unknown or split package layout; activation refused' >&2
  exit 1
fi
if [ ! -r "$paths" ] || ! command -v sha256sum >/dev/null 2>&1; then
  echo 'Unable to read installed APK for integrity verification' >&2
  exit 1
fi
expected=112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d
actual="$(sha256sum "$paths" 2>/dev/null | awk '{print $1}')"
if [ "$actual" != "$expected" ]; then
  echo 'Installed APK is not byte-identical to reviewed Xiaomi 3.59.2; hooks stay off' >&2
  exit 1
fi
tmp="$MODDIR/.bridge.conf.active.$$"
umask 022
if ! {
  printf 'native_probe=1\n'
  printf 'calendar_hook=1\n'
  printf 'fail_on_conflict=1\n'
} > "$tmp"; then
  rm -f "$tmp"
  exit 1
fi
chmod 0644 "$tmp" || { rm -f "$tmp"; exit 1; }
if ! mv -f "$tmp" "$MODDIR/bridge.conf"; then
  rm -f "$tmp"
  exit 1
fi
echo 'MiFitness Bridge calendar gate hooks ARMED for new app processes.'
echo 'Existing app processes were not modified or force-stopped.'
echo 'To activate, close/reopen Mi Fitness; to retreat use safe-mode.sh.'
