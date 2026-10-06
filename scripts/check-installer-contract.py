#!/usr/bin/env python3
"""Read pinned public installer contracts; never mutate its checkout."""
import argparse
import subprocess
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_agent.handoff import read_image_contract
lock = json.loads((Path(__file__).resolve().parents[1] / 'contracts/installer.lock.json').read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--checkout', type=Path)
args = parser.parse_args()
for name, expected in lock['files'].items():
    if args.checkout:
        data = subprocess.check_output(['git', '-C', str(args.checkout), 'show', f"{lock['revision']}:{name}"])
    else:
        data = urllib.request.urlopen(f"https://raw.githubusercontent.com/ControlStackAI/agent-installer/{lock['revision']}/{name}", timeout=30).read()
    assert hashlib.sha256(data).hexdigest() == expected, name
    if name.startswith('profiles/'):
        profile = json.loads(data)
        assert profile['schema'] == 1 and profile['default_filesystem'] == 'zfs'
        read_image_contract({'schema': 1, 'distro': profile['id'], 'runtime': 'codex'})
print('Pinned installer contract checks passed; resident handoff emission is not yet integrated.')
