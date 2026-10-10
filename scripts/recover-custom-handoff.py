#!/usr/bin/env python3
"""Run reviewed handoff code on an existing live installation, without reinstalling.

Launch on a free local console with openvt, from an immutable reviewed checkout.
No package installation, disk formatting, account enrollment or reboot occurs here.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from system_agent import deployment, tui
from system_agent.facts import discover


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plain', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0 or not sys.stdin.isatty():
        parser.error('Open this helper on a local root console; do not pipe approvals into it.')
    facts = discover()
    if facts['phase'] != 'live' or facts['distro_id'] not in ('arch', 'nixos'):
        parser.error('Recovery is only supported on an Arch or NixOS live USB.')
    state = Path('/run/controlstack-agent')
    if not args.plain and not os.environ.get('CONTROLSTACK_TUI') and not shutil.which('controlstack-tui'):
        # Existing images expose the UI through the setup wrapper, not PATH.
        # Read its immutable public Nix path; never source a shell wrapper.
        wrapper = shutil.which('system-agent-setup')
        value = Path(wrapper).read_text() if wrapper else ''
        match = re.search(r'/nix/store/[a-z0-9]{32}-controlstack-tui-[^/\s\x27\x22]+/bin/controlstack-tui', value)
        if not match or not os.access(match[0], os.X_OK):
            parser.error('Cannot locate the packaged Ratatui UI. Use --plain on the local console.')
        os.environ['CONTROLSTACK_TUI'] = match[0]
    code = 1
    with contextlib.nullcontext() if args.plain else tui.Interface(True, facts['distro_id']):
        try:
            if tui.active:
                tui.active.context('First-boot handoff recovery')
            result = deployment.first_boot_review(state)
            if result['state'] == 'first-boot-reviewed':
                result = deployment.finalize(state)
                code = 0
                message = ('First-boot handoff saved. Untested features remain pending. Return to your agent '
                           'to sync and safely unmount/export the reviewed target before reboot. This helper has not rebooted.')
            else:
                message = result['message']
            print(json.dumps(result, indent=2), flush=True)
        except (OSError, ValueError, KeyError, EOFError, KeyboardInterrupt, subprocess.SubprocessError, tui.Cancelled) as error:
            message = 'Handoff did not finish: ' + (str(error) or 'Review cancelled') + '. Preserve the installation and inspect the current record before retrying.'
        print(message, flush=True)
        try:
            if tui.active:
                tui.active.info('Return to your agent', message)
            else:
                input('Press Enter to return to your agent. ')
        except (EOFError, KeyboardInterrupt, tui.Cancelled):
            pass
    return code


if __name__ == '__main__':
    raise SystemExit(main())
