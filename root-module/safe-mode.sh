#!/system/bin/sh
# Root-only, argument-free emergency safe mode for MiFitness-Bridge.
# Preserve installed app, SCEME mount, user data, and paired wearable state.
# Disables bridge calendar hooks on the next com.mi.health process start.
MODDIR="$(dirname "$0")"
if [ "$(id -u 2>/dev/null)" != "0" ]; then
  echo "MiFitness safe mode requires Root Shell" >&2
  exit 1
fi
if [ ! -r "$MODDIR/module.prop" ] || ! grep -Fxq 'id=mifitness_bridge' "$MODDIR/module.prop"; then
  echo "Refusing to modify an unexpected module directory" >&2
  exit 1
fi
tmp="$MODDIR/.bridge.conf.safe.$$"
umask 022
if ! {
  printf 'calendar_hook=0\n'
  printf 'fail_on_conflict=1\n'
  printf '# emergency-safe-mode=1\n'
} > "$tmp"; then
  echo "Failed to write safe mode file" >&2
  rm -f "$tmp"
  exit 1
fi
chmod 0644 "$tmp" || { rm -f "$tmp"; exit 1; }
if ! mv -f "$tmp" "$MODDIR/bridge.conf"; then
  rm -f "$tmp"
  exit 1
fi
echo "MiFitness Bridge calendar hook disabled for NEW app processes."
echo "The currently running app process is unchanged until it exits."
echo "To apply without reboot, exit Mi Fitness or run: am force-stop com.mi.health"
echo "This script did not stop the application or delete any user data."
