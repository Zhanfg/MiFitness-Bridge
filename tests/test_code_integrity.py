"""Offline tests of module package integrity guard using synthetic files only."""
import hashlib
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = ROOT / "root-module" / "check-code.sh"
ASSETS = (
    "zygisk/arm64-v8a.so", "classes.dex", "module.prop", "customize.sh",
    "service.sh", "guard.sh", "hook-audit.sh", "check-code.sh", "action.sh", "safe-mode.sh",
    "enable-calendar.sh",
)


class ModuleIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mifitness-code-guard-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        for path in ASSETS:
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            if path == "check-code.sh":
                file.write_bytes(CHECKER.read_bytes())
            elif path == "module.prop":
                file.write_text("id=mifitness_bridge\n")
            else:
                file.write_bytes(("synthetic:" + path).encode())
        self.rebuild_manifest()

    def rebuild_manifest(self):
        with (self.root / "code-integrity.sha256").open("w") as fp:
            for path in ASSETS:
                hash_value = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                fp.write(hash_value + "  " + path + "\n")

    def check(self):
        return subprocess.run(
            ["sh", str(self.root / "check-code.sh")],
            capture_output=True, text=True, timeout=10,
        )

    def test_unchanged_package_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("code_integrity=matches_packaged_manifest", result.stdout)

    def test_modified_native_library_is_detected(self):
        (self.root / "zygisk/arm64-v8a.so").write_bytes(b"synthetic changed file")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code_integrity=content_changed", result.stdout)

    def test_deleted_dex_is_detected(self):
        (self.root / "classes.dex").unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code_integrity=missing_or_redirected_file", result.stdout)

    def test_redirected_file_is_detected(self):
        (self.root / "classes.dex").unlink()
        (self.root / "classes.dex").symlink_to(self.root / "module.prop")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code_integrity=missing_or_redirected_file", result.stdout)

    def test_missing_manifest_fails_closed(self):
        (self.root / "code-integrity.sha256").unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code_integrity=unavailable", result.stdout)

    def test_duplicate_manifest_entry_is_rejected(self):
        with (self.root / "code-integrity.sha256").open("a") as fp:
            fp.write(hashlib.sha256(b"synthetic").hexdigest() + "  classes.dex\n")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code_integrity=invalid_manifest", result.stdout)


if __name__ == "__main__":
    unittest.main()
