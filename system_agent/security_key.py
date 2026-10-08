"""Owner security-key policy, with local enrollment and physical touch confirmation."""
import ctypes
import json
import os
import pwd
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

CONFIG = Path('/etc/controlstack-agent/owner-policy.json')
STATE = Path('/var/lib/controlstack-security')
ORIGIN = 'pam://controlstack-system'
USB = Path('/sys/bus/usb/devices')


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def devices():
    found = {}
    for device in USB.glob('*'):
        try:
            if (device / 'idVendor').read_text().strip() != '1050':
                continue
            serial = (device / 'serial').read_text().strip() if (device / 'serial').exists() else ''
            found[device.name] = serial
        except OSError:
            continue
    return found


def policy():
    value = json.loads(CONFIG.read_text())
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', value['owner']):
        raise ValueError('Invalid owner policy')
    return value


def password_allowed():
    try:
        # Missing/corrupt policy fails closed. Installation writes an explicit default.
        return json.loads((STATE / 'password-unlock.json').read_text()) == {'enabled': True}
    except (OSError, ValueError):
        return False


def matching_keys():
    saved = json.loads((STATE / 'key-device.json').read_text())
    return {name for name, serial in devices().items() if not saved['serial'] or serial == saved['serial']}


def unlocked(owner):
    # Check both logind and the lock process: a compositor's hint may lag.
    if subprocess.run(['pgrep', '-u', owner, '-x', 'hyprlock'], stdout=subprocess.DEVNULL).returncode == 0:
        return False
    for row in run(['loginctl', 'list-sessions', '--no-legend'], capture_output=True).stdout.splitlines():
        session = row.split()[0]
        props = dict(line.split('=', 1) for line in run(
            ['loginctl', 'show-session', session, '-p', 'Name', '-p', 'Active', '-p', 'Remote',
             '-p', 'LockedHint', '-p', 'Type', '-p', 'Class'], capture_output=True).stdout.splitlines() if '=' in line)
        if (props.get('Name') == owner and props.get('Active') == 'yes' and props.get('Remote') == 'no'
                and props.get('LockedHint') == 'no' and props.get('Type') == 'wayland'
                and props.get('Class') == 'user'):
            return True
    return False


def validate_enrollment(value, owner):
    if not isinstance(value, dict) or set(value) != {'mapping', 'serial'}:
        raise ValueError('Security-key enrollment is missing')
    mapping = value['mapping']
    if (not isinstance(mapping, str) or len(mapping) > 16384 or '\n' in mapping or '\r' in mapping
            or not mapping.startswith(owner + ':') or not re.fullmatch(r'[A-Za-z0-9,:/+_=. -]+', mapping)):
        raise ValueError('Invalid security-key registration')
    parts = mapping[len(owner) + 1:].split(',')
    if len(parts) != 4 or not parts[0] or not parts[1] or parts[2] not in ('es256', 'eddsa', 'rs256'):
        raise ValueError('Incomplete security-key registration')
    if not isinstance(value['serial'], str) or not re.fullmatch(r'[A-Za-z0-9-]{0,64}', value['serial']):
        raise ValueError('Invalid security-key device identity')
    return value


def pam_verify(mapping, owner):
    """Use the actual pinned PAM module and a private config directory, never host PAM files."""
    class Message(ctypes.Structure):
        _fields_ = [('style', ctypes.c_int), ('message', ctypes.c_char_p)]
    class Response(ctypes.Structure):
        _fields_ = [('response', ctypes.c_void_p), ('code', ctypes.c_int)]
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(Message)),
                                    ctypes.POINTER(ctypes.POINTER(Response)), ctypes.c_void_p)
    libc = ctypes.CDLL(None)
    libc.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    libc.calloc.restype = ctypes.c_void_p
    @callback_type
    def converse(count, messages, responses, _):
        if count < 1 or count > 32 or any(messages[i].contents.style not in (3, 4) for i in range(count)):
            return 19  # PAM_CONV_ERR: no password/PIN is accepted by this touch-only policy.
        memory = libc.calloc(count, ctypes.sizeof(Response))
        if not memory:
            return 5
        responses[0] = ctypes.cast(memory, ctypes.POINTER(Response))
        return 0
    class Conversation(ctypes.Structure):
        _fields_ = [('callback', callback_type), ('data', ctypes.c_void_p)]
    pam = ctypes.CDLL(os.environ['CONTROLSTACK_PAM_LIBRARY'])
    pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation),
                                     ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    with tempfile.TemporaryDirectory(prefix='controlstack-key-', dir='/run') as directory:
        module = os.environ['CONTROLSTACK_U2F_MODULE']
        Path(directory, 'verify').write_text(f'auth required {module} authfile={mapping} origin={ORIGIN} appid={ORIGIN} userpresence=1\n')
        handle = ctypes.c_void_p()
        conversation = Conversation(converse, None)
        result = pam.pam_start_confdir(b'verify', owner.encode(), ctypes.byref(conversation), directory.encode(), ctypes.byref(handle))
        if result == 0:
            try:
                result = pam.pam_authenticate(handle, 0)
            finally:
                pam.pam_end(handle, result)
        return result == 0


def verify(mapping, owner):
    print('Touch your enrolled YubiKey to confirm.', flush=True)
    command = [sys.executable, '-m', 'system_agent.security_key', 'verify', str(mapping), owner]
    return subprocess.run(command, timeout=60, stdin=subprocess.DEVNULL).returncode == 0


def enroll(owner):
    attached = devices()
    fido = run(['fido2-token', '-L'], capture_output=True).stdout.splitlines()
    if len(attached) != 1 or len(fido) != 1 or 'yubico' not in fido[0].casefold():
        raise ValueError('Connect just the YubiKey you want to enroll, with FIDO enabled, and retry.')
    print('Touch the YubiKey to register it for this computer. You will touch it once more to test sign-in.', flush=True)
    result = run(['pamu2fcfg', '-u', owner, '-o', ORIGIN, '-i', ORIGIN], capture_output=True, timeout=90)
    value = validate_enrollment({'mapping': result.stdout.strip(), 'serial': next(iter(attached.values()))}, owner)
    with tempfile.TemporaryDirectory(prefix='controlstack-enroll-', dir='/run') as directory:
        # PAM requires an account that exists on the running live system. Only
        # the lookup label changes; credential, public key and origin are identical.
        live_user = pwd.getpwuid(os.getuid()).pw_name
        mapping = Path(directory) / 'keys'
        mapping.write_text(live_user + ':' + value['mapping'].split(':', 1)[1] + '\n')
        mapping.chmod(0o600)
        if not verify(mapping, live_user):
            raise ValueError('The new YubiKey registration did not pass its sign-in test. No disk was changed.')
    if devices() != attached:
        raise ValueError('The connected key changed during enrollment. Retry with one YubiKey.')
    return value


def install_enrollment(root, value, owner):
    value = validate_enrollment(value, owner)
    directory = Path(root) / 'var/lib/controlstack-security'
    directory.mkdir(parents=True, exist_ok=True); directory.chmod(0o755)
    # Public FIDO key handles/verification keys, never a private key. Root-owned
    # files must be readable by the unprivileged lock-screen PAM client.
    for name, content in {'u2f-keys': value['mapping'] + '\n',
                          'key-device.json': json.dumps({'serial': value['serial']}) + '\n',
                          'password-unlock.json': '{"enabled": true}\n'}.items():
        path = directory / name; path.write_text(content); path.chmod(0o644)


def set_password(enabled):
    if os.geteuid() != 0:
        raise PermissionError('Use the local security-key control')
    owner = policy()['owner']
    if os.environ.get('SUDO_USER') != owner or not unlocked(owner) or not matching_keys():
        raise PermissionError('Unlock the desktop and connect the enrolled YubiKey first')
    if not verify(STATE / 'u2f-keys', owner):
        raise PermissionError('YubiKey confirmation did not finish')
    # Recheck after touching: the session or key may have changed during the prompt.
    if not unlocked(owner) or not matching_keys():
        raise PermissionError('The desktop locked or the key was removed; no policy changed')
    fd, name = tempfile.mkstemp(prefix='.policy-', dir=STATE)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'enabled': enabled}, stream); stream.write('\n')
    os.chmod(name, 0o644); os.replace(name, STATE / 'password-unlock.json')
    print('Password screen unlock is ' + ('enabled.' if enabled else 'disabled. Use your YubiKey to unlock.'))


def lock_owner(owner):
    for row in run(['loginctl', 'list-sessions', '--no-legend'], capture_output=True).stdout.splitlines():
        fields = row.split()
        if len(fields) >= 3 and fields[2] == owner:
            subprocess.run(['loginctl', 'lock-session', fields[0]], check=False)


def watch():
    owner = policy()['owner']
    previous = matching_keys()
    while True:
        time.sleep(.25)
        current = matching_keys()
        if previous - current:
            lock_owner(owner)
        previous = current


def main():
    args = sys.argv[1:]
    if args == ['password-check']:
        return 0 if password_allowed() else 1
    if len(args) == 3 and args[0] == 'verify':
        return 0 if pam_verify(Path(args[1]), args[2]) else 1
    try:
        if args == ['status']:
            value = policy()
            enabled = value['login_policy'] == 'yubikey'
            print(json.dumps({'enabled': enabled, 'key_present': bool(matching_keys()) if enabled else False,
                              'password_unlock': password_allowed() if enabled else True,
                              'unlocked': unlocked(value['owner']) if enabled else False,
                              'always_on': value['power_policy'] == 'always-on'}))
        elif args in (['password', 'on'], ['password', 'off']):
            set_password(args[1] == 'on')
        elif args == ['watch'] and os.geteuid() == 0:
            watch()
        else:
            raise ValueError('Unsupported security-key operation')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
