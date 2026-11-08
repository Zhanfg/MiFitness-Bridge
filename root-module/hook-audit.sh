#!/system/bin/sh
# One-shot, read-only module coexistence inventory.
# A Zygisk payload existing on disk does NOT prove it targets Mi Fitness.
# No modules are disabled, modified, loaded or named in public logs.
MODDIR="$(dirname "$0")"
[ -r "$MODDIR/module.prop" ] &&
  grep -Fxq 'id=mifitness_bridge' "$MODDIR/module.prop" || exit 1
count=0
for root in /data/adb/modules /data/adb/ksu/modules; do
  [ -d "$root" ] || continue
  for dir in "$root"/*; do
    [ -d "$dir" ] || continue
    [ "$dir" = "$MODDIR" ] && continue
    [ -e "$dir/disable" ] && continue
    [ -e "$dir/remove" ] && continue
    [ -r "$dir/module.prop" ] || continue
    found=no
    for lib in "$dir"/zygisk/*.so; do
      if [ -s "$lib" ]; then found=yes; break; fi
    done
    if [ "$found" = yes ]; then count=$((count+1)); fi
  done
done
printf 'other_zygisk_modules_visible=%s\n' "$count"
printf 'injection_conflict_assessment=not_proven_by_inventory\n'
exit 0
