"""Cross-check machine-readable bridge policy against the actual source guards."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "root-module" / "compatibility-policy.json"


class PolicyDeclarationTests(unittest.TestCase):
    def test_no_owner_update_lock_or_uninstall_block(self):
        policy = json.loads(POLICY.read_text())
        self.assertEqual(policy["package_name"], "com.mi.health")
        self.assertTrue(policy["allow_owner_upgrade_downgrade_uninstall"])
        self.assertFalse(policy["block_package_manager_operations"])
        self.assertFalse(policy["root_resistant"])
        self.assertEqual(policy["app_private_data_backup"], "not_performed")

    def test_version_and_hash_pins_match_all_enforcers(self):
        policy = json.loads(POLICY.read_text())
        baseline = str(policy["reviewed_version_code"])
        sha = policy["reviewed_apk_sha256"]
        signer = policy["reviewed_signer_sha256"]
        for path in (
            "root-module/guard.sh",
            "root-module/enable-calendar.sh",
            "root-module/customize.sh",
            "java/src/dev/axymorrsen/mifitness/ApkIntegrity.java"
        ):
            with self.subTest(path=path):
                self.assertIn(sha, (ROOT / path).read_text())
        self.assertIn(baseline,
                      (ROOT / "java/src/dev/axymorrsen/mifitness/CalendarHook.java").read_text())
        self.assertIn(signer,
                      (ROOT / "java/src/dev/axymorrsen/mifitness/CalendarHook.java").read_text())

    def test_default_mode_does_not_modify_art(self):
        config = (ROOT / "root-module" / "bridge.conf").read_text()
        self.assertIn("native_probe=1", config)
        self.assertIn("calendar_hook=0", config)
        self.assertIn("fail_on_conflict=1", config)


if __name__ == "__main__":
    unittest.main()
