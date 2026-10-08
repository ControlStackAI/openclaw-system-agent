import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from build_support import images
from system_agent import coding_login


class ImageLocks(unittest.TestCase):
    def lock(self):
        return images.resolve('nixos', epoch=1791392279)

    def test_checked_in_locks_match_reviewed_sources(self):
        manifest = images.source_manifest()
        for distro in ('arch', 'nixos'):
            lock = images.validate(json.loads((images.ROOT / 'images' / (distro + '.lock.json')).read_text()))
            self.assertEqual(lock['source'], manifest, 'Resolve checked-in locks after changing build sources')

    def test_actual_root_nixpkgs_not_transitive_dependency(self):
        lock = self.lock()
        self.assertEqual(images.plan(lock)['nixpkgs'], '151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            images.stage_source(root, lock['source'])
            images.prepare_flake(root, lock)
            pinned = json.loads((root / 'flake.lock').read_text())
            self.assertEqual(images.root_nixpkgs(pinned)['locked'], images.root_nixpkgs(lock['flake_lock'])['locked'])
            self.assertEqual(pinned['nodes']['nixpkgs']['locked'], lock['flake_lock']['nodes']['nixpkgs']['locked'])

    def test_mutated_source_never_builds(self):
        lock = self.lock()
        with tempfile.TemporaryDirectory() as temp, patch.object(images, 'source_manifest', return_value={}):
            with self.assertRaisesRegex(ValueError, 'changed'):
                images.stage_source(Path(temp), lock['source'])

    def test_unpinned_dependency_and_unsafe_manifest_rejected(self):
        lock = self.lock()
        bad = copy.deepcopy(lock)
        images.root_nixpkgs(bad['flake_lock'])['locked']['rev'] = 'latest'
        with self.assertRaisesRegex(ValueError, 'Unpinned'):
            images.validate(bad)
        bad = copy.deepcopy(lock)
        bad['source'] = {'../../home/auth.json': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            images.validate(bad)

    def test_unsupported_distro_and_cross_distro_options(self):
        lock = self.lock()
        lock['distro'] = 'ubuntu'
        with self.assertRaises(ValueError):
            images.validate(lock)
        with self.assertRaises(ValueError):
            images.resolve('nixos', arch_version='latest')
        with self.assertRaises(ValueError):
            images.resolve('arch', nixpkgs='latest')

    def test_build_cannot_overwrite_or_accept_foreign_iso(self):
        lock = self.lock()
        with tempfile.TemporaryDirectory() as temp, patch.object(images.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'exists'):
                images.build(lock, temp, 1)
            with self.assertRaisesRegex(ValueError, 'cached Arch'):
                images.build(lock, Path(temp)/'out', 1, Path('wrong.iso'))
            run.assert_not_called()

    def test_comparison_rehashes_artifacts_and_requires_same_lock(self):
        lock = self.lock()
        with tempfile.TemporaryDirectory() as temp:
            dirs = [Path(temp)/'one', Path(temp)/'two']
            for directory in dirs:
                directory.mkdir()
                (directory/'test.iso').write_bytes(b'image fixture')
                images.write_new(directory/'image.lock.json', lock)
                images.write_new(directory/'build-receipt.json', {
                    'image':'test.iso', 'sha256':images.digest(directory/'test.iso'),
                    'lock_sha256':hashlib.sha256(images.canonical(lock)).hexdigest()})
            self.assertTrue(images.compare(*dirs)['byte_identical'])
            self.assertFalse(images.compare(*dirs)['independent_builds_proven'])
            (dirs[1]/'test.iso').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'no longer'):
                images.compare(*dirs)


class CodingLogin(unittest.TestCase):
    def test_vendor_flows_only(self):
        self.assertEqual(coding_login.login_command('browser'), ['codex','login'])
        self.assertEqual(coding_login.login_command('device'), ['codex','login','--device-auth'])
        with self.assertRaises(ValueError):
            coding_login.login_command('yubikey-bypass')

    def test_root_cannot_inherit_owner_credentials(self):
        with patch.object(coding_login.os, 'geteuid', return_value=0), patch.object(coding_login.subprocess, 'run') as run:
            self.assertEqual(coding_login.main(), 1)
            run.assert_not_called()

    def test_saved_login_can_be_reused_without_new_flow(self):
        with patch.object(coding_login.os, 'geteuid', return_value=1000), \
             patch.object(coding_login.pwd, 'getpwuid') as account, \
             patch.object(coding_login.subprocess, 'run') as run, \
             patch.object(coding_login, 'choose', return_value=1):
            account.return_value.pw_name = 'owner'
            run.return_value.returncode = 0
            self.assertEqual(coding_login.main(), 0)
            run.assert_called_once_with(['codex', 'login', 'status'], capture_output=True, text=True)

class Interview(unittest.TestCase):
    def test_change_one_choice_preserves_all_other_answers(self):
        from system_agent.interview import interview, LABELS
        from system_agent.choices import DEFAULTS
        original = dict(DEFAULTS, purpose='development', desktop='hyprland')
        answers = iter([list(LABELS).index('desktop') + 2, 2, 1])
        result = interview(original, lambda *_: next(answers), lambda: 'UTC', lambda _: None)
        self.assertEqual(result, dict(original, desktop='plasma'))
        self.assertEqual(original['desktop'], 'hyprland')

    def test_main_use_is_typed_and_cannot_contain_a_secret_or_command(self):
        from system_agent.choices import validate_partial
        self.assertEqual(validate_partial({'purpose':'development'}), {'purpose':'development'})
        with self.assertRaises(ValueError):
            validate_partial({'purpose':'run sudo erase-disk'})

    def test_purpose_survives_partial_choice_channel_without_becoming_approval(self):
        from system_agent.choices import update, read
        from system_agent.state import private_dir
        with tempfile.TemporaryDirectory() as temp:
            private_dir(Path(temp)/'lifecycle')
            result = update(temp, 'purpose', 'development')
            self.assertEqual(read(temp), {'purpose':'development'})
            self.assertFalse(result['disk_erasure_approved'])
