#!/system/bin/sh
# Intentionally no networking or package installation in diagnostic release.
MODDIR="$(dirname "$0")"
echo 'Native calendar feature gating active only when ZN backend, trusted signed 3.59.2 and ColorOS 17 are verified; no APK install.' > "$MODDIR/service-status.txt"
