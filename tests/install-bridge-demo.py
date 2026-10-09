"""Fixture chat client and disk-free installer, with the real root console bridge."""
import contextlib
from pathlib import Path
import subprocess
import time
from system_agent.setup import Setup, choose
from system_agent.tui import Interface
from system_agent.install_bridge import Bridge

class Demo(Setup):
    def connect(self): return True
    def agent(self, *args, **kwargs):
        if args[0] == 'health': return subprocess.CompletedProcess(args, 0)
        return super().agent(*args, **kwargs)
    def install_choices(self, choices):
        Path('/run/review-reached').write_text(str(choices))
        answer = choose('Approve the disposable installation fixture?', ['Cancel without disk changes', 'Approve fixture only'])
        if answer == 1: return None
        Path('/run/fixture-approved').write_text('local UI approval only')
        if Path('/run/fixture-export-failure').exists():
            from unittest.mock import patch
            from system_agent.install_common import export_installed_pool
            failure = subprocess.CalledProcessError(1, ['zpool', 'export', 'csafixture'], stderr='pool is busy: synthetic namespace holder')
            with patch('system_agent.install_common.run', side_effect=failure):
                export_installed_pool('csafixture')

        return {'state':'installed-awaiting-reboot', 'disk_erasure_approved':True, 'message':'Fixture only; no disk was touched.'}

setup = Demo(True, 'nixos')
with Bridge('nixos') as bridge, Interface(True, 'nixos'):
    setup.bridge = bridge
    setup.chat()
