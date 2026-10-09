#!/usr/bin/env python3
"""Custom-mode native console installation, using only fresh file-backed VM disks."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import time
import pexpect

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('iso_test', ROOT/'scripts/qualify-iso.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
Guest=module.Guest


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('iso',type=Path); parser.add_argument('--distro',choices=['arch','nixos'],required=True)
    args=parser.parse_args(); iso=args.iso.resolve(); area=ROOT/'.build/iso-test'/('custom-'+args.distro)
    area.mkdir(parents=True,exist_ok=True)
    if (area/'target.qcow2').exists(): raise ValueError('Archive/remove the previous disposable test disk before a new case')
    guest=Guest(iso,area,uefi=True,memory=8192,live_login=args.distro=='arch')
    live='runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent OPENCLAW_CONFIG_PATH=/run/controlstack-agent/openclaw.json OPENCLAW_NIX_MODE=0 '
    def answer(prompt,value,timeout=120):
        guest.command('timeout '+str(timeout)+' bash -c '+shlex.quote('until grep -Fq '+shlex.quote(prompt)+' /dev/vcs1; do sleep 1; done'),timeout=timeout+10)
        guest.type_console(value); time.sleep(.5)
    try:
        answer('What would you like to do?','8'); answer('How would you like to deploy','2')
        guest.command(live+'system-agent deployment-mode | grep custom')
        guest.put('/tmp/provider.py',(ROOT/'tests/fixture_provider.py').read_text())
        guest.command('python3 /tmp/provider.py >/tmp/provider.log 2>&1 &')
        guest.command(live+'openclaw onboard --non-interactive --accept-risk --mode local --skip-daemon --skip-health --skip-ui --skip-skills --skip-channels --skip-bootstrap --skip-hooks --skip-search --auth-choice custom-api-key --custom-base-url http://127.0.0.1:18080/v1 --custom-model-id fixture-model --custom-provider-id fixture --custom-compatibility openai --custom-api-key non-secret-vm-fixture',timeout=180)
        guest.command(live+'system-agent local-policy'); guest.command('systemctl restart controlstack-agent'); guest.gateway_ready('/run/controlstack-agent')
        answer('What would you like to do?','2')
        guest.command("timeout 120 bash -c \"until pgrep -u controlstack-agent -f '[s]ystem_agent chat'; do sleep 1; done\"",timeout=130)
        guest.command("timeout 90 bash -c \"until grep -q 'You own the native installation' /tmp/fixture-request.json 2>/dev/null; do sleep 1; done\"",timeout=100)
        plan=dict(schema=1,distro=args.distro,disk='/dev/vda',target='/mnt/controlstack-custom',base='minimal',storage_action='erase',username='owner',storage_plan='VM fixture: replace only the disposable disk with EFI and ext4, explicitly selected instead of ZFS',access_plan='Owner sudo; resident private state with no root grant',recovery_plan='Keep ISO and saved native config',requirements=[dict(id='console',description='Minimal console system with resident OpenClaw and no display manager')])
        guest.put('/tmp/custom-plan.json',json.dumps(plan)); guest.command('chmod 644 /tmp/custom-plan.json'); guest.command(live+'system-agent deployment-review /tmp/custom-plan.json')
        answer('Type ERASE CONTROLSTACK-VM-ONLY','ERASE TYPO'); answer('Try the disk confirmation again?','1'); answer('Type ERASE CONTROLSTACK-VM-ONLY','ERASE CONTROLSTACK-VM-ONLY')
        guest.command('timeout 120 bash -c '+shlex.quote('until '+live+'system-agent deployment-status | grep -q \'"state": "approved"\'; do sleep 1; done'),timeout=130)
        guest.command(live+'system-agent deployment-checkpoint preparing '+shlex.quote('Native console fixture; no desktop requested'))
        guest.put('/tmp/custom-native.py',(ROOT/'tests/custom-native.py').read_text())
        # Import the exact shipped adapter code, never a modified guest implementation.
        guest.command('core=$(readlink -f $(command -v system-agent)); export PYTHONPATH=$(dirname $(dirname "$core"))/lib/system-agent; python3 /tmp/custom-native.py '+args.distro,timeout=1800)
        guest.command(live+'system-agent deployment-checkpoint configuring '+shlex.quote('Native files and bootloader installed; account password remains pending'))
        guest.command(live+'system-agent deployment-account')
        answer('Set the local password','1'); answer('Password for your local account','vmonlytestpassword'); answer('Enter it again:','vmonlytestpassword'); answer('Use a YubiKey','1')
        guest.command('timeout 120 bash -c '+shlex.quote('until '+live+'system-agent install-status | grep -q account-ready; do sleep 1; done'),timeout=130)
        guest.command('system-agent --state /run/controlstack-agent deployment-verify',timeout=60)
        guest.command('test ! -e /mnt/controlstack-custom/etc/systemd/system/display-manager.service')
        guest.command(live+'system-agent deployment-requirement console passed '+shlex.quote('Native package/configuration installed; console/PAM and resident service present; independent boot is next'))
        guest.command('system-agent --state /run/controlstack-agent deployment-finalize')
        guest.command('test ! -e /mnt/controlstack-custom/var/lib/controlstack-agent/openclaw.json; sync; umount -R /mnt/controlstack-custom')
        guest.process.sendline('poweroff'); guest.process.expect(pexpect.EOF,timeout=60)
    finally: guest.close()
    guest=Guest(iso,area,uefi=True,installed=True,memory=8192)
    try:
        guest.command('findmnt -n -o FSTYPE / | grep -x ext4')
        guest.command('systemctl start controlstack-agent-boot-check; systemctl is-active controlstack-agent controlstack-agent-boot-check',timeout=180)
        guest.command("grep '\"installed_boot_verified\": true' /var/lib/controlstack-agent/lifecycle/boot-verification.json")
        guest.command("grep 'Minimal console system' /var/lib/controlstack-agent/workspace/USER.md")
        guest.command('test ! -e /etc/systemd/system/display-manager.service; ! runuser -u controlstack-agent -- sudo -n id -u')
        guest.qmp('screendump',{'filename':str(area/'installed.png'),'format':'png'})
        result=dict(schema=1,distro=args.distro,iso_sha256=hashlib.file_digest(iso.open('rb'),'sha256').hexdigest(),native_minimal_install=True,custom_local_review=True,custom_instructions_reached_provider=True,confirmation_typo_retried=True,protected_account_setup=True,independent_installed_boot=True,filesystem='ext4',real_provider=False,physical_key=False,physical_disks_attached=False)
        (area/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally: guest.close()
    (area/'target.qcow2').unlink(); (area/'extra-usb.raw').unlink()

if __name__=='__main__': main()
