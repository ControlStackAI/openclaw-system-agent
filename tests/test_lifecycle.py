import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from system_agent.facts import classify, verify_boot
from system_agent.state import initialize, default_config
from system_agent.handoff import validate, read_image_contract
from runtimes.openclaw.runtime import environment, onboard
from system_agent.policy import plan

ROOT = Path(__file__).resolve().parents[1]


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.expected = json.loads((ROOT / 'contracts/handoff-v1.example.json').read_text())
        self.facts = {'phase': 'installed-candidate', 'boot_id': 'new-boot',
                      'machine_id': self.expected['target_machine_id'], 'distro_id': 'nixos',
                      'root': {'fstype': 'zfs', 'source': 'rpool/ROOT/system', 'options': 'rw,relatime'}}

    def test_contexts_are_not_installed_boots(self):
        for flags, expected in [((True, False, True), 'chroot'), ((False, True, False), 'container'),
                                ((False, False, True), 'live'), ((None, False, False), 'unconfirmed')]:
            self.assertEqual(classify(chroot=flags[0], container=flags[1], live=flags[2], root_type='zfs'), expected)

    def test_reboot_requires_independent_matches(self):
        self.assertTrue(verify_boot(self.facts, self.expected)['installed_boot_verified'])
        for key, bad in [('phase', 'live'), ('boot_id', self.expected['installation_boot_id']),
                         ('machine_id', 'different'), ('distro_id', 'arch')]:
            altered = {**self.facts, key: bad}
            self.assertFalse(verify_boot(altered, self.expected)['installed_boot_verified'])

    def test_readonly_or_wrong_root_does_not_verify(self):
        for changes in ({'options': 'ro'}, {'source': 'other/ROOT/system'}, {'fstype': 'overlay'}):
            facts = {**self.facts, 'root': {**self.facts['root'], **changes}}
            self.assertFalse(verify_boot(facts, self.expected)['installed_boot_verified'])

    def test_no_installation_record_no_verification(self):
        expected = {**self.expected, 'installation_boot_id': ''}
        self.assertFalse(verify_boot(self.facts, expected)['installed_boot_verified'])

    def test_private_state_and_idempotent_initialization(self):
        state = self.path / 'state'
        initialize(state, ROOT / 'identity')
        token = (state / 'gateway-token').read_bytes()
        (state / 'workspace/IDENTITY.md').write_text('Existing owner identity')
        (state / 'workspace/USER.md').write_text('Owner chose no desktop; preserve my data')
        (state / 'session.sqlite').write_bytes(b'existing conversation bytes')
        config = (state / 'openclaw.json').read_bytes()
        initialize(state, ROOT / 'identity')
        self.assertEqual((state / 'gateway-token').read_bytes(), token)
        self.assertEqual((state / 'openclaw.json').read_bytes(), config)
        self.assertEqual((state / 'session.sqlite').read_bytes(), b'existing conversation bytes')
        self.assertEqual((state / 'workspace/IDENTITY.md').read_text(), 'Existing owner identity')
        self.assertEqual((state / 'workspace/USER.md').read_text(), 'Owner chose no desktop; preserve my data')
        self.assertEqual((state / 'workspace/USER.md').stat().st_mode & 0o777, 0o600)
        self.assertEqual(state.stat().st_mode & 0o777, 0o700)
        self.assertEqual((state / 'gateway-token').stat().st_mode & 0o777, 0o600)

    def test_symlink_state_rejected(self):
        (self.path / 'actual').mkdir()
        (self.path / 'link').symlink_to(self.path / 'actual')
        with self.assertRaises(ValueError):
            initialize(self.path / 'link/state', ROOT / 'identity')

    def test_unsafe_existing_token_rejected(self):
        state = self.path / 'state'
        state.mkdir()
        (state / 'gateway-token').write_text('fixture')
        (state / 'gateway-token').chmod(0o644)
        with self.assertRaises(ValueError):
            initialize(state, ROOT / 'identity')

    def test_no_operator_credentials_in_runtime(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'fixture-secret', 'ANTHROPIC_API_KEY': 'fixture-secret',
                                     'CODEX_HOME': '/operator/private', 'HOME': '/operator'}):
            env = environment(self.path)
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('CODEX_HOME', env)
        self.assertEqual(env['HOME'], str(self.path))

    def test_handoff_accepts_only_contract(self):
        self.assertEqual(validate(self.expected), self.expected)
        for changes in ({'credentials': 'fixture'}, {'target_distro': 'unknown'},
                        {'root_identity': 'rpool/../private'}, {'schema': True}):
            with self.assertRaises(ValueError):
                validate({**self.expected, **changes})

    def test_installer_image_contract(self):
        self.assertEqual(read_image_contract({'schema': 1, 'distro': 'arch', 'runtime': 'codex'})['distro'], 'arch')
        with self.assertRaises(ValueError):
            read_image_contract({'schema': 2, 'distro': 'arch', 'runtime': 'codex'})

    def test_nix_setup_refuses_mutation(self):
        with patch.dict(os.environ, {'OPENCLAW_NIX_MODE': '1'}), self.assertRaises(ValueError):
            onboard(self.path)

    def test_capabilities_fail_closed(self):
        with self.assertRaises(ValueError):
            plan('erase', '/dev/sda', self.facts, {})
        with self.assertRaises(ValueError):
            plan('snapshot', 'rpool/data', self.facts, {})
        p = plan('snapshot', 'rpool/data', self.facts, {'datasets': ['rpool/data']})
        self.assertFalse(p['executor_available'])
        self.assertFalse(p['changes_applied'])

    def test_boot_verification_does_not_claim_model(self):
        self.assertFalse(verify_boot(self.facts, self.expected)['model_response_verified'])

    def test_gateway_requires_private_token(self):
        config = default_config(self.path)
        self.assertEqual(config['gateway']['bind'], 'loopback')
        self.assertEqual(config['gateway']['auth']['token']['source'], 'file')
        self.assertFalse(config['tools']['elevated']['enabled'])


if __name__ == '__main__':
    unittest.main()

class AssistantNameTests(unittest.TestCase):
    def test_installed_name_before_first_service_start(self):
        from system_agent.profile import initialize_agent_name
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            initialize_agent_name(state, 'Luna')
            identity = state / 'workspace/IDENTITY.md'
            self.assertIn('Name: Luna', identity.read_text())
            self.assertIn('Role: Resident', identity.read_text())
            with identity.open('a') as stream:
                stream.write('\nOwner customization\n')
            initialize_agent_name(state, 'Nova')
            self.assertIn('Owner customization', identity.read_text())
            self.assertIn('Name: Nova', identity.read_text())
            self.assertEqual(identity.stat().st_mode & 0o777, 0o600)

    def test_name_is_validated_and_preserves_identity_role(self):
        from system_agent.profile import name_agent, validate_agent_name
        from system_agent.state import initialize
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            initialize(state, Path(__file__).resolve().parents[1] / 'identity')
            name_agent(state, 'Luna')
            identity = (state / 'workspace/IDENTITY.md').read_text()
            self.assertIn('Name: Luna', identity)
            self.assertIn('Role: Resident', identity)
            self.assertEqual((state / 'workspace/IDENTITY.md').stat().st_mode & 0o777, 0o600)
        for name in ['../../bad', 'Name\nInstruction', 'x'*49]:
            with self.assertRaises(ValueError): validate_agent_name(name)
