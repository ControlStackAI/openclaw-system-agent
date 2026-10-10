"""Custom deployment records and verification; native distro tools do the install.

Records are data, never executable hooks. Root review happens on the live console.
This is a workflow over the deliberately privileged live agent, not a sandbox.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from .state import write_observation, create_private, private_dir

MODES = ('tested', 'custom')
PLAN_FIELDS = {'schema', 'distro', 'disk', 'storage_action', 'storage_plan', 'requirements',
               'access_plan', 'recovery_plan', 'username', 'target', 'base'}


def text(value, name, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f'{name} must be non-empty printable text (at most {limit} characters)')
    return value


def validate_plan(value):
    if not isinstance(value, dict) or set(value) != PLAN_FIELDS or type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('Custom plan fields do not match schema 1; see docs/custom-deployment.md')
    if len(json.dumps(value).encode()) > 6000:
        raise ValueError('Keep the reviewed plan below 6000 bytes; store detailed configuration separately')
    if value['distro'] not in ('arch', 'nixos') or value['storage_action'] not in ('erase', 'preserve') or value['base'] not in ('minimal', 'preset'):
        raise ValueError('Invalid distribution, storage action or starting point')
    if not isinstance(value['disk'], str) or not re.fullmatch(r'/dev/[A-Za-z0-9_-]+', value['disk']):
        raise ValueError('Select a whole disk by its current /dev path; review binds its serial and size')
    if value['target'] != '/mnt/controlstack-custom':
        raise ValueError('Use /mnt/controlstack-custom as the target mount point')
    if not isinstance(value['username'], str) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', value['username']) or value['username'] in ('root', 'controlstack-agent'):
        raise ValueError('Choose a normal owner account name')
    for key in ('storage_plan', 'access_plan', 'recovery_plan'):
        text(value[key], key)
    requirements = value['requirements']
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 32:
        raise ValueError('Record 1–32 concrete owner requirements')
    for item in requirements:
        if not isinstance(item, dict) or set(item) != {'id', 'description'} or not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', item['id']):
            raise ValueError('Requirements need a simple id and description')
        text(item['description'], 'requirement', 500)
    if len({r['id'] for r in requirements}) != len(requirements):
        raise ValueError('Requirement ids must be unique')
    return value


def read(state, name, default=None):
    path = Path(state) / 'lifecycle' / name
    return json.loads(path.read_text()) if path.exists() else default


def mode(state):
    return read(state, 'deployment-mode.json', {'mode': 'tested'})['mode']


def set_mode(state, selected, identity=None):
    from .facts import discover
    if discover()['phase'] != 'live' or selected not in MODES:
        raise ValueError('Deployment modes can only be selected in the live environment')
    prior = read(state, 'custom-deployment.json')
    if prior and prior.get('state') not in ('cancelled', 'draft') and selected != mode(state):
        raise ValueError('A reviewed custom deployment is in progress. Finish or explicitly archive it before changing modes.')
    identity = Path(identity or Path(__file__).resolve().parent.parent / 'identity')
    source = identity / ('custom/AGENTS.md' if selected == 'custom' else 'AGENTS.md')
    workspace = private_dir(Path(state) / 'workspace')
    temporary = workspace / '.deployment-instructions'
    temporary.unlink(missing_ok=True)
    create_private(temporary, source.read_text())
    os.replace(temporary, workspace / 'AGENTS.md')
    record = {'mode': selected}
    write_observation(state, 'deployment-mode.json', record)
    return record


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def review(plan):
    """Root console: approval covers only this plan and this current disk identity."""
    from .facts import discover
    from .install_common import disks, disk_identity, confirm_disk_erasure
    from .setup import choose
    validate_plan(plan)
    facts = discover()
    if os.geteuid() != 0 or facts['phase'] != 'live' or facts['distro_id'] != plan['distro']:
        raise ValueError('Custom review requires the matching live root console')
    node = next((n for n in disks() if n['name'] == plan['disk']), None)
    if node is None:
        raise ValueError('The requested disk is not an unused internal disk. Mounted disks, imported pools and the boot USB are excluded. Inspect existing data before revising the plan.')
    print('\nCustom deployment — ' + plan['base'] + ' starting point')
    print(json.dumps(disk_identity(node), indent=2))
    for key in ('storage_action', 'storage_plan', 'access_plan', 'recovery_plan'):
        print(key.replace('_', ' ').capitalize() + ': ' + plan[key])
    for requirement in plan['requirements']:
        print('Requested: ' + requirement['description'])
    print('The live agent will use native installation tools after this review. This is not the fixed preset installer.')
    approved = (confirm_disk_erasure(node) is not None if plan['storage_action'] == 'erase' else
                choose('Apply this plan while preserving existing data?', ['Cancel', 'Approve this exact plan']) == 2)
    return {'state': 'approved' if approved else 'cancelled', 'mode': 'custom', 'plan': plan,
            'plan_digest': digest(plan), 'disk': disk_identity(node), 'boot_id': facts['boot_id'],
            'disk_erasure_approved': approved and plan['storage_action'] == 'erase',
            'disk_changes': 'none-by-review', 'installed_boot_verified': False,
            'message': 'Plan approved locally; recheck disk identity before native commands.' if approved else 'Custom review cancelled. No disk changed by review.'}


def checkpoint(state, phase, detail):
    if phase not in ('preparing', 'writing', 'configuring', 'needs-attention', 'prepared-for-boot'):
        raise ValueError('Unknown deployment phase')
    text(detail, 'checkpoint', 2000)
    record = read(state, 'custom-deployment.json')
    if not record or record['state'] == 'cancelled':
        raise ValueError('Review the custom deployment plan locally first')
    if phase == 'prepared-for-boot':
        raise ValueError('Use deployment-finalize; a checkpoint cannot certify boot readiness')
    record['state'] = phase
    if phase in ('writing', 'configuring', 'needs-attention'):
        record['disk_changes'] = 'Native operations may have changed the target; inspect progress and actual storage.'
    record.setdefault('progress', []).append({'phase': phase, 'detail': detail})
    record['progress'] = record['progress'][-64:]
    write_observation(state, 'custom-deployment.json', record)
    return record


def target_file(root, relative):
    """Resolve absolute target symlinks inside target, including Nix store links."""
    pending = list(Path(relative).parts)
    current = root
    count = 0
    while pending:
        part = pending.pop(0)
        if part in ('/', '.'):
            continue
        if part == '..':
            if current == root:
                raise ValueError('Target path escapes its root')
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            count += 1
            if count > 40:
                raise ValueError('Too many target symlinks')
            link = Path(os.readlink(current))
            current = root if link.is_absolute() else current.parent
            pending = list(link.parts) + pending
    return current


def readable_by(root, relative, uid, gid):
    """Verify ordinary Unix permissions needed by the resident account at boot."""
    path = target_file(root, relative)
    if not path.is_file():
        return False
    current = path
    while True:
        stat = current.stat()
        shift = 6 if stat.st_uid == uid else 3 if stat.st_gid == gid else 0
        needed = 4 if current == path else 1
        if not ((stat.st_mode >> shift) & needed):
            return False
        if current == root:
            return True
        current = current.parent


def verify(root, plan, run=subprocess.run):
    """Check the boot floor from actual target files/mounts, never a model assertion."""
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError('Target root must not be a symbolic link')
    checks = {}
    def exists(name):
        return target_file(root, name).is_file()
    result = run(['findmnt', '--json', '--mountpoint', str(root), '-o', 'SOURCE,FSTYPE,UUID,OPTIONS'], capture_output=True, text=True)
    try:
        fs = json.loads(result.stdout)['filesystems'][0] if result.returncode == 0 else {}
    except (ValueError, KeyError, IndexError):
        fs = {}
    checks['root-mounted-writable'] = fs.get('fstype') in ('zfs', 'ext4', 'btrfs', 'xfs') and 'rw' in fs.get('options', '').split(',')
    checks['machine-identity'] = exists('etc/machine-id') and bool(re.fullmatch('[a-f0-9]{32}', target_file(root, 'etc/machine-id').read_text().strip()))
    checks['init'] = exists('sbin/init') if plan['distro'] == 'arch' else exists('nix/var/nix/profiles/system/init')
    passwd = target_file(root, 'etc/passwd')
    checks['resident-account'] = passwd.is_file() and any(line.startswith('controlstack-agent:') for line in passwd.read_text().splitlines())
    resident = next((line.split(':') for line in passwd.read_text().splitlines() if line.startswith('controlstack-agent:')), None) if passwd.is_file() else None
    checks['resident-system-files-readable'] = bool(resident) and all(readable_by(root, name, int(resident[2]), int(resident[3])) for name in ('etc/machine-id', 'etc/os-release', 'etc/passwd', 'etc/systemd/system/controlstack-agent.service'))
    checks['owner-account'] = passwd.is_file() and any(line.startswith(plan['username'] + ':') for line in passwd.read_text().splitlines())
    checks['console-authentication'] = exists('etc/pam.d/login') and exists('etc/shadow')
    checks['resident-service'] = exists('etc/systemd/system/controlstack-agent.service')
    checks['resident-enabled'] = exists('etc/systemd/system/multi-user.target.wants/controlstack-agent.service')
    if plan['distro'] == 'arch':
        checks['kernel'] = exists('boot/vmlinuz-linux')
        checks['initramfs'] = exists('boot/initramfs-linux.img')
        modules = list((root / 'usr/lib/modules').glob('*/modules.dep'))
        checks['kernel-modules'] = bool(modules)
        checks['mount-configuration'] = exists('etc/fstab')
        checks['firmware'] = (root / 'usr/lib/firmware').is_dir()
    else:
        checks['kernel'] = exists('nix/var/nix/profiles/system/kernel')
        checks['initramfs'] = exists('nix/var/nix/profiles/system/initrd')
        checks['kernel-modules'] = target_file(root, 'nix/var/nix/profiles/system/kernel-modules/lib/modules').is_dir()
        checks['mount-configuration'] = exists('etc/fstab')
        checks['native-configuration'] = (root / 'etc/nixos').is_dir() and any((root / 'etc/nixos').glob('*.nix'))
    # Check the actual mounted ESP and referenced systemd-boot files. Alternative
    # bootloaders require an explicit verifier adapter, never a fabricated pass.
    esp = run(['findmnt', '-n', '--mountpoint', str(root / 'boot'), '-o', 'FSTYPE'], capture_output=True, text=True)
    checks['esp-mounted'] = esp.returncode == 0 and esp.stdout.strip() == 'vfat'
    entries = list((root / 'boot/loader/entries').glob('*.conf'))
    entries_valid = False
    for entry in entries:
        lines = [line.split(None, 1) for line in entry.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        references = [v for k, v in lines if k in ('linux', 'initrd')] if all(len(x) == 2 for x in lines) else []
        if references and all(exists('boot/' + ref.lstrip('/')) for ref in references):
            options = next((v for k, v in lines if k == 'options'), '')
            if plan['distro'] == 'arch':
                root_option = ('zfs=' + fs.get('source', '') if fs.get('fstype') == 'zfs' else
                               'root=UUID=' + str(fs.get('uuid', '')))
                entries_valid = root_option in options.split()
            else:
                init = next((v.removeprefix('init=') for v in options.split() if v.startswith('init=')), '')
                entries_valid = bool(init) and exists(init)
            if entries_valid:
                break
    checks['boot-entry'] = entries_valid and exists('boot/EFI/BOOT/BOOTX64.EFI')
    if fs.get('fstype') == 'zfs':
        checks['zfs-userspace'] = exists('usr/bin/zpool') if plan['distro'] == 'arch' else exists('run/current-system/sw/bin/zpool') or exists('nix/var/nix/profiles/system/sw/bin/zpool')
        module_base = 'usr/lib/modules' if plan['distro'] == 'arch' else 'nix/var/nix/profiles/system/kernel-modules/lib/modules'
        base = target_file(root, module_base)
        versions = [p.name for p in base.iterdir() if p.is_dir()] if base.is_dir() else []
        module = find_target_file(root, module_base, 'zfs.ko')
        checks['zfs-module'] = module is not None
        if module is not None and len(versions) == 1:
            vermagic = run(['modinfo', '-F', 'vermagic', str(module)], capture_output=True, text=True)
            checks['zfs-kernel-match'] = vermagic.returncode == 0 and bool(vermagic.stdout.split()) and vermagic.stdout.split()[0] == versions[0]
            if plan['distro'] == 'arch':
                packaged_kernel = target_file(root, module_base + '/' + versions[0] + '/vmlinuz')
                checks['boot-kernel-match'] = packaged_kernel.is_file() and file_hash(packaged_kernel) == file_hash(root / 'boot/vmlinuz-linux')
            else:
                kernel = target_file(root, 'nix/var/nix/profiles/system/kernel')
                checks['boot-kernel-match'] = any('linux-' + versions[0] in part for part in kernel.parts)
        else:
            checks['zfs-kernel-match'] = False
    return {'schema': 1, 'checks': checks, 'boot_floor_passed': all(checks.values()),
            'installed_boot_verified': False, 'root': fs,
            'limits': 'Preboot structural checks for UEFI/systemd-boot. Independent boot and requested-feature tests remain required.'}


def record_review(state, result):
    # The console writes as the agent account via this command; no credentials.
    allowed = {'mode', 'state', 'plan', 'plan_digest', 'disk', 'boot_id', 'disk_erasure_approved', 'disk_changes', 'installed_boot_verified', 'message'}
    if not isinstance(result, dict) or set(result) - allowed:
        raise ValueError('Unexpected review fields; credentials and executable content are not accepted')
    if result.get('mode') != 'custom' or result.get('state') not in ('approved', 'cancelled'):
        raise ValueError('Invalid custom review result')
    validate_plan(result['plan'])
    write_observation(state, 'custom-deployment.json', result)
    return result


def requirement(state, identifier, status, evidence):
    record = read(state, 'custom-deployment.json')
    if not record or identifier not in {r['id'] for r in record['plan']['requirements']}:
        raise ValueError('Unknown reviewed requirement')
    if status not in ('pending', 'passed', 'failed'):
        raise ValueError('Use pending, passed or failed')
    text(evidence, 'evidence', 1000)
    record.setdefault('requirement_results', {})[identifier] = {'status': status, 'evidence': evidence}
    write_observation(state, 'custom-deployment.json', record)
    return record


def write_live_record(state, record):
    """Root console updates a non-secret record without taking its ownership."""
    path = Path(state) / 'lifecycle/custom-deployment.json'
    owner = path.stat()
    temporary = path.with_name('custom-deployment.' + secrets.token_hex(8))
    try:
        create_private(temporary, json.dumps(record, indent=2))
        os.chown(temporary, owner.st_uid, owner.st_gid)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def first_boot_review(state):
    """Local owner schedules pending work; nothing is marked passed or erased."""
    from .facts import discover
    from .setup import choose
    record = read(state, 'custom-deployment.json')
    facts = discover()
    if (os.geteuid() != 0 or facts['phase'] != 'live' or not record or
            record['state'] not in ('approved', 'preparing', 'writing', 'configuring', 'needs-attention') or
            record['boot_id'] != facts['boot_id'] or record['plan_digest'] != digest(validate_plan(record['plan']))):
        raise ValueError('First-boot review requires the unchanged approved plan in this live session')
    original = json.dumps(record, sort_keys=True)
    decisions = {}
    print('You are still on the live USB. This review does not erase a disk, reboot, or certify installed login.')
    print('Required boot checks and failed feature checks still block handoff.')
    for item in record['plan']['requirements']:
        result = record.get('requirement_results', {}).get(item['id'], {'status': 'pending'})
        if result['status'] == 'passed':
            continue
        if result['status'] != 'pending':
            raise ValueError('Resolve the failed or invalid requirement before first-boot review: ' + item['id'])
        print('Current evidence: ' + result.get('evidence', 'Not yet verified'))
        answer = choose('When should this be completed? ' + item['description'], [
            'Before reboot — keep this blocking',
            'After first boot — keep verification pending',
            'Optional work — I approve deferring it',
            'Cancel this review'])
        if answer == 4:
            return {'state': 'cancelled', 'message': 'First-boot review cancelled. Previous records and installation are unchanged.'}
        if answer in (2, 3):
            decisions[item['id']] = {'when': 'post-boot' if answer == 2 else 'deferred', 'result_at_review': result}
    print('Pending work carried forward:')
    for item in record['plan']['requirements']:
        if item['id'] in decisions:
            print(item['description'] + ' — ' + decisions[item['id']]['when'])
    if choose('Save this first-boot review? Untested items remain pending.', ['Cancel', 'Save reviewed schedule']) != 2:
        return {'state': 'cancelled', 'message': 'First-boot review cancelled. Installation is unchanged.'}
    if json.dumps(read(state, 'custom-deployment.json'), sort_keys=True) != original:
        raise ValueError('Deployment changed during review. Review the current evidence again.')
    record['first_boot_review'] = {'schema': 1, 'boot_id': facts['boot_id'], 'plan_digest': record['plan_digest'],
                                 'approved_by': 'root-local-console', 'decisions': decisions}
    write_live_record(state, record)
    return {'state': 'first-boot-reviewed', 'message': 'Pending work scheduled locally. Run deployment-finalize; boot and storage checks still apply.'}


def first_boot_tasks(record):
    """Only unchanged, locally reviewed pending items can cross first boot."""
    review = record.get('first_boot_review', {})
    reviewed = (review.get('schema') == 1 and review.get('approved_by') == 'root-local-console' and
                review.get('boot_id') == record['boot_id'] and review.get('plan_digest') == record['plan_digest'])
    tasks, blocking = [], []
    for item in record['plan']['requirements']:
        result = record.get('requirement_results', {}).get(item['id'], {'status': 'pending'})
        if result.get('status') == 'passed':
            continue
        decision = review.get('decisions', {}).get(item['id'], {}) if reviewed else {}
        if (result.get('status') != 'pending' or decision.get('when') not in ('post-boot', 'deferred') or
                decision.get('result_at_review') != result):
            blocking.append(item['id'])
        else:
            tasks.append({**item, 'status': 'pending', 'when': decision['when'], 'evidence': result.get('evidence', 'Not yet verified')})
    if blocking:
        raise ValueError('Requested features block first boot: ' + ', '.join(blocking) +
                         '. Fix failures; use deployment-first-boot-review only for pending post-boot tests or owner-deferred optional work.')
    return tasks


def finalize(state):
    from .facts import discover
    from .handoff import validate
    from .install_common import output
    facts = discover()
    record = read(state, 'custom-deployment.json')
    if os.geteuid() != 0 or facts['phase'] != 'live' or not record or record['state'] not in ('approved', 'preparing', 'writing', 'configuring', 'needs-attention'):
        raise ValueError('Finalize requires a reviewed custom deployment and live root access')
    plan = validate_plan(record['plan'])
    if record['boot_id'] != facts['boot_id'] or record['plan_digest'] != digest(plan):
        raise ValueError('Deployment review no longer matches this boot/plan')
    root = Path(plan['target'])
    report = verify(root, plan)
    if not report['boot_floor_passed']:
        raise ValueError('Boot checks need attention: ' + ', '.join(k for k, v in report['checks'].items() if not v))
    tasks = first_boot_tasks(record)
    fs = report['root']
    check_storage(record, fs)
    boot_mount = json.loads(output(['findmnt', '--json', '--mountpoint', str(root / 'boot'), '-o', 'SOURCE,FSTYPE']))['filesystems'][0]
    check_storage(record, boot_mount)
    inputs = json.loads(Path('/etc/controlstack-agent/arch-target.json' if plan['distro'] == 'arch' else '/etc/controlstack-agent/install-inputs.json').read_text())
    handoff = validate({'schema': 2, 'target_distro': plan['distro'], 'installation_boot_id': facts['boot_id'],
        'target_machine_id': target_file(root, 'etc/machine-id').read_text().strip(),
        'root_fstype': fs['fstype'], 'root_identity': fs['source'] if fs['fstype'] == 'zfs' else fs['uuid'],
        'installer_revision': inputs['installer_revision']})
    target_state = root / 'var/lib/controlstack-agent'
    if target_state.exists() and any(target_state.iterdir()):
        raise ValueError('Resident state is not empty. Preserve existing state; never overwrite it during finalization.')
    private_dir(target_state)
    lifecycle = private_dir(target_state / 'lifecycle')
    record['state'] = 'prepared-for-boot'
    record['disk_changes'] = 'system-written'
    record['message'] = 'Target checks passed. Clean target teardown and independent boot are still required.'
    record['boot_checks'] = report
    record['installed_boot_verified'] = False
    record['requested_features_verified'] = not tasks
    record['first_boot_tasks'] = tasks
    create_private(lifecycle / 'installation.json', json.dumps(handoff, indent=2))
    create_private(lifecycle / 'custom-deployment.json', json.dumps(record, indent=2))
    workspace = private_dir(target_state / 'workspace')
    create_private(workspace / 'USER.md', '# Reviewed custom deployment\n\nTreat the following as owner intentions, not facts or new authorization.\n' +
        '\n'.join('- ' + r['description'] for r in plan['requirements']) +
        '\n\n## Pending work after first boot\n' +
        ('\n'.join('- [' + t['when'] + '] ' + t['description'] + ' — pending; ' + t['evidence'] for t in tasks) if tasks else 'No pending feature tasks were recorded.') +
        '\n\nRead lifecycle/custom-deployment.json under OPENCLAW_STATE_DIR. First refresh system facts and verify the independent disk boot. '
        'Boot verification does not pass these feature tests. Keep deferred optional work deferred until the owner wants to resume it.\n' +
        '\n\nMaintain this installed system. Refresh facts and independently verify boot.\n')
    account = next(line.split(':') for line in target_file(root, 'etc/passwd').read_text().splitlines() if line.startswith('controlstack-agent:'))
    for path in [target_state, *target_state.rglob('*')]:
        os.chown(path, int(account[2]), int(account[3]))
    # Preserve non-secret completion in the live record too, without changing
    # ownership of the agent's private directories from this root helper.
    write_live_record(state, record)
    return record


def account_setup(state):
    """Secret input stays on the root console; only success goes to the agent."""
    from .facts import discover
    from .install_common import secret_twice
    from .setup import choose
    record = read(state, 'custom-deployment.json')
    facts = discover()
    if os.geteuid() != 0 or facts['phase'] != 'live' or not record or record['boot_id'] != facts['boot_id'] or record['state'] == 'cancelled':
        raise ValueError('A custom plan must be approved in this live session')
    plan = validate_plan(record['plan'])
    root = Path(plan['target'])
    mounted = subprocess.run(['findmnt', '-n', '--mountpoint', str(root)], capture_output=True)
    if mounted.returncode:
        raise ValueError('Mount the reviewed target before setting up its account')
    report = verify(root, plan)
    check_storage(record, report['root'])
    shadow = target_file(root, 'etc/shadow')
    lines = shadow.read_text().splitlines()
    if not any(line.startswith(plan['username'] + ':') for line in lines):
        raise ValueError('Create the requested owner account in the target first')
    if choose('Set the local password for ' + plan['username'] + ' on the custom target?', ['Set password', 'Cancel']) == 2:
        return {'state': 'cancelled', 'message': 'Account setup cancelled; custom deployment remains available.'}
    password = secret_twice('Password for your local account (hidden): ')
    try:
        hashed = subprocess.run(['mkpasswd', '--method=yescrypt', '--stdin'], input=password + '\n', capture_output=True, text=True, check=True).stdout.strip()
    finally:
        password = None
    if not hashed.startswith('$y$'):
        raise ValueError('Password hashing failed')
    updated = []
    for line in lines:
        fields = line.split(':')
        if fields[0] == plan['username']:
            fields[1] = hashed
        updated.append(':'.join(fields))
    shadow.write_text('\n'.join(updated) + '\n')
    shadow.chmod(0o600)
    password_file = target_file(root, 'var/lib/controlstack-owner.password')
    password_file.write_text(hashed + '\n')
    password_file.chmod(0o600)
    if choose('Use a YubiKey for this account?', ['Keep the reviewed password policy', 'Enroll and test a YubiKey']) == 2:
        from .security_key import enroll, install_enrollment
        enrollment = enroll(plan['username'])
        install_enrollment(root, enrollment, plan['username'])
        message = 'Local password and YubiKey enrollment saved. Verify the chosen greeter and lock PAM policy before reboot.'
    else:
        message = 'Local account password saved on the target. No secret was returned to chat.'
    return {'state': 'account-ready', 'message': message}


def check_storage(record, fs):
    from .install_common import output
    # Prove target storage belongs to the reviewed disk, including ZFS members.
    members = output(['zpool', 'status', '-P', fs['source'].split('/')[0]]).split() if fs['fstype'] == 'zfs' else [fs['source'].split('[')[0]]
    paths = [p for p in members if p.startswith('/dev/')]
    if not paths:
        raise ValueError('Cannot identify target storage members')
    for device in paths:
        chain = json.loads(output(['lsblk', '--json', '--inverse', '--paths', '--bytes', '-o', 'NAME,TYPE,SERIAL,SIZE', device]))
        from .install_common import descendants
        owners = [n for top in chain['blockdevices'] for n in descendants(top) if n['type'] == 'disk']
        if not owners or any(n['name'] != record['disk']['name'] or n.get('serial') != record['disk']['serial'] or int(n['size']) != int(record['disk']['size']) for n in owners):
            raise ValueError('Target filesystem is outside the reviewed disk identity')


def encryption_key_setup(state):
    """Create a private RAM key file for native encryption tools, never chat."""
    from .facts import discover
    from .install_common import secret_twice, output
    from .setup import choose
    facts = discover()
    record = read(state, 'custom-deployment.json')
    if os.geteuid() != 0 or facts['phase'] != 'live' or not record or record['boot_id'] != facts['boot_id'] or record['state'] == 'cancelled':
        raise ValueError('Review the custom plan in this live session first')
    if output(['findmnt', '-n', '-o', 'FSTYPE', '/run']) != 'tmpfs':
        raise ValueError('Disk passphrase entry requires private RAM storage')
    area = private_dir('/run/controlstack-custom-secrets')
    key = area / 'volume.key'
    if key.exists() or key.is_symlink():
        raise ValueError('A disk passphrase is already staged. Resume the existing encryption step; do not replace its key blindly.')
    if choose('Create the disk encryption passphrase for your reviewed custom plan?', ['Cancel', 'Enter passphrase privately']) == 1:
        return {'state': 'cancelled', 'message': 'Disk passphrase entry cancelled.'}
    secret = secret_twice('Disk unlock passphrase (hidden; keep a safe copy elsewhere): ')
    try:
        if not 8 <= len(secret.encode()) <= 512 or any(c in secret for c in '\r\n\x00'):
            raise ValueError('Use a single-line passphrase of 8–512 bytes')
        create_private(key, secret)
    finally:
        secret = None
    return {'state': 'encryption-key-ready', 'key_file': str(key),
            'message': 'Passphrase staged privately in RAM. Feed the file to native encryption tools without printing it; remove it after use. Do not copy it to the installed system.'}


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def find_target_file(root, relative, prefix):
    """Follow target Nix-store directory links without following host paths."""
    pending = [Path(relative)]
    seen = set()
    while pending:
        relative = pending.pop()
        current = target_file(root, relative)
        if current in seen:
            continue
        seen.add(current)
        if len(seen) > 50000:
            raise ValueError('Target module tree is unexpectedly large')
        if current.is_file() and current.name.startswith(prefix):
            return current
        if current.is_dir():
            pending.extend(relative / child.name for child in current.iterdir())
    return None
