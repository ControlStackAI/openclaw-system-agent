import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from system_agent import console_font as font

class ConsoleFontTests(unittest.TestCase):
    def test_rejects_graphical_and_serial_terminals(self):
        for tty in ['/dev/pts/0', '/dev/ttyS0', '/dev/tty0']:
            with patch.object(font.os, 'ttyname', return_value=tty):
                self.assertIsNone(font.console_device())

    def watchdog_case(self, reply, readable=True):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(font, 'STATE_DIR', Path(root)), \
             patch.object(font, 'setfont') as setter, \
             patch.object(font.select, 'select', return_value=([object()] if readable else [], [], [])), \
             patch.object(font.sys, 'stdin', io.StringIO(reply)), \
             patch('sys.stdout', io.StringIO()):
            font.watchdog('/dev/tty1', 20)
            persisted = font.state_file('/dev/tty1').exists()
            return setter.call_args_list, persisted

    def test_timeout_and_parent_eof_restore_without_saving(self):
        for reply, readable in [('', False), ('', True), ('restore\n', True)]:
            calls, persisted = self.watchdog_case(reply, readable)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[-1].args[1].name, 'previous.psf')
            self.assertFalse(persisted)

    def test_only_confirmation_saves(self):
        calls, persisted = self.watchdog_case('keep\n')
        self.assertEqual(len(calls), 2)
        self.assertTrue(persisted)

    def test_apply_failure_still_restores_snapshot(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(font, 'STATE_DIR', Path(root)), \
             patch.object(font, 'setfont', side_effect=[None, OSError('failed'), None]) as setter:
            with self.assertRaises(OSError):
                font.watchdog('/dev/tty1', 24)
            self.assertEqual(setter.call_args.args[1].name, 'previous.psf')
