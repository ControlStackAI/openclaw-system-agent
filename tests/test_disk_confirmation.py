import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch
from adapters.arch import install as arch
from adapters.nixos import install as nixos
from system_agent.install_common import confirm_disk_erasure, export_installed_pool
from system_agent.tui import Cancelled


class DiskConfirmation(unittest.TestCase):
    disk = {'serial': 'DEMO123', 'wwn': None}

    def test_typo_then_exact_phrase_retries_without_approving_typo(self):
        with patch('builtins.input', side_effect=['ERASE DEMO12X', 'ERASE DEMO123']) as prompt, \
                patch('system_agent.setup.choose', return_value=1) as choose, \
                contextlib.redirect_stdout(io.StringIO()) as feedback:
            self.assertEqual(confirm_disk_erasure(self.disk), 'ERASE DEMO123')
        self.assertEqual(prompt.call_count, 2)
        choose.assert_called_once()
        self.assertIn('Nothing has been erased', feedback.getvalue())

    def test_blank_case_and_spacing_errors_are_not_approval(self):
        for wrong in ['', 'erase DEMO123', 'ERASEDEMO123', 'ERASE  DEMO123', 'ERASE demo123']:
            with self.subTest(wrong=wrong), patch('builtins.input', return_value=wrong), \
                    patch('system_agent.setup.choose', return_value=2):
                self.assertIsNone(confirm_disk_erasure(self.disk))

    def test_explicit_cancel_never_opens_retry(self):
        with patch('builtins.input', return_value='CANCEL'), patch('system_agent.setup.choose') as choose:
            self.assertIsNone(confirm_disk_erasure(self.disk))
            choose.assert_not_called()

    def test_escape_eof_and_interrupt_cancel_without_approval(self):
        for failure in [Cancelled(), EOFError(), KeyboardInterrupt()]:
            with self.subTest(failure=type(failure).__name__), patch('builtins.input', side_effect=failure):
                self.assertIsNone(confirm_disk_erasure(self.disk))
        with patch('builtins.input', return_value='wrong'), patch('system_agent.setup.choose', side_effect=Cancelled()):
            self.assertIsNone(confirm_disk_erasure(self.disk))

    def test_wwn_is_used_when_serial_is_unavailable(self):
        with patch('builtins.input', return_value='ERASE 0xabcdef'), patch('system_agent.setup.choose') as choose:
            self.assertEqual(confirm_disk_erasure({'serial': None, 'wwn': '0xabcdef'}), 'ERASE 0xabcdef')
            choose.assert_not_called()

    def test_both_installers_preserve_prepared_plan_during_retry_and_cancel(self):
        node = dict(self.disk, name='/dev/fixture', model='Fixture', size=48 * 1024**3)
        choices = dict(hostname='fixture', username='owner', desktop='none', keyboard='us',
                       locale='en_US.UTF-8', timezone='UTC', encrypt=False, login_policy='password')
        for adapter in [arch, nixos]:
            with self.subTest(adapter=adapter.__name__), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(adapter, 'check_context'))
                disks = stack.enter_context(patch.object(adapter, 'disks', return_value=[node]))
                prepare = stack.enter_context(patch.object(adapter, 'prepare', return_value={'disk': node}))
                install = stack.enter_context(patch.object(adapter, 'install'))
                secret = stack.enter_context(patch.object(adapter, 'secret_twice'))
                stack.enter_context(patch('system_agent.interview.interview', return_value=choices))
                # Show disks, select one, retry a typo, then explicitly cancel.
                stack.enter_context(patch('system_agent.setup.choose', side_effect=[2, 1, 1]))
                stack.enter_context(patch('builtins.input', side_effect=['ERASE DEMO12X', 'CANCEL']))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                self.assertIsNone(adapter.interactive('/unused-fixture-state'))
                disks.assert_called_once()
                prepare.assert_called_once_with(node, choices, None)
                install.assert_not_called()
                secret.assert_not_called()


class PoolExportDiagnostics(unittest.TestCase):
    def test_success_exports_only_the_named_pool_without_force(self):
        with patch('system_agent.install_common.run') as run:
            export_installed_pool('csafixture')
            run.assert_called_once_with(['zpool', 'export', 'csafixture'], capture_output=True)

    def test_failure_preserves_zfs_detail_and_reports_completed_disk_writes(self):
        failure = subprocess.CalledProcessError(1, ['zpool', 'export', 'csafixture'],
            stderr="cannot export 'csafixture': pool is busy")
        with patch('system_agent.install_common.run', side_effect=failure) as run:
            with self.assertRaises(ValueError) as caught:
                export_installed_pool('csafixture')
            self.assertIn('pool is busy', str(caught.exception))
            self.assertIn('disk has already been changed', str(caught.exception))
            self.assertIn('Do not restart installation', str(caught.exception))
            self.assertIn('exit 1', str(caught.exception))
            run.assert_called_once_with(['zpool', 'export', 'csafixture'], capture_output=True)
