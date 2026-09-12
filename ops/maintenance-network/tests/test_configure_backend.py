from pathlib import Path
import importlib.util
import unittest


MODULE_PATH = Path(__file__).parents[1] / "configure-backend.py"
SPEC = importlib.util.spec_from_file_location("configure_backend", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConfigureBackendTest(unittest.TestCase):
    def test_properties_preserve_unrelated_values(self):
        source = "motd=test\nonline-mode=true\nserver-port=25565\nserver-ip=\n"
        result = MODULE.update_properties(source, 25567)
        self.assertIn("motd=test\n", result)
        self.assertIn("online-mode=false\n", result)
        self.assertIn("server-port=25567\n", result)
        self.assertIn("server-ip=127.0.0.1\n", result)

    def test_existing_velocity_section_is_updated(self):
        source = """version: 31
proxies:
  bungee-cord:
    online-mode: true
  velocity:
    enabled: false
    online-mode: false
    secret: old
scoreboards:
  save-empty-scoreboard-teams: true
"""
        result = MODULE.update_paper_global(source, "abcdef0123456789abcdef0123456789")
        self.assertIn("    enabled: true", result)
        self.assertIn("    online-mode: true", result)
        self.assertIn("    secret: 'abcdef0123456789abcdef0123456789'", result)
        self.assertIn("scoreboards:\n", result)

    def test_missing_sections_are_added(self):
        result = MODULE.update_paper_global("version: 31\n", "x" * 32)
        self.assertIn("proxies:\n  velocity:\n", result)
        self.assertIn("    enabled: true\n", result)
        self.assertIn("    online-mode: true\n", result)

    def test_spigot_bungeecord_is_disabled(self):
        source = "settings:\n  bungeecord: true\n  timeout-time: 60\nworld-settings:\n"
        result = MODULE.update_spigot(source)
        self.assertIn("  bungeecord: false\n", result)
        self.assertIn("  timeout-time: 60\n", result)


if __name__ == "__main__":
    unittest.main()
