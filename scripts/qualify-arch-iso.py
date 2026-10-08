#!/usr/bin/env python3
"""Arch live qualification only. Does not implement or claim target installation."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_support.images import digest
spec = importlib.util.spec_from_file_location("nixos_iso_test", Path(__file__).with_name("qualify-iso.py"))
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("iso", type=Path)
parser.add_argument("--uefi", action="store_true")
args = parser.parse_args()
iso = args.iso.resolve()
if not iso.is_file():
    parser.error("Use a regular-file ISO, never a host device")
area = Path(tempfile.mkdtemp(prefix="arch-live-", dir=shared.ROOT / ".build"))
guest = shared.Guest(iso, area, uefi=args.uefi, offline=True, live_login=True, memory=2048)
try:
    guest.command("grep '^ID=arch' /etc/os-release")
    guest.command("systemctl is-active controlstack-agent")
    guest.command("cat /dev/vcs1 | grep -F 'OpenClaw System Assistant'")
    guest.command("test $(stat -c %a /run/controlstack-agent) = 700")
    guest.command("test $(stat -c %a /run/controlstack-agent/openclaw.json) = 600")
    guest.command("modinfo -F version zfs | grep '^2.4.4'")
    guest.command("openclaw --version")
    guest.command("codex --version")
    guest.command("test -x /opt/codex/bin/codex-code-mode-host")
    guest.command("runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent system-agent inspect | grep '\"phase\": \"live\"'")
    guest.gateway_ready('/run/controlstack-agent')
    guest.process.sendline('system-agent-setup')
    guest.process.expect_exact('Choose a number:')
    guest.process.sendline('4')
    guest.process.expect_exact('no disk will be changed by this preview.')
    guest.process.expect_exact('Choose a number:')
    guest.process.sendline('1')
    guest.process.expect_exact('The connection is not ready yet.')
    guest.process.expect_exact('Choose a number:')
    guest.process.sendline('3')
    guest.process.expect_exact('Choose a number:')
    guest.process.sendline('8')
    guest.process.expect_exact('CS_READY> ')
    guest.qmp('screendump', {'filename':str(area/'console.png'), 'format':'png'})
    (area/'result.json').write_text(json.dumps({
        'iso_sha256':digest(iso), 'boot':'uefi' if args.uefi else 'bios',
        'live_console':True, 'offline_login_gate':True, 'private_ram_state':True,
        'gateway_health':True, 'disk_install':False, 'real_provider_login':False,
        'physical_hardware':False, 'yubikey_authentication':False}, indent=2)+'\n')
    print('Passed Arch live checks:', area)
finally:
    guest.close()
