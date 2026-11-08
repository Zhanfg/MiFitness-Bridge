#!/system/bin/sh
# Read-only official Xiaomi GetApps metadata probe. No APK downloads or installs.
OUT="/sdcard/Download/MiFitness_GetApps_Probe_$(date '+%Y%m%d_%H%M%S').txt"
TMP="/data/local/tmp/mifitness_getapps_probe_$$"
mkdir -p "$TMP" || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
{
  echo 'MiFitness GetApps official URL probe v0.4.0'
  echo 'Package: com.mi.health'
  echo 'Date:' "$(date '+%Y-%m-%d %H:%M:%S %z')"
  echo 'Mode: metadata only; no APK download, no install'
  echo '---'
} > "$OUT" || exit 1
n=0
for url in \
  'https://app.mi.com/details?id=com.mi.health' \
  'https://m.app.mi.com/details?id=com.mi.health' \
  'https://r.app.xiaomi.com/details?id=com.mi.health'
do
  n=$((n + 1))
  body="$TMP/$n.body"
  hdr="$TMP/$n.hdr"
  echo "URL: $url" >> "$OUT"
  if command -v curl >/dev/null 2>&1; then
    result="$(curl --silent --show-error --location --max-time 18 --connect-timeout 8 \
      --proto '=https' --proto-redir '=https' --max-filesize 1048576 \
      --dump-header "$hdr" --output "$body" --write-out 'HTTP %{http_code}' \
      "$url" 2> "$TMP/curl.err")"
    status=$?
    echo "curl_status=$status $result" >> "$OUT"
    [ "$status" -eq 0 ] || sed -n '1,3p' "$TMP/curl.err" >> "$OUT"
  elif command -v wget >/dev/null 2>&1; then
    wget -T 18 -O "$body" "$url" > "$TMP/wget.log" 2>&1
    status=$?
    echo "wget_status=$status" >> "$OUT"
    [ "$status" -eq 0 ] || sed -n '1,3p' "$TMP/wget.log" >> "$OUT"
  elif command -v busybox >/dev/null 2>&1; then
    busybox wget -T 18 -O "$body" "$url" > "$TMP/wget.log" 2>&1
    status=$?
    echo "busybox_wget_status=$status" >> "$OUT"
    [ "$status" -eq 0 ] || sed -n '1,3p' "$TMP/wget.log" >> "$OUT"
  else
    echo 'error=no curl, wget or busybox wget available' >> "$OUT"
    break
  fi
  if [ -s "$body" ]; then
    echo "body_bytes=$(wc -c < "$body" | tr -d ' ')" >> "$OUT"
    if grep -F -q 'com.mi.health' "$body"; then
      echo 'package_string_in_page=yes (not proof of listing)' >> "$OUT"
    else
      echo 'package_string_in_page=no' >> "$OUT"
    fi
    if grep -F -q '维护中' "$body"; then
      echo 'maintenance_text_in_page=yes' >> "$OUT"
    else
      echo 'maintenance_text_in_page=no' >> "$OUT"
    fi
    LC_ALL=C grep -aoE 'appID|版本号|包名|维护中|com\.mi\.health' "$body" | head -n 20 | tr '\n' ' ' >> "$OUT"
    echo >> "$OUT"
  else
    echo 'body_bytes=0' >> "$OUT"
  fi
  echo '---' >> "$OUT"
done
printf 'Report: %s\n' "$OUT"
