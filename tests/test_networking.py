import subprocess
import unittest
from unittest.mock import patch
from system_agent import networking


class NetworkMessages(unittest.TestCase):
    def test_loopback_is_not_an_adapter(self):
        with patch.object(networking, 'command', side_effect=[
            subprocess.CompletedProcess([], 0, 'lo:loopback:connected (externally)\n'),
            subprocess.CompletedProcess([], 0, '{"rfkilldevices": []}')]):
            report = networking.status()
        self.assertEqual(report['devices'], [])
        self.assertIn('No network adapter', networking.explain(report))

    def test_hardware_block_precedes_missing_adapter(self):
        report = {'manager_ready': True, 'devices': [], 'radios': [{'type': 'wlan', 'hard': 'blocked'}]}
        self.assertIn('wireless key or switch', networking.explain(report))

    def test_bluetooth_block_does_not_hide_wifi(self):
        report = {'manager_ready': True, 'devices': [{'name': 'wlan0', 'type': 'wifi', 'state': 'disconnected'}],
                  'radios': [{'type': 'bluetooth', 'hard': 'blocked'}]}
        self.assertIn('Activate a connection', networking.explain(report))

    def test_missing_adapter_does_not_open_empty_menu(self):
        with patch.object(networking, 'command', return_value=subprocess.CompletedProcess([], 0, '')), \
             patch.object(networking, 'status', return_value={'manager_ready': True, 'devices': [], 'radios': []}), \
             patch.object(networking.subprocess, 'run') as run:
            self.assertFalse(networking.connect())
            run.assert_not_called()
