import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from system_agent import deployment as d
from system_agent import handoff
from system_agent.install_bridge import Bridge

PLAN = dict(schema=1, distro='arch', disk='/dev/vda', target='/mnt/controlstack-custom',
            base='minimal', storage_action='erase', username='owner', storage_plan='EFI and portable ZFS',
            access_plan='Owner sudo; resident service without root', recovery_plan='USB and independent backup',
            requirements=[{'id':'login', 'description':'Custom company greeter'}])

class DeploymentTests(unittest.TestCase):
    def test_arbitrary_requirements_do_not_become_commands(self):
        plan = copy.deepcopy(PLAN)
        plan['requirements'][0]['description'] = 'A custom Quickshell greeter with company branding'
        self.assertEqual(d.validate_plan(plan), plan)
        for key in ('execute', 'password', 'approval'):
            with self.assertRaises(ValueError): d.validate_plan({**plan, key:'unsafe'})
        with self.assertRaises(ValueError): d.validate_plan({**plan, 'storage_plan':'bad\x1b[2J'})

    def test_no_target_escape_or_root_account(self):
        for change in [{'target':'/'}, {'target':'/mnt/../'}, {'disk':'/dev/vda;sh'}, {'username':'root'}]:
            with self.assertRaises(ValueError): d.validate_plan({**PLAN, **change})

    def test_requirements_must_be_unique(self):
        with self.assertRaises(ValueError): d.validate_plan({**PLAN, 'requirements':PLAN['requirements'] * 2})

    def test_custom_review_does_not_claim_disk_approval(self):
        broker = Bridge('arch')
        result = broker.handle({'operation':'custom', 'choices':PLAN, 'retry':False})
        self.assertEqual(result['mode'], 'custom')
        self.assertFalse(result['disk_erasure_approved'])
        self.assertEqual(result['state'], 'queued')

    def test_cancelled_review_preserves_disk(self):
        node = dict(name='/dev/vda', size=48*1024**3, serial='FIXTURE', wwn='', model='VM')
        with patch('system_agent.facts.discover', return_value={'phase':'live','distro_id':'arch','boot_id':'fixture'}), patch.object(d.os,'geteuid', return_value=0), patch('system_agent.install_common.disks', return_value=[node]), patch('system_agent.install_common.confirm_disk_erasure', return_value=None):
            result = d.review(PLAN)
        self.assertEqual(result['state'], 'cancelled')
        self.assertEqual(result['disk_changes'], 'none-by-review')

    def test_custom_instructions_replace_preset_and_progress_survives(self):
        with tempfile.TemporaryDirectory() as directory, patch('system_agent.facts.discover', return_value={'phase':'live'}):
            d.set_mode(directory, 'custom')
            instructions = (Path(directory)/'workspace/AGENTS.md').read_text()
            self.assertIn('You own the native installation', instructions)
            self.assertNotIn('Only record answers actually given', instructions)
            d.record_review(directory, {'mode':'custom','state':'approved','plan':PLAN})
            d.checkpoint(directory, 'writing', 'Partitioning finished; do not partition again')
            with self.assertRaises(ValueError): d.set_mode(directory, 'tested')
            self.assertEqual(d.read(directory,'custom-deployment.json')['state'], 'writing')
            with self.assertRaises(ValueError): d.checkpoint(directory, 'prepared-for-boot', 'claim')

    def test_target_absolute_symlinks_never_read_host_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'etc').mkdir(); (root/'etc/machine-id').write_text('target')
            (root/'identity').symlink_to('/etc/machine-id')
            self.assertEqual(d.target_file(root,'identity').read_text(), 'target')
            (root/'escape').symlink_to('../../etc/shadow')
            with self.assertRaises(ValueError): d.target_file(root,'escape')

    def test_empty_target_never_passes_boot_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            result = d.verify(directory, PLAN, run=lambda *a, **k: subprocess.CompletedProcess(a,1,'',''))
            self.assertFalse(result['boot_floor_passed'])
            self.assertFalse(result['installed_boot_verified'])

    def test_requirement_evidence_does_not_certify_boot(self):
        with tempfile.TemporaryDirectory() as directory:
            d.record_review(directory, {'mode':'custom','state':'approved','plan':PLAN})
            record=d.requirement(directory,'login','passed','Isolated VM logged into requested session')
            self.assertNotIn('installed_boot_verified', record)
            with self.assertRaises(ValueError): d.requirement(directory,'unknown','passed','claim')

    def test_module_search_follows_target_links_inside_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'modules/version').mkdir(parents=True)
            (root/'nix/store/fixture').mkdir(parents=True)
            (root/'nix/store/fixture/zfs.ko.zst').write_text('fixture')
            (root/'modules/version/extra').symlink_to('/nix/store/fixture')
            self.assertEqual(d.find_target_file(root, 'modules', 'zfs.ko'), root/'nix/store/fixture/zfs.ko.zst')

    def test_review_record_rejects_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                d.record_review(directory, {'mode':'custom', 'state':'approved', 'plan':PLAN, 'token':'not-real'})
            self.assertFalse((Path(directory)/'lifecycle/custom-deployment.json').exists())

    def test_boot_files_must_be_readable_by_resident_account(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); root.chmod(0o755)
            (root/'etc').mkdir(mode=0o755)
            identity=root/'etc/machine-id'; identity.write_text('a'*32); identity.chmod(0o444)
            self.assertTrue(d.readable_by(root,'etc/machine-id',65534,65534))
            identity.chmod(0o600)
            self.assertFalse(d.readable_by(root,'etc/machine-id',65534,65534))
            identity.chmod(0o444); (root/'etc').chmod(0o700)
            self.assertFalse(d.readable_by(root,'etc/machine-id',65534,65534))

    def test_encryption_secret_stays_in_private_ram_file(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)/'state'
            area = Path(directory)/'ram'; area.mkdir(mode=0o700)
            d.record_review(state, {'mode':'custom','state':'approved','plan':PLAN,'boot_id':'fixture'})
            with patch('system_agent.facts.discover', return_value={'phase':'live','boot_id':'fixture'}), patch.object(d.os,'geteuid',return_value=0), patch('system_agent.install_common.output',return_value='tmpfs'), patch('system_agent.install_common.secret_twice',return_value='fixture-only-passphrase'), patch('system_agent.setup.choose',return_value=2), patch.object(d,'private_dir',return_value=area):
                result=d.encryption_key_setup(state)
                key=area/'volume.key'
                self.assertEqual(key.read_bytes(),b'fixture-only-passphrase')
                self.assertEqual(key.stat().st_mode & 0o777,0o600)
                self.assertNotIn('fixture-only-passphrase',json.dumps(result))
                with self.assertRaises(ValueError): d.encryption_key_setup(state)

    def test_new_filesystem_handoff_still_requires_identity(self):
        record=dict(schema=2,target_distro='arch',installation_boot_id='12345678-1234-1234-1234-123456789abc',
                    target_machine_id='a'*32,root_fstype='ext4',root_identity='87654321-1234-1234-1234-123456789abc',installer_revision='b'*40)
        self.assertEqual(handoff.validate(record),record)
        with self.assertRaises(ValueError): handoff.validate({**record,'schema':1})
        with self.assertRaises(ValueError): handoff.validate({**record,'root_identity':'/dev/vda2'})

if __name__ == '__main__': unittest.main()
