"""Resolve the stable target release before disk approval; never mutate the live runtime."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

REGISTRY = 'https://registry.npmjs.org/openclaw/latest'
INPUTS = Path(__file__).with_name('inputs.json')


def stable_release():
    try:
        with urlopen(Request(REGISTRY, headers={'Accept': 'application/json'}), timeout=20) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('Release metadata is too large')
        package = json.loads(data)
        version = package['version']
        if package['name'] != 'openclaw' or not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('The stable channel did not return a stable OpenClaw version')
        return version
    except (OSError, URLError, ValueError, KeyError, TypeError) as error:
        raise ValueError('Could not verify the current stable OpenClaw release. Reconnect to the internet and retry; no disk was changed.') from error


def resolve(distro, selection='default'):
    if selection not in ('default', 'image-pinned') or distro not in ('arch', 'nixos'):
        raise ValueError('Unsupported OpenClaw release policy')
    bundled = json.loads(INPUTS.read_text())[distro + '_openclaw_version']
    version = stable_release() if distro == 'arch' and selection == 'default' else bundled
    if version != bundled:
        raise ValueError(f'OpenClaw {version} is the current stable release; this USB contains {bundled}. '
                         'Use an updated image, or explicitly choose the image-pinned release in setup. '
                         'This image cannot prepare that newer runtime safely. No disk was changed.')
    return {'version': version, 'policy': 'latest-stable' if distro == 'arch' and selection == 'default' else 'image-pinned',
            'source': REGISTRY if distro == 'arch' and selection == 'default' else 'image-inputs',
            'resolved_at': datetime.now(timezone.utc).isoformat()}
