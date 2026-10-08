import io
import json
import unittest
from unittest.mock import patch
from runtimes.openclaw import release_policy as release

class ReleasePolicyTests(unittest.TestCase):
    def test_arch_checks_stable_and_records_selected_version(self):
        version = json.loads(release.INPUTS.read_text())['arch_openclaw_version']
        with patch.object(release, 'stable_release', return_value=version) as fetch:
            result = release.resolve('arch')
            fetch.assert_called_once()
            self.assertEqual(result['version'], version)
            self.assertEqual(result['policy'], 'latest-stable')

    def test_old_image_never_silently_claims_latest(self):
        with patch.object(release, 'stable_release', return_value='9999.1.1'):
            with self.assertRaisesRegex(ValueError, 'No disk was changed'):
                release.resolve('arch')

    def test_nixos_and_explicit_pin_never_resolve_mutable_tag(self):
        with patch.object(release, 'stable_release') as fetch:
            self.assertEqual(release.resolve('nixos')['policy'], 'image-pinned')
            self.assertEqual(release.resolve('arch', 'image-pinned')['policy'], 'image-pinned')
            fetch.assert_not_called()

    def test_prereleases_and_wrong_package_are_rejected(self):
        for name, version in [('openclaw', '2026.9.9-beta.1'), ('other', '2026.9.8')]:
            with patch.object(release, 'urlopen', return_value=io.BytesIO(json.dumps({'name': name, 'version': version}).encode())):
                with self.assertRaises(ValueError): release.stable_release()
