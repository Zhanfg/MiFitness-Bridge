"""Synthetic Zygisk coexistence inventory tests. Never read real module folders."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HookInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.modules = self.root / "other-modules"
        self.modules.mkdir()
        self.current = self.modules / "mifitness_bridge"
        self.current.mkdir()
        (self.current / "module.prop").write_text("id=mifitness_bridge\n")
        self.script = self.current / "hook-audit.sh"
        self.script.write_text(
            (ROOT / "root-module" / "hook-audit.sh").read_text().replace(
                "/data/adb/modules /data/adb/ksu/modules",
                str(self.modules)
            )
        )
        self.add_module("mifitness_bridge", enabled=True, zygisk=True)

    def add_module(self, name, enabled=True, zygisk=False):
        module = self.modules / name
        module.mkdir(exist_ok=True)
        (module / "module.prop").write_text("id=" + name + "\n")
        if not enabled:
            (module / "disable").touch()
        if zygisk:
            (module / "zygisk").mkdir(exist_ok=True)
            (module / "zygisk" / "arm64-v8a.so").write_bytes(b"synthetic")
        return module

    def run_probe(self):
        return subprocess.run(["sh", str(self.script)], capture_output=True,
                              text=True, timeout=10)

    def test_other_enabled_zygisk_module_counted_without_names(self):
        self.add_module("module-alpha", zygisk=True)
        self.add_module("module-bravo", zygisk=True)
        self.add_module("nonzygisk")
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("other_zygisk_modules_visible=2", result.stdout)
        self.assertIn("injection_conflict_assessment=not_proven_by_inventory",
                      result.stdout)
        self.assertNotIn("module-alpha", result.stdout)
        self.assertNotIn("module-bravo", result.stdout)

    def test_disabled_modules_not_counted_or_changed(self):
        other = self.add_module("disabled-module", enabled=False, zygisk=True)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("other_zygisk_modules_visible=0", result.stdout)
        self.assertTrue((other / "disable").exists())


if __name__ == "__main__":
    unittest.main()
