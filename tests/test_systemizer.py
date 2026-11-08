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
        self.write_tool("chown", "#!/bin/sh\nexit 0\n")
        self.write_tool("chcon", "#!/bin/sh\nexit 0\n")
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

    def run_installer(self, installed=True, system=False, version="359002", paths="", script=SCRIPT):
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
            ["sh", str(script)], env=env, capture_output=True,
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


    def test_selinux_context_failure_removes_overlay(self):
        # Entirely synthetic local files and command stubs; never writes /system.
        installed_dir = self.dir / "data" / "app" / "com.mi.health-test"
        installed_dir.mkdir(parents=True)
        apk = installed_dir / "base.apk"
        apk.write_bytes(b"SYNTHETIC TEST APK")
        script = self.dir / "sandboxed-context-test.sh"
        script.write_text(
            SCRIPT.read_text().replace(
                "/data/app/*.apk",
                str(self.dir / "data" / "app" / "*.apk")
            )
        )
        self.write_tool(
            "sha256sum",
            "#!/bin/sh\nprintf '112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d  %s\\n' \"$1\"\n"
        )
        self.write_tool("chcon", "#!/bin/sh\nexit 1\n")
        proc, state = self.run_installer(
            paths="package:" + str(apk), script=script
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "context-failed")
        self.assert_no_system_mount()

    def test_single_pinned_apk_copy_path_in_sandbox(self):
        # Mechanical staging test ONLY. All paths and SHA output are mocked.
        # This does not establish authenticity of any real APK.
        installed_dir = self.dir / "data" / "app" / "com.mi.health-test"
        installed_dir.mkdir(parents=True)
        apk = installed_dir / "base.apk"
        apk.write_bytes(b"SYNTHETIC TEST APK, NO PROPRIETARY DATA")
        modified_script = self.dir / "sandboxed-customize.sh"
        original = SCRIPT.read_text()
        self.assertIn("/data/app/*.apk", original)
        modified_script.write_text(
            original.replace("/data/app/*.apk", str(self.dir / "data" / "app" / "*.apk"))
        )
        self.write_tool(
            "sha256sum",
            "#!/bin/sh\nprintf '112e603b8342cb134402a6dcabdf3ec16fd5171ec65a1d5f7cb7efd83cb0995d  %s\\n' \"$1\"\n"
        )
        proc, state = self.run_installer(
            paths="package:" + str(apk), script=modified_script
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "staged-reboot-required")
        result = self.modpath / "system" / "app" / "MiFitnessBridge" / "base.apk"
        self.assertEqual(result.read_bytes(), apk.read_bytes())


    def run_boot_verifier(self, state, version):
        service_path = self.modpath / "service.sh"
        service_path.write_text((ROOT / "root-module" / "service.sh").read_text())
        (self.modpath / "systemize-state.txt").write_text(state)
        # No sleeping, actual root, devices, or package manager access.
        self.write_tool(
            "getprop",
            '#!/bin/sh\nif [ "$1" = "sys.boot_completed" ]; then echo 1; '
            'else echo arm64-v8a; fi\n'
        )
        env = os.environ.copy()
        env.update({
            "PATH": str(self.bindir) + os.pathsep + env.get("PATH", ""),
            "MOCK_VERSION": version,
            "MOCK_ALL_PACKAGES": "package:com.mi.health",
            "MOCK_SYSTEM_PACKAGES": "package:com.mi.health",
            "MOCK_PM_PATH": "",
        })
        proc = subprocess.run(
            ["sh", str(service_path)], env=env, capture_output=True,
            text=True, check=False, timeout=10
        )
        output = (self.modpath / "boot-status.txt").read_text()
        return proc, output

    def test_boot_version_drift_disables_own_overlay_at_next_boot(self):
        proc, report = self.run_boot_verifier("staged-reboot-required", "359009")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("app_version_profile=mismatch_or_unavailable", report)
        self.assertIn("module_action=disabled_on_next_boot_due_to_version_drift", report)
        self.assertTrue((self.modpath / "disable").is_file())

    def test_boot_unchanged_baseline_keeps_own_overlay(self):
        proc, report = self.run_boot_verifier("staged-reboot-required", "359002")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("app_version_profile=359002_verified", report)
        self.assertFalse((self.modpath / "disable").exists())

    def test_boot_foreign_sceme_overlay_is_never_disabled(self):
        proc, report = self.run_boot_verifier("existing-system", "359009")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("app_version_profile=mismatch_or_unavailable", report)
        self.assertFalse((self.modpath / "disable").exists())



    def test_sourced_kernelsu_installer_continues_after_safe_skip(self):
        # KernelSU uses '. customize.sh'; 'exit 0' here would kill update-binary.
        marker = self.dir / "manager-resumed"
        harness = self.dir / "manager-installer.sh"
        harness.write_text(
            '#!/bin/sh\n'
            '. "' + str(SCRIPT) + '"\n'
            'printf ok > "' + str(marker) + '"\n'
        )
        proc, state = self.run_installer(system=True, script=harness)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "existing-system")
        self.assertEqual(marker.read_text(), "ok")
        self.assert_no_system_mount()

    def test_sourced_kernelsu_installer_continues_when_app_absent(self):
        marker = self.dir / "manager-resumed"
        harness = self.dir / "manager-installer.sh"
        harness.write_text(
            '#!/bin/sh\n'
            '. "' + str(SCRIPT) + '"\n'
            'printf ok > "' + str(marker) + '"\n'
        )
        proc, state = self.run_installer(installed=False, script=harness)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(state, "app-absent")
        self.assertEqual(marker.read_text(), "ok")
        self.assert_no_system_mount()



    def run_safe_mode(self, simulated_uid):
        safe = self.modpath / "safe-mode.sh"
        safe.write_text((ROOT / "root-module" / "safe-mode.sh").read_text())
        (self.modpath / "module.prop").write_text("id=mifitness_bridge\nversion=v0.5.0-dev\n")
        conf = self.modpath / "bridge.conf"
        conf.write_text("calendar_hook=1\nfail_on_conflict=1\n")
        self.write_tool("id", "#!/bin/sh\nprintf '%s\\n' '" + str(simulated_uid) + "'\n")
        env = os.environ.copy()
        env["PATH"] = str(self.bindir) + os.pathsep + env.get("PATH", "")
        proc = subprocess.run(
            ["sh", str(safe)], env=env, capture_output=True,
            text=True, check=False, timeout=10
        )
        return proc, conf.read_text()

    def test_safe_mode_disables_only_calendar_hook(self):
        proc, conf = self.run_safe_mode(0)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("calendar_hook=0", conf)
        self.assertIn("fail_on_conflict=1", conf)
        self.assertFalse((self.modpath / "disable").exists())
        self.assert_no_system_mount()

    def test_non_root_safe_mode_refuses_configuration_changes(self):
        proc, conf = self.run_safe_mode(2000)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("calendar_hook=1", conf)
        self.assert_no_system_mount()


if __name__ == "__main__":
    unittest.main()
