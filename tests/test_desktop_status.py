import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('desktop_status', Path(__file__).parents[1] / 'adapters/nixos/hyprland/desktop-status.py')
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)


class DesktopStatusTests(unittest.TestCase):
    def test_only_sanitized_service_fields_are_exposed(self):
        result = status.service_status('ActiveState=active\nMemoryCurrent=1234\nCPUUsageNSec=5678\nNRestarts=2\nEnvironment=TOKEN=private\nExecStart=private-command\n')
        self.assertEqual(result, dict(state='active', memory=1234, cpu_ns=5678, restarts=2))
        self.assertNotIn('private', str(result))

    def test_unavailable_accounting_is_not_displayed_as_zero(self):
        result = status.service_status('ActiveState=failed\nMemoryCurrent=[not set]\nCPUUsageNSec=18446744073709551615\nNRestarts=-1\n')
        self.assertEqual(result, dict(state='failed', memory=None, cpu_ns=None, restarts=None))
        self.assertEqual(status.service_status('ActiveState=unexpected')['state'], 'unknown')
