#!/usr/bin/env python3
"""Xiaomi App Store candidate probe. No APK is installed by this program.

Standard library only, HTTPS only. Downloads are opt-in and require both
Android SDK aapt and apksigner to verify package/version/signing certificate.
This is NOT a Xiaomi-supported public download API.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

if __package__:
    from .verify_calendar_abi import inspect as inspect_calendar_abi
else:
    from verify_calendar_abi import inspect as inspect_calendar_abi

TARGET = "com.mi.health"
BASELINE_VERSION_CODE = 359002
# SHA-256 of the V1 certificate in the user-supplied com.mi.health 3.59.2.
# Certificate digest is public; it is NOT an APK checksum or secret.
PINNED_CERT_SHA256 = "c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025"
PAGES = (
    "https://app.mi.com/details?id={pkg}",
    "https://m.app.mi.com/details?id={pkg}",
    "https://r.app.xiaomi.com/details?id={pkg}",
)
MAX_PAGE = 2 * 1024 * 1024
MAX_APK = 400 * 1024 * 1024

def allowed_url(url):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and (
        host in {"app.mi.com", "m.app.mi.com", "r.app.xiaomi.com", "market.xiaomi.com"}
        or host.endswith(".market.xiaomi.com")
    )

class StrictRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError("refusing non-Xiaomi or non-HTTPS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def opener():
    return build_opener(StrictRedirects())

def fetch_page(url):
    if not allowed_url(url):
        raise ValueError("untrusted URL")
    req = Request(url, headers={"User-Agent": "MiFitnessBridge-SourceProbe/0.4"})
    with opener().open(req, timeout=12) as res:
        raw = res.read(MAX_PAGE + 1)
        if len(raw) > MAX_PAGE:
            raise ValueError("metadata page exceeds size cap")
        return raw.decode("utf-8", errors="replace")

def parse_market_page(body, package=TARGET):
    """Return a candidate only when the page actually contains target package."""
    visible = html.unescape(re.sub(r"<[^>]*>", "\n", body))
    normalized = re.sub(r"\s+", " ", visible)
    if re.search(r"包名\s*[:：]?\s*" + re.escape(package) + r"(?![\w.])", normalized) is None:
        return None
    # appID and version are rendered as separate text nodes on the store page.
    id_match = re.search(r"appID\s*[:：]?\s*(\d{1,12})(?!\d)", normalized, re.I)
    ver_match = re.search(r"版本号\s*[:：]?\s*([0-9][A-Za-z0-9._-]{0,36})", normalized)
    if not id_match:
        return None
    return {
        "package": package,
        "app_id": id_match.group(1),
        "listed_version": ver_match.group(1) if ver_match else None,
        "maintenance": ("维护中" in normalized or "下载服务目前正在升级维护" in normalized),
        "candidate_url": "https://app.mi.com/download/" + id_match.group(1),
    }

def discover():
    checks = []
    candidate = None
    for page in PAGES:
        url = page.format(pkg=quote(TARGET))
        try:
            parsed = parse_market_page(fetch_page(url))
            if not parsed:
                checks.append({"page": url, "status": "target_not_listed"})
                continue
            checks.append({"page": url, "status": "maintenance" if parsed["maintenance"] else "candidate", "version": parsed["listed_version"]})
            if not parsed["maintenance"]:
                candidate = parsed
                break
        except Exception as exc:
            checks.append({"page": url, "status": "request_failed", "reason": str(exc)[:180]})
    return {"target": TARGET, "provider": "xiaomi_market_legacy", "checks": checks, "candidate": candidate}

def checked_open(url):
    if not allowed_url(url):
        raise ValueError("download URL outside approved Xiaomi hosts")
    req = Request(url, headers={"User-Agent": "MiFitnessBridge-SourceProbe/0.4"})
    response = opener().open(req, timeout=20)
    if not allowed_url(response.geturl()):
        response.close()
        raise ValueError("redirect leaves approved Xiaomi hosts")
    return response

def stage_candidate(url, output):
    """Stage a candidate to a temp file. Caller MUST verify before promoting."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".mifitness-", suffix=".apk", dir=str(output.parent), delete=False) as tmp:
        temp_path = Path(tmp.name)
        try:
            with checked_open(url) as res:
                first = res.read(4)
                if first not in (bytes((80,75,3,4)), bytes((80,75,5,6)), bytes((80,75,7,8))):
                    raise ValueError("response is not an APK/ZIP (may be HTML maintenance page)")
                tmp.write(first)
                length = len(first)
                while True:
                    chunk = res.read(1024 * 1024)
                    if not chunk:
                        break
                    length += len(chunk)
                    if length > MAX_APK:
                        raise ValueError("APK exceeds 400MiB cap")
                    tmp.write(chunk)
            return temp_path
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

def verify_apk(path, minimum_version):
    if not shutil.which("aapt") or not shutil.which("apksigner"):
        raise RuntimeError("Android SDK aapt and apksigner are required for verified download")
    badging = subprocess.run(["aapt", "dump", "badging", str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
    match = re.search(r"^package: name='([^']+)' versionCode='(\d+)'", badging, re.M)
    if not match or match.group(1) != TARGET:
        raise ValueError("downloaded package identity does not equal com.mi.health")
    version_code = int(match.group(2))
    if version_code < minimum_version:
        raise ValueError("downloaded APK is older than requested baseline")
    if version_code != BASELINE_VERSION_CODE:
        raise ValueError("New Mi Fitness version has no approved native Hook semantic profile; download refused")
    result = subprocess.run(["apksigner", "verify", "--print-certs", str(path)], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise ValueError("APK signature verification failed")
    signers = re.findall(r"Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F:]+)", result.stdout)
    if not signers or any(x.replace(":", "").lower() != PINNED_CERT_SHA256 for x in signers):
        raise ValueError("APK signing certificate is not the trusted baseline signer")
    abi = inspect_calendar_abi(Path(path))
    if not abi["abi_match"]:
        raise ValueError("Downloaded APK no longer matches required 3.59.2 ART method ABI")
    return {
        "package": TARGET, "version_code": version_code,
        "sha256": abi["apk_sha256"],
        "signature_verified": True, "calendar_abi_match": True,
        "semantic_profile": "359002-reviewed-only"
    }

def main():
    ap = argparse.ArgumentParser(description="Probe legacy Xiaomi market for com.mi.health (fail closed)")
    ap.add_argument("--download", metavar="PATH", help="opt-in: download and verify APK to this local path, never install")
    ap.add_argument("--min-version-code", type=int, default=BASELINE_VERSION_CODE)
    args = ap.parse_args()
    result = discover()
    if args.download and result["candidate"]:
        temp = None
        try:
            temp = stage_candidate(result["candidate"]["candidate_url"], args.download)
            verified = verify_apk(temp, args.min_version_code)
            Path(args.download).parent.mkdir(parents=True, exist_ok=True)
            temp.replace(args.download)
            result["verified_download"] = verified
        except Exception as exc:
            result["download_error"] = str(exc)
            if temp is not None:
                temp.unlink(missing_ok=True)
    elif args.download:
        result["download_error"] = "No validated Xiaomi market candidate for com.mi.health"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.download and "verified_download" not in result else 0

if __name__ == "__main__":
    sys.exit(main())
