#!/usr/bin/env python3
"""Host-only, zero-root tests for systemizer fail-closed states.

Runs the real customize.sh with fake pm/getprop/dumpsys binaries.
No files under /system, /data/app, or /data/adb are ever changed.
"""
import os
import pathlib
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "root-module" / "customize.sh"


class SystemizerSafetyTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="mifitness-systemizer-")
        self.addCleanup(self.tempdir.cleanup)
        self.dir = pathlib.Path(self.tempdir.name)
        self.modpath = self.dir / "module"
        (self.modpath / "zygisk").mkdir(parents=True)
        (self.modpath / "zygisk" / "arm64-v8a.so").write_bytes(b"TEST PLACEHOLDER, NOT A REAL ELF")
        self.bindir = self.dir / "bin"
        self.bindir.mkdir()
        self.write_tool(
            "getprop", '#!/bin/sh\nprintf "%s\\n" "arm64-v8a"\n'
        )
        self.write_tool(
            "ui_print", '#!/bin/sh\nexit 0\n'
        )
        self.write_tool(
            "pm",
            "#!/bin/sh\n"
            'if [ "$1" = "list" ] && [ "$2" = "packages" ]; then\n'
            '  if [ "$3" = "-s" ]; then printf "%s\\n" "$MOCK_SYSTEM_PACKAGES";\n'
            '  else printf "%s\\n" "$MOCK_ALL_PACKAGES"; fi\n'
            'elif [ "$1" = "path" ]; then printf "%s\\n" "$MOCK_PM_PATH"; fi\n'
        )
        self.write_tool(
            "dumpsys",
            '#!/bin/sh\nprintf "Packages:\\n  Package [com.mi.health]:\\n'
            '    versionCode=%s minSdk=26\\n" "$MOCK_VERSION"\n'
        )

    def write_tool(self, name, script):
        p = self.bindir / name
        p.write_text(script)
        p.chmod(0o755)

    def run_installer(self, installed=True, system=False, version="359002", paths=""):
        env = os.environ.copy()
        env.update({
            "PATH": str(self.bindir) + os.pathsep + env.get("PATH", ""),
            "MODPATH": str(self.modpath),
            "MOCK_ALL_PACKAGES": "package:com.mi.health" if installed else "package:other.app",
            "MOCK_SYSTEM_PACKAGES": "package:com.mi.health" if system else "package:other.app",
            "MOCK_VERSION": version,
            "MOCK_PM_PATH": paths,
        })
        result = subprocess.run(
            ["sh", str(SCRIPT)], env=env, capture_output=True,
            text=True, check=False, timeout=15
        )
        state_file = self.modpath / "systemize-state.txt"
        state = state_file.read_text().strip() if state_file.exists() else ""
        return result, state

    def assert_no_system_mount(self):
        self.assertFalse((self.modpath / "system").exists(),
                         "systemizer must fail closed without writing an overlay")

    def test_existing_sceme_system_app_is_preserved(self):
        proc, state = self.run_installer(system=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "existing-system")
        self.assert_no_system_mount()

    def test_uninstalled_app_is_not_systemized(self):
        proc, state = self.run_installer(installed=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "app-absent")
        self.assert_no_system_mount()

    def test_unknown_version_is_not_systemized(self):
        proc, state = self.run_installer(version="359009")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "version-unverified")
        self.assert_no_system_mount()

    def test_missing_package_path_is_not_guessed(self):
        proc, state = self.run_installer()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "path-unavailable")
        self.assert_no_system_mount()

    def test_split_packages_are_not_copied(self):
        paths = (
            "package:/data/app/~~random/com.mi.health-123/base.apk\n"
            "package:/data/app/~~random/com.mi.health-123/split_config.arm64_v8a.apk"
        )
        proc, state = self.run_installer(paths=paths)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "split-not-pinned")
        self.assert_no_system_mount()

    def test_fake_apk_path_is_rejected_without_side_effects(self):
        # sha256sum must not be called to install arbitrary untrusted paths.
        proc, state = self.run_installer(paths="package:/data/local/tmp/fake.apk")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(state, {"hash-unavailable", "hash-untrusted"})
        self.assert_no_system_mount()


if __name__ == "__main__":
    unittest.main()
