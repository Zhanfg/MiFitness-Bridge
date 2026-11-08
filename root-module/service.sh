#!/system/bin/sh
# Intentionally no networking or package installation in diagnostic release.
MODDIR="$(dirname "$0")"
echo 'Native diagnostic only; no APK installs and no root IPC server.' > "$MODDIR/service-status.txt"
