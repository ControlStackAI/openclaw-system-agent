import unittest
from types import SimpleNamespace
from system_agent.readiness import readiness


class ReadinessTests(unittest.TestCase):
    def check(self, responses):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            rc, out = responses.pop(0)
            return SimpleNamespace(returncode=rc, stdout=out)
        return readiness(run), calls

    def test_offline_never_reaches_clock(self):
        result, calls = self.check([(6, '')])
        self.assertFalse(result[0])
        self.assertEqual(len(calls), 1)
        self.assertIn('internet', result[1])

    def test_tls_error_has_separate_message(self):
        result, calls = self.check([(60, '')])
        self.assertIn('secure connection', result[1])
        self.assertEqual(len(calls), 1)

    def test_clock_wait_follows_connectivity(self):
        result, calls = self.check([(0, '200'), (0, '200'), (0, 'no')])
        self.assertIn('clock', result[1])
        self.assertEqual(calls[-1][0], 'timedatectl')

    def test_ready(self):
        self.assertTrue(self.check([(0, '200'), (0, '200'), (0, 'yes')])[0][0])

class OnboardingGateTests(unittest.TestCase):
    def test_disconnect_after_selection_blocks_login(self):
        import os
        import tempfile
        from unittest.mock import patch
        from runtimes.openclaw.runtime import onboard
        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, {'OPENCLAW_NIX_MODE': '0'}), \
             patch('system_agent.readiness.readiness', return_value=(False, 'Disconnected')), \
             patch('runtimes.openclaw.runtime.invoke') as invoke:
            with self.assertRaises(ValueError):
                onboard(state)
            invoke.assert_not_called()

class FocusedAccountLoginTests(unittest.TestCase):
    def test_chatgpt_uses_device_code_without_general_onboarding(self):
        from unittest.mock import patch
        from runtimes.openclaw.runtime import connect_account
        with patch('system_agent.readiness.readiness', return_value=(True, 'Ready')), \
             patch('runtimes.openclaw.runtime.invoke', return_value=0) as invoke:
            self.assertEqual(connect_account('/run/fixture', 'chatgpt'), 0)
            invoke.assert_called_once_with('/run/fixture', ['models', 'auth', 'login', '--provider', 'openai', '--method', 'device-code', '--set-default'], None)

    def test_disconnection_blocks_focused_login(self):
        from unittest.mock import patch
        from runtimes.openclaw.runtime import connect_account
        with patch('system_agent.readiness.readiness', return_value=(False, 'Disconnected')), \
             patch('runtimes.openclaw.runtime.invoke') as invoke:
            with self.assertRaises(ValueError):
                connect_account('/run/fixture', 'chatgpt')
            invoke.assert_not_called()
