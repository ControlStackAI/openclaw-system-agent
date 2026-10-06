"""Owner-run maintenance broker. The resident account has no permission to run it."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path
from .facts import discover
from .state import private_dir, create_private

ACTIONS = {'snapshot': 'datasets', 'scrub': 'pools', 'restart-service': 'services'}
POLICY = Path('/etc/controlstack-agent/capabilities.json')
PLANS = Path('/var/lib/controlstack-agent-approvals')


def read_policy(path=POLICY):
    # NixOS /etc files are root-owned links into its immutable store.
    # Validate both the link path and its resolved root-owned target before opening.
    for item in (path, *path.parents):
        mode = item.lstat()
        if mode.st_uid != 0 or (not stat.S_ISLNK(mode.st_mode) and mode.st_mode & 0o022):
            raise ValueError('Capability policy must be under root-owned, non-writable paths.')
    resolved = path.resolve(strict=True)
    for parent in resolved.parents:
        mode = parent.lstat()
        trusted_store = parent == Path('/nix/store') and bool(mode.st_mode & stat.S_ISVTX)
        if stat.S_ISLNK(mode.st_mode) or mode.st_uid != 0 or (mode.st_mode & 0o022 and not trusted_store):
            raise ValueError('Resolved capability policy path is not protected.')
    fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise ValueError('Capability policy must be a root-owned, non-writable regular file.')
        value = json.load(f)
    if set(value) - {'datasets', 'pools', 'services'}:
        raise ValueError('Unknown capability policy field.')
    if any(not isinstance(v, list) or any(not isinstance(x, str) for x in v) for v in value.values()):
        raise ValueError('Capability targets must be lists of names.')
    return value


def query(args):
    return subprocess.check_output(args, text=True, timeout=20).strip()


def identity(action, target):
    if action == 'snapshot':
        return query(['zfs', 'get', '-Hp', '-o', 'value', 'guid', target])
    if action == 'scrub':
        return query(['zpool', 'get', '-Hp', '-o', 'value', 'guid', target])
    loaded = query(['systemctl', 'show', target, '-p', 'LoadState', '--value'])
    if loaded != 'loaded':
        raise ValueError('The selected service is not loaded.')
    # Bind restart approval to exact unit content/config as well as unit name.
    return hashlib.sha256(query(['systemctl', 'cat', target]).encode()).hexdigest()


def validate_target(action, target, policy):
    if action not in ACTIONS or target not in policy.get(ACTIONS[action], []):
        raise ValueError('This operation is not enabled for that target.')
    if not re.fullmatch(r'[A-Za-z0-9_.:/-]+', target) or target.startswith('-'):
        raise ValueError('Invalid target name.')
    if action == 'snapshot' and ('/' not in target or any(p in ('.', '..') for p in target.split('/'))):
        raise ValueError('Snapshots require an explicitly named dataset, not a whole pool.')
    if action == 'scrub' and '/' in target:
        raise ValueError('Scrub requires a pool name.')
    if action == 'restart-service' and not re.fullmatch(r'[A-Za-z0-9_.-]+\.service', target):
        raise ValueError('Restart requires an exact non-template service unit.')


def create_plan(action, target, policy, facts, now=None):
    validate_target(action, target, policy)
    if facts['phase'] != 'installed-candidate' or not facts.get('boot_id'):
        raise ValueError('Maintenance requires an inspected installed-system environment.')
    now = int(time.time() if now is None else now)
    plan = {'schema': 1, 'id': secrets.token_hex(16), 'action': action, 'target': target,
            'resource_identity': identity(action, target), 'boot_id': facts['boot_id'],
            'expires': now + 300, 'snapshot_name': 'controlstack-' + secrets.token_hex(8)}
    plan['digest'] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    return plan


def execution_argv(plan, policy, facts, approval, now=None):
    candidate = {k: v for k, v in plan.items() if k != 'digest'}
    digest = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
    if not secrets.compare_digest(approval, digest) or digest != plan.get('digest'):
        raise ValueError('Approval does not match this exact plan.')
    if (time.time() if now is None else now) >= plan['expires']:
        raise ValueError('This plan expired. Inspect again before approving.')
    if facts['phase'] != 'installed-candidate' or facts['boot_id'] != plan['boot_id']:
        raise ValueError('The boot environment changed. A new plan is required.')
    action, target = plan['action'], plan['target']
    validate_target(action, target, policy)
    if identity(action, target) != plan['resource_identity']:
        raise ValueError('The target changed since this plan was made.')
    if action == 'snapshot':
        return ['zfs', 'snapshot', target + '@' + plan['snapshot_name']]
    if action == 'scrub':
        return ['zpool', 'scrub', target]
    return ['systemctl', 'restart', target]


def main():
    p = argparse.ArgumentParser(description='Owner-approved, narrowly scoped system maintenance')
    sub = p.add_subparsers(dest='command', required=True)
    plan = sub.add_parser('plan')
    plan.add_argument('action', choices=sorted(ACTIONS))
    plan.add_argument('target')
    apply = sub.add_parser('apply')
    apply.add_argument('id')
    apply.add_argument('--approve', required=True, help='Digest from the exact owner-reviewed plan')
    args = p.parse_args()
    try:
        if os.geteuid() != 0:
            raise ValueError('Only the owner’s administrator session can approve maintenance.')
        os.umask(0o077)
        policy = read_policy()
        directory = private_dir(PLANS)
        if args.command == 'plan':
            record = create_plan(args.action, args.target, policy, discover())
            create_private(directory / (record['id'] + '.json'), json.dumps(record, indent=2))
            print(json.dumps({**record, 'changes_applied': False,
                'owner_review': f"Approve {args.action} for {args.target}? The approval expires in five minutes."}, indent=2))
            return 0
        if not re.fullmatch('[a-f0-9]{32}', args.id):
            raise ValueError('Invalid plan identifier.')
        # Exclusive lock serializes execution and atomically consumes the approval.
        fd = os.open(directory / (args.id + '.json'), os.O_RDWR | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            record = json.load(f)
            if record.get('consumed'):
                raise ValueError('This approval has already been used.')
            argv = execution_argv(record, policy, discover(), args.approve)
            record['consumed'] = True
            f.seek(0); f.truncate(); json.dump(record, f); f.flush(); os.fsync(f.fileno())
            # Consume before executing. A crash must never replay an approved action.
            subprocess.run(argv, check=True, timeout=120)
            action, target = record['action'], record['target']
            if action == 'snapshot':
                query(['zfs', 'list', '-H', '-t', 'snapshot', target + '@' + record['snapshot_name']])
                result = 'snapshot-created'
            elif action == 'restart-service':
                query(['systemctl', 'is-active', target])
                result = 'service-active'
            else:
                result = 'scrub-start-requested'  # Completion requires a later pool-health check.
            print(json.dumps({'id': args.id, 'result': result, 'changes_applied': True}))
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f'Maintenance did not complete: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
