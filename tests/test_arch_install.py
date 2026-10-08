import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from adapters.arch import install, target
from system_agent.interview import interview


class ArchInstallation(unittest.TestCase):
    def test_cancel_and_bad_secret_never_touch_disks(self):
        plan = {'disk': {'serial': 'fixture', 'wwn': None}, 'choices': {'encrypt': True}}
        with patch.object(install, 'run') as command:
            for confirmation, key in [('yes', 'fixture-password'), ('ERASE fixture', 'bad')]:
                with self.assertRaises(ValueError):
                    install.install(plan, confirmation, 'non-secret-fixture', key)
            command.assert_not_called()

    def test_changed_payload_is_rejected_before_preparing_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'target.sfs'
            payload.write_bytes(b'corrupted fixture')
            inputs = root / 'inputs.json'
            inputs.write_text(json.dumps({'payload': str(payload), 'sha256': '0' * 64}))
            choices = dict(hostname='fixture', username='owner', desktop='hyprland',
                           keyboard='us', locale='en_US.UTF-8', timezone='UTC', encrypt=False)
            with patch.object(install, 'INPUTS', inputs), patch.object(install, 'check_context', return_value={}), patch.object(install, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'integrity'):
                    install.prepare({}, choices)
                command.assert_not_called()

    def test_unavailable_saved_desktop_is_reasked(self):
        choices = dict(hostname='fixture', username='owner', desktop='gnome', purpose='development',
                       keyboard='us', locale='en_US.UTF-8', timezone='UTC', encrypt=False)
        prompts = []
        def choose(question, options):
            prompts.append((question, options))
            return 1
        result = interview(choices, choose, lambda: 'UTC', lambda x: None, desktops=('hyprland', 'none'))
        self.assertEqual(result['desktop'], 'hyprland')
        self.assertEqual(len(prompts[0][1]), 2)
        self.assertNotIn('GNOME', ' '.join(prompts[0][1]))

    def test_public_target_directories_ignore_private_setup_umask(self):
        choices = dict(hostname='fixture', username='owner', desktop='hyprland',
                       keyboard='us', locale='en_US.UTF-8', timezone='UTC', encrypt=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = os.umask(0o077)
            try:
                target.configure(root, '/public-runtime', choices)
                restored = os.umask(0o077)
                self.assertEqual(restored, 0o077)
            finally:
                os.umask(previous)
            for name in ('usr/share/controlstack', 'etc/xdg/nvim',
                         'etc/systemd/user/graphical-session.target.wants',
                         'etc/controlstack-agent'):
                self.assertEqual((root / name).stat().st_mode & 0o777, 0o755, name)
            self.assertEqual((root / 'etc/sudoers.d/controlstack').stat().st_mode & 0o777, 0o440)
