#!/usr/bin/env python3
"""Custom-mode native console installation, using only fresh file-backed VM disks."""
import argparse
import hashlib
import base64
import io
import zipfile
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
    parser.add_argument('--handoff-recovery', action='store_true')
    parser.add_argument('--public-package-cache',type=Path)
    args=parser.parse_args(); iso=args.iso.resolve(); area=ROOT/'.build/iso-test'/('custom-'+args.distro+('-handoff-recovery' if args.handoff_recovery else ''))
    area.mkdir(parents=True,exist_ok=True)
    if (area/'target.qcow2').exists(): raise ValueError('Archive/remove the previous disposable test disk before a new case')
    guest=Guest(iso,area,uefi=True,memory=8192,live_login=args.distro=='arch',public_package_cache=args.public_package_cache)
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
        if args.handoff_recovery:
            plan['requirements'] += [dict(id='actual-login',description='Verify actual installed console login after reboot'), dict(id='optional-app',description='Optional application work requested for later')]
        guest.put('/tmp/custom-plan.json',json.dumps(plan)); guest.command('chmod 644 /tmp/custom-plan.json'); guest.command(live+'system-agent deployment-review /tmp/custom-plan.json')
        answer('Type ERASE CONTROLSTACK-VM-ONLY','ERASE TYPO'); answer('Try the disk confirmation again?','1'); answer('Type ERASE CONTROLSTACK-VM-ONLY','ERASE CONTROLSTACK-VM-ONLY')
        guest.command('timeout 120 bash -c '+shlex.quote('until '+live+'system-agent deployment-status | grep -q \'"state": "approved"\'; do sleep 1; done'),timeout=130)
        guest.command(live+'system-agent deployment-checkpoint preparing '+shlex.quote('Native console fixture; no desktop requested'))
        if args.public_package_cache:
            guest.command('mkdir /run/public-package-cache; mount -t 9p -o trans=virtio,version=9p2000.L,ro cspkg /run/public-package-cache; export CONTROLSTACK_TEST_PACKAGE_CACHE=/run/public-package-cache')
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
        if args.handoff_recovery:
            guest.command(live+'system-agent deployment-requirement actual-login pending '+shlex.quote('Requires the installed system to boot'))
            guest.command(live+'system-agent deployment-requirement optional-app pending '+shlex.quote('Owner wants this optional work later'))
            guest.command("! system-agent --state /run/controlstack-agent deployment-finalize >/tmp/old-finalizer.log 2>&1; grep -q 'Requested features still need verification' /tmp/old-finalizer.log; test ! -e /mnt/controlstack-custom/var/lib/controlstack-agent/lifecycle/installation.json")
            guest.command('cp /run/controlstack-agent/lifecycle/custom-deployment.json /tmp/before-recovery.json; sha256sum /mnt/controlstack-custom/etc/shadow >/tmp/shadow-before-recovery')
            bundle=io.BytesIO(); recovery_files={}
            with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
                for source in sorted((ROOT/'system_agent').glob('*.py')):
                    archive.write(source,str(source.relative_to(ROOT)))
                    recovery_files[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
                archive.write(ROOT/'scripts/recover-custom-handoff.py','scripts/recover-custom-handoff.py')
                recovery_files['scripts/recover-custom-handoff.py']=hashlib.sha256((ROOT/'scripts/recover-custom-handoff.py').read_bytes()).hexdigest()
            payload=bundle.getvalue()
            guest.put('/tmp/handoff-fix.b64',base64.b64encode(payload).decode())
            guest.command("python3 -c "+shlex.quote("import base64,io,zipfile; zipfile.ZipFile(io.BytesIO(base64.b64decode(open('/tmp/handoff-fix.b64').read()))).extractall('/run/handoff-fix')"))
            guest.command('openvt -c 8 -s -w -- python3 /run/handoff-fix/scripts/recover-custom-handoff.py >/tmp/handoff-console.log 2>&1 &')
            def recovery_answer(prompt, value):
                guest.command('timeout 90 bash -c '+shlex.quote('until grep -Fq '+shlex.quote(prompt)+' /dev/vcs8; do sleep 1; done'),timeout=100)
                guest.type_console(value)
            recovery_answer('Verify actual installed console login','2')
            recovery_answer('Optional application work','3')
            recovery_answer('Save this first-boot review','2')
            guest.command("timeout 90 bash -c " + shlex.quote("until grep -q prepared-for-boot /run/controlstack-agent/lifecycle/custom-deployment.json; do sleep 1; done"),timeout=100)
            guest.qmp('screendump',{'filename':str(area/'first-boot-review.png'),'format':'png'})
            recovery_answer('Return to your agent','')
            guest.command('sha256sum -c /tmp/shadow-before-recovery')
            guest.put('/tmp/check-recovery.py', '''import json
from pathlib import Path
before=json.loads(Path('/tmp/before-recovery.json').read_text())
after=json.loads(Path('/run/controlstack-agent/lifecycle/custom-deployment.json').read_text())
for key in ('plan','plan_digest','disk','boot_id','requirement_results'): assert before[key]==after[key],key
assert after['installed_boot_verified'] is False
assert after['requested_features_verified'] is False
assert [(t['id'],t['when'],t['status']) for t in after['first_boot_tasks']]==[('actual-login','post-boot','pending'),('optional-app','deferred','pending')]
''')
            guest.command('python3 /tmp/check-recovery.py')
        else:
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
        if args.handoff_recovery:
            guest.command("grep 'post-boot' /var/lib/controlstack-agent/workspace/USER.md; grep 'deferred' /var/lib/controlstack-agent/workspace/USER.md")
            guest.command("python3 -c "+shlex.quote("import json; r=json.load(open('/var/lib/controlstack-agent/lifecycle/custom-deployment.json')); assert not r['requested_features_verified']; assert all(t['status']=='pending' for t in r['first_boot_tasks'])"))
        guest.qmp('screendump',{'filename':str(area/'installed.png'),'format':'png'})
        result=dict(schema=1,distro=args.distro,iso_sha256=hashlib.file_digest(iso.open('rb'),'sha256').hexdigest(),native_minimal_install=True,custom_local_review=True,custom_instructions_reached_provider=True,confirmation_typo_retried=True,protected_account_setup=True,independent_installed_boot=True,filesystem='ext4',real_provider=False,physical_key=False,physical_disks_attached=False)
        if args.handoff_recovery:
            result.update(handoff_recovery=True,recovery_bundle_sha256=hashlib.sha256(payload).hexdigest(),recovery_files_sha256=recovery_files,old_finalizer_blocked=True,public_package_cache_used=bool(args.public_package_cache),local_pending_review=True,approval_and_evidence_preserved=True,password_preserved=True,pending_tasks_survived_boot=True,iso_modified=False)
        (area/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally: guest.close()
    (area/'target.qcow2').unlink(); (area/'extra-usb.raw').unlink()

if __name__=='__main__': main()
