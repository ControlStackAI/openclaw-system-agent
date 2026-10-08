import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from system_agent.access import live_system_access, configure_live_tools


class LiveAccessTests(unittest.TestCase):
    def test_live_grant_requires_image_marker_and_protected_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = root / 'etc/controlstack-agent/live-system-access.json'
            contract.parent.mkdir(parents=True)
            contract.write_text('{"schema":1,"access":"sudo-full"}')
            self.assertFalse(live_system_access(root))
            marker = root / 'etc/agent-installer/live-image'
            marker.parent.mkdir(); marker.write_text('arch')
            real_stat = Path.stat
            for uid, mode, expected in [(0, 0o100644, True), (1000, 0o100644, False), (0, 0o100666, False)]:
                def stat(path, *args, **kwargs):
                    if path == contract:
                        return SimpleNamespace(st_uid=uid, st_mode=mode)
                    return real_stat(path, *args, **kwargs)
                with patch.object(Path, 'stat', stat):
                    self.assertEqual(live_system_access(root), expected)
            contract.write_text('invalid')
            self.assertFalse(live_system_access(root))

    def test_runtime_policy_changes_only_live_images(self):
        config = {'tools': {'allow': ['exec']}, 'agents': {'defaults': {'model': {'primary': 'fixture/test'}}}}
        before = json.loads(json.dumps(config))
        with patch('system_agent.access.live_system_access', return_value=False):
            configure_live_tools(config)
        self.assertEqual(config, before)
        with patch('system_agent.access.live_system_access', return_value=True):
            configure_live_tools(config)
        self.assertEqual(config['tools']['exec'], {'host': 'gateway', 'mode': 'full'})
        self.assertEqual(config['agents']['defaults']['sandbox'], {'mode': 'off'})
        self.assertEqual(config['agents']['defaults']['model'], before['agents']['defaults']['model'])
