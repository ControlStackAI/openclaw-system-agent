import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from system_agent import security_key as key
from system_agent.interview import interview
from adapters.arch import target

CHOICES = dict(hostname='fixture', username='owner', desktop='hyprland', timezone='UTC',
               keyboard='us', locale='en_US.UTF-8', encrypt=False, purpose='development', agent_name='OpenClaw')

class OwnerPolicyTests(unittest.TestCase):
    def test_saved_preferences_are_reviewed_without_reasking(self):
        calls = []
        result = interview(CHOICES, lambda q, opts: calls.append(q) or 1, lambda: 'UTC', lambda c: None)
        self.assertEqual(result['power_policy'], 'always-on')
        self.assertEqual(result['login_policy'], 'yubikey')
        self.assertEqual(calls, ['Would you like to change anything?'])

    def test_explicit_preferences_override_profile(self):
        result = interview({**CHOICES, 'power_policy': 'standard', 'login_policy': 'password'},
                           lambda q, opts: 1, lambda: 'UTC', lambda c: None)
        self.assertEqual(result['login_policy'], 'password')

    def test_enrollment_is_owner_bound_and_not_commands(self):
        value = {'mapping': 'owner:AA,BB,es256,+presence', 'serial': '1234'}
        self.assertEqual(key.validate_enrollment(value, 'owner'), value)
        for mapping in ['other:AA,BB,es256,+presence', 'owner:AA,BB,es256,+presence\nauth sufficient pam_permit.so', 'owner:AA']:
            with self.assertRaises(ValueError):
                key.validate_enrollment({**value, 'mapping': mapping}, 'owner')

    def test_missing_or_corrupt_password_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(key, 'STATE', Path(directory)):
            self.assertFalse(key.password_allowed())
            for text, expected in [('garbage', False), ('{"enabled":true}', True), ('{"enabled":"true"}', False)]:
                (Path(directory) / 'password-unlock.json').write_text(text)
                self.assertEqual(key.password_allowed(), expected)

    def test_policy_change_needs_unlocked_owner_key_touch_and_recheck(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(key, 'STATE', Path(directory)), \
             patch.object(key.os, 'geteuid', return_value=0), patch.dict(key.os.environ, {'SUDO_USER':'owner'}), \
             patch.object(key, 'policy', return_value={'owner':'owner'}), \
             patch.object(key, 'matching_keys', return_value={'fixture'}), patch.object(key, 'verify', return_value=True) as verify:
            with patch.object(key, 'unlocked', return_value=False):
                with self.assertRaises(PermissionError): key.set_password(False)
                verify.assert_not_called()
            with patch.object(key, 'unlocked', side_effect=[True, False]):
                with self.assertRaises(PermissionError): key.set_password(False)
            self.assertFalse((Path(directory) / 'password-unlock.json').exists())
            with patch.object(key, 'unlocked', return_value=True):
                key.set_password(False)
                self.assertFalse(key.password_allowed())
                key.set_password(True)
                self.assertTrue(key.password_allowed())

    def test_arch_target_masks_sleep_and_separates_login_from_unlock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target.configure(root, '/public-runtime', {**CHOICES, 'power_policy':'always-on', 'login_policy':'yubikey'})
            self.assertEqual((root / 'etc/systemd/system/suspend.target').readlink(), Path('/dev/null'))
            self.assertIn('HandleLidSwitch=ignore', (root / 'etc/systemd/logind.conf.d/90-controlstack.conf').read_text())
            self.assertNotIn('password-check', (root / 'etc/pam.d/sddm').read_text())
            self.assertIn('[success=ignore default=1]', (root / 'etc/pam.d/hyprlock').read_text())
            self.assertIn('password-check', (root / 'etc/pam.d/hyprlock').read_text())

    def test_removing_key_locks_once_and_inserting_does_not_unlock(self):
        with patch.object(key, 'policy', return_value={'owner':'owner'}), \
             patch.object(key, 'matching_keys', side_effect=[{'key'}, set(), set(), {'key'}, KeyboardInterrupt]), \
             patch.object(key.time, 'sleep'), patch.object(key, 'lock_owner') as lock:
            with self.assertRaises(KeyboardInterrupt): key.watch()
            lock.assert_called_once_with('owner')

    def test_other_desktop_requires_explicit_policy_correction(self):
        answers = iter([1, 1 + list(__import__('system_agent.interview', fromlist=['LABELS']).LABELS).index('login_policy') + 1, 2, 1])
        result = interview({**CHOICES, 'desktop':'gnome'}, lambda q, opts: next(answers), lambda: 'UTC', lambda c: None)
        self.assertEqual(result['login_policy'], 'password')

    def test_live_enrollment_verifies_before_target_account_exists(self):
        from types import SimpleNamespace
        outputs = [SimpleNamespace(stdout='fixture: Yubico key'), SimpleNamespace(stdout='new-owner:AA,BB,es256,+presence')]
        def assertion(path, owner):
            self.assertEqual(owner, 'live-root')
            self.assertEqual(path.read_text(), 'live-root:AA,BB,es256,+presence\n')
            return True
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(key, 'devices', return_value={'key':'123'}), \
             patch.object(key, 'run', side_effect=outputs), \
             patch.object(key.pwd, 'getpwuid', return_value=SimpleNamespace(pw_name='live-root')), \
             patch.object(key, 'verify', side_effect=assertion), \
             patch.object(key.tempfile, 'TemporaryDirectory', return_value=__import__('contextlib').nullcontext(directory)):
            value = key.enroll('new-owner')
            self.assertTrue(value['mapping'].startswith('new-owner:'))

    def test_lock_signal_only_targets_owner_sessions(self):
        from types import SimpleNamespace
        with patch.object(key, 'run', return_value=SimpleNamespace(stdout='1 1000 owner seat0\n2 1001 other seat1\n')), \
             patch.object(key.subprocess, 'run') as command:
            key.lock_owner('owner')
            command.assert_called_once_with(['loginctl', 'lock-session', '1'], check=False)
