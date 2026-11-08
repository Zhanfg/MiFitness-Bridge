#!/system/bin/sh
# SHA-256 manifest detects accidental changes and incomplete module installations.
# NOT a root-proof trust anchor: a root actor could rewrite both files and manifest.
MODDIR="$(dirname "$0")"
[ -r "$MODDIR/module.prop" ] &&
  grep -Fxq 'id=mifitness_bridge' "$MODDIR/module.prop" || exit 2
if [ ! -r "$MODDIR/code-integrity.sha256" ] ||
   ! command -v sha256sum >/dev/null 2>&1; then
  echo "code_integrity=unavailable"
  exit 2
fi
files='zygisk/arm64-v8a.so classes.dex module.prop customize.sh service.sh guard.sh hook-audit.sh check-code.sh action.sh safe-mode.sh enable-calendar.sh compatibility-policy.json'
manifest="$MODDIR/code-integrity.sha256"
for file in $files; do
  expected="$(awk -v path="$file" '$2==path {count++; h=$1} END {if(count==1) print h}' "$manifest")"
  case "$expected" in
    ''|*[!0123456789abcdef]*) echo "code_integrity=invalid_manifest"; exit 2 ;;
  esac
  [ "$(printf '%s' "$expected" | wc -c | tr -d ' ')" -eq 64 ] ||
    { echo "code_integrity=invalid_manifest"; exit 2; }
  if [ ! -f "$MODDIR/$file" ] || [ -L "$MODDIR/$file" ]; then
    echo "code_integrity=missing_or_redirected_file"
    exit 2
  fi
  actual="$(sha256sum "$MODDIR/$file" 2>/dev/null | awk '{print $1}')"
  if [ "$actual" != "$expected" ]; then
    echo "code_integrity=content_changed"
    exit 2
  fi
done
echo "code_integrity=matches_packaged_manifest"
exit 0
