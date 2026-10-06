import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from adapters.nixos.install import validate_choices, eligible, render_target, install
from system_agent.state import initialize

CHOICES = dict(hostname="my-computer", username="owner", desktop="none", timezone="UTC",
               keyboard="us", locale="en_US.UTF-8", encrypt=False)


class Installation(unittest.TestCase):
    def test_choices_reject_injection_unknown_fields_and_implicit_encryption(self):
        self.assertEqual(validate_choices(CHOICES), CHOICES)
        for values in ({"username": "root"}, {"hostname": '${builtins.readFile "/secret"}'},
                       {"desktop": "unknown"}, {"encrypt": "no"}, {"timezone": "../../etc/passwd"},
                       {"api_key": "fixture"}):
            with self.assertRaises(ValueError):
                validate_choices({**CHOICES, **values})

    def test_in_use_disks_and_unidentified_disks_are_excluded(self):
        node = dict(name="/dev/fixture-target", type="disk", size=64 * 1024**3, serial="fixture",
                    ro=False, mountpoints=[None])
        self.assertTrue(eligible(node))
        for changes in ({"ro": True}, {"serial": None}, {"type": "part"}, {"size": 1024},
                        {"mountpoints": ["/run/iso"]}, {"children": [{"name": "/dev/fixture-part", "mountpoints": ["/"]}]}):
            self.assertFalse(eligible({**node, **changes}))
        self.assertFalse(eligible(node, [node["name"]]))

    def test_no_approval_no_commands(self):
        plan = {"disk": {"serial": "fixture", "wwn": None}}
        with patch("adapters.nixos.install.run") as run:
            with self.assertRaises(ValueError):
                install(plan, "yes", "non-secret-fixture")
            run.assert_not_called()

    def test_seed_config_is_created_once_not_replaced_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.json"
            seed.write_text(json.dumps({"test": "initial"}))
            initialize(root / "state", root / "identity", seed_config=seed)
            seed.write_text(json.dumps({"test": "changed"}))
            initialize(root / "state", root / "identity", seed_config=seed)
            self.assertEqual(json.loads((root / "state/openclaw.json").read_text()), {"test": "initial"})
