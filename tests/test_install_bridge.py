import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from system_agent import install_bridge as bridge
from system_agent.setup import Setup

class InstallBridgeTests(unittest.TestCase):
    def test_no_agent_operation_can_supply_approval_disk_or_shell(self):
        broker = bridge.Bridge('arch')
        for message in [
            {'operation':'execute', 'approval':'yes'},
            {'operation':'request', 'choices':{'disk':'/dev/sda'}, 'retry':False},
            {'operation':'request', 'choices':{}, 'retry':False, 'approve':'ERASE fixture'},
            {'operation':'request', 'choices':{'script':'touch /tmp/unsafe'}, 'retry':False},
        ]:
            with self.assertRaises(ValueError): broker.handle(message)
        self.assertIsNone(broker.take())

    def test_request_is_typed_idempotent_and_never_an_approval(self):
        broker = bridge.Bridge('arch')
        message = {'operation':'request', 'choices':{'hostname':'fixture'}, 'retry':False}
        with patch.object(bridge.time, 'monotonic', return_value=100):
            first = broker.handle(message)
        self.assertFalse(first['disk_erasure_approved'])
        with patch.object(bridge.time, 'monotonic', return_value=103):
            self.assertEqual(broker.take()['state'], 'reviewing')
            self.assertIsNone(broker.take())
        self.assertEqual(broker.handle(message)['id'], first['id'])
        broker.finish({'state':'cancelled'})
        self.assertEqual(broker.handle(message)['state'], 'cancelled')
        self.assertNotEqual(broker.handle({**message, 'retry':True})['id'], first['id'])

    def test_missing_payload_is_not_reported_as_permission_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'inputs.json'
            config.write_text(json.dumps({'payload':directory+'/target.sfs'}))
            with patch('adapters.arch.install.INPUTS', config):
                self.assertEqual(bridge.readiness('arch')['payload']['status'], 'missing-from-installer-view')
                (Path(directory)/'target.sfs').write_bytes(b'public fixture')
                self.assertEqual(bridge.readiness('arch')['payload']['status'], 'readable-by-installer')

    def test_bounded_protocol_rejects_extra_messages(self):
        for content in [b'x'*(bridge.LIMIT+1), b'{}\n{}\n']:
            first, second = socket.socketpair()
            with first, second:
                first.sendall(content)
                with self.assertRaises(ValueError): bridge.read_message(second)

    def test_console_uses_same_installer_and_reports_cancel_or_success(self):
        setup = Setup(True, 'arch'); setup.bridge = bridge.Bridge('arch')
        record = setup.bridge.handle({'operation':'request','choices':{'hostname':'fixture'},'retry':False})
        with patch.object(setup, 'install_choices', return_value=None) as install:
            setup.install_requested(record)
            install.assert_called_once_with(record['choices'])
        self.assertEqual(setup.bridge.record['state'], 'cancelled')
        with patch.object(setup, 'install_choices', return_value={'state':'installed-awaiting-reboot'}):
            setup.install_requested(record)
        self.assertEqual(setup.bridge.record['state'], 'installed-awaiting-reboot')

    def test_failed_execution_does_not_claim_disk_was_untouched(self):
        setup = Setup(True, 'arch'); setup.bridge = bridge.Bridge('arch')
        record = setup.bridge.handle({'operation':'request', 'choices':{}, 'retry':False})
        with patch.object(setup, 'install_choices', side_effect=OSError('fixture interrupted')):
            setup.install_requested(record)
        self.assertEqual(setup.bridge.record['state'], 'failed')
        self.assertIsNone(setup.bridge.record['disk_erasure_approved'])
        self.assertIn('unknown', setup.bridge.record['disk_changes'])


    def test_known_payload_failure_reports_pre_write_state(self):
        from system_agent.install_common import payload_issue
        setup = Setup(True, 'arch'); setup.bridge = bridge.Bridge('arch')
        record = setup.bridge.handle({'operation':'request', 'choices':{}, 'retry':False})
        with patch.object(setup, 'install_choices', side_effect=payload_issue('/fixture/target.sfs', 'missing')):
            setup.install_requested(record)
        result = setup.bridge.record
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(result['stage'], 'payload-check')
        self.assertEqual(result['disk_changes'], 'none-this-attempt')
        self.assertFalse(result['disk_erasure_approved'])
        self.assertNotEqual(setup.bridge.handle({'operation':'request', 'choices':{}, 'retry':True})['id'], record['id'])

    def test_export_failure_is_preserved_and_cannot_restart_erasure(self):
        import subprocess
        from system_agent.install_common import export_installed_pool
        setup = Setup(True, 'arch'); setup.bridge = bridge.Bridge('arch')
        record = setup.bridge.handle({'operation':'request', 'choices':{}, 'retry':False})
        failure = subprocess.CalledProcessError(1, ['zpool','export','csafixture'], stderr='pool is busy')
        with patch.object(setup, 'install_choices', side_effect=lambda _: export_installed_pool('csafixture')), \
                patch('system_agent.install_common.run', side_effect=failure):
            setup.install_requested(record)
        result = dict(setup.bridge.record)
        self.assertEqual(result['state'], 'needs-cleanup')
        self.assertEqual(result['disk_changes'], 'system-written')
        self.assertTrue(result['disk_erasure_approved'])
        self.assertFalse(result['installed_boot_verified'])
        self.assertEqual(result['diagnostic'], 'pool is busy')
        for retry in [False, True]:
            for choices in [{}, {'hostname':'different-choice'}]:
                self.assertEqual(setup.bridge.handle({'operation':'request', 'choices':choices, 'retry':retry}), result)
        self.assertIsNone(setup.bridge.take())
