"""Image-owned access contract, distinct from observed privilege availability."""
import json
from pathlib import Path
import stat


def live_system_access(root=Path('/')):
    path = root / 'etc/controlstack-agent/live-system-access.json'
    if not (root / 'etc/agent-installer/live-image').is_file():
        return False
    try:
        info = path.stat()
        return (stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
                and json.loads(path.read_text()) == {'schema': 1, 'access': 'sudo-full'})
    except (OSError, ValueError):
        return False


def configure_live_tools(config):
    if live_system_access():
        config.setdefault('agents', {}).setdefault('defaults', {})['sandbox'] = {'mode': 'off'}
        config.setdefault('tools', {})['exec'] = {'host': 'gateway', 'mode': 'full'}
