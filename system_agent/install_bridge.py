"""Live-only request bridge. The root console owns all disk approval and execution.

The agent can inspect readiness or request the supported installation flow. There
is deliberately no execute command, approval argument, shell string or disk path.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import socket
import stat
import struct
import threading
import time

DIRECTORY = Path('/run/controlstack-install-bridge')
SOCKET = DIRECTORY / 'console.sock'
LIMIT = 16384


def request(operation, choices=None, retry=False):
    message = {'operation': operation}
    if choices is not None:
        message['choices'] = choices
        message['retry'] = retry
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        try:
            client.connect(str(SOCKET))
        except OSError as error:
            raise ValueError('The live console installation bridge is not available. Open the local System Assistant setup; do not bypass permissions.') from error
        client.sendall(json.dumps(message).encode() + b'\n')
        value = json.loads(read_message(client))
        if 'error' in value:
            raise ValueError(value['error'])
        return value


def read_message(connection):
    data = b''
    while b'\n' not in data:
        chunk = connection.recv(min(4096, LIMIT + 1 - len(data)))
        if not chunk:
            raise ValueError('Incomplete bridge request')
        data += chunk
        if len(data) > LIMIT:
            raise ValueError('Bridge request is too large')
    line, rest = data.split(b'\n', 1)
    if rest:
        raise ValueError('Only one request is allowed per connection')
    return line


def readiness(distro):
    from .profile import DESKTOPS
    result = {'distro': distro, 'uefi': Path('/sys/firmware/efi').is_dir(),
              'desktops': ['hyprland', 'none'] if distro == 'arch' else list(DESKTOPS),
              'checked_by': 'root-local-console', 'disk_erasure_approved': False,
              'approval': 'The local screen reviews the exact disk and requires the owner to approve it.',
              'custom_scripts_supported': False}
    from .choices import DEFAULTS
    result['supported_choices'] = list(DEFAULTS)
    if distro == 'arch':
        from adapters.arch.install import INPUTS
        try:
            inputs = json.loads(INPUTS.read_text())
            payload = Path(inputs['payload'])
            info = payload.stat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Payload is not a regular file')
            with payload.open('rb') as stream:
                stream.read(1)
            result['payload'] = {'status': 'readable-by-installer', 'bytes': info.st_size,
                                 'integrity': 'checked during preparation before disk approval'}
        except FileNotFoundError:
            result['payload'] = {'status': 'missing-from-installer-view'}
        except PermissionError:
            result['payload'] = {'status': 'installer-permission-denied'}
        except (OSError, ValueError, KeyError):
            result['payload'] = {'status': 'invalid-installer-payload-metadata'}
    else:
        from adapters.nixos.install import INPUTS
        result['payload'] = {'status': 'pinned-inputs-present' if INPUTS.is_file() else 'missing-pinned-inputs',
                             'integrity': 'Nix prepares the selected closure before disk approval'}
    return result


class Bridge:
    def __init__(self, distro, directory=DIRECTORY):
        self.distro = distro
        self.directory = directory
        self.path = directory / 'console.sock'
        self.lock = threading.Lock()
        self.record = None
        self.stopping = threading.Event()

    def handle(self, value):
        if not isinstance(value, dict):
            raise ValueError('Expected a structured installation request')
        operation = value.get('operation')
        if operation == 'status' and set(value) == {'operation'}:
            result = readiness(self.distro)
            with self.lock:
                result['request'] = dict(self.record) if self.record else None
            return result
        if operation != 'request' or set(value) != {'operation', 'choices', 'retry'} or type(value.get('retry')) is not bool:
            raise ValueError('Only status and a typed installation request are supported; approval must happen locally')
        from .choices import validate_partial
        choices = dict(validate_partial(value['choices']))
        with self.lock:
            # A retry of an installed target must not reopen the erasure flow.
            # Keep the cleanup diagnosis even if the model changes its choices.
            if self.record and self.record['state'] == 'needs-cleanup':
                return dict(self.record)
            if self.record and self.record['state'] in ('queued', 'reviewing'):
                return dict(self.record)
            # Tool retries cannot reopen the same approval after cancel/failure.
            digest = hashlib.sha256(json.dumps(choices, sort_keys=True).encode()).hexdigest()
            if self.record and self.record['choices_digest'] == digest and not value['retry']:
                return dict(self.record)
            self.record = {'id': secrets.token_hex(8), 'state': 'queued', 'choices': choices,
                           'choices_digest': digest, 'requested_at': time.monotonic(),
                           'disk_erasure_approved': False,
                           'message': 'Your local console will open installation review automatically. No disk has been changed.'}
            return dict(self.record)

    def take(self):
        with self.lock:
            if not self.record or self.record['state'] != 'queued':
                return None
            # Give the tool response a moment to reach the chat before switching.
            if time.monotonic() - self.record['requested_at'] < 2:
                return None
            self.record['state'] = 'reviewing'
            return dict(self.record)

    def finish(self, result):
        with self.lock:
            self.record.update(result)

    def serve(self):
        while not self.stopping.is_set():
            try:
                connection, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                connection.settimeout(3)
                try:
                    _, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid not in (0, self.account.pw_uid):
                        raise PermissionError('Only the local system assistant may request installation review')
                    result = self.handle(json.loads(read_message(connection)))
                except (OSError, ValueError, TypeError) as error:
                    result = {'error': str(error)}
                try:
                    connection.sendall(json.dumps(result).encode() + b'\n')
                except OSError:
                    pass

    def __enter__(self):
        from .facts import discover
        facts = discover()
        if os.geteuid() != 0 or facts['phase'] != 'live' or facts['distro_id'] != self.distro:
            raise ValueError('The installation bridge requires the root live console')
        self.account = pwd.getpwnam('controlstack-agent')
        self.directory.mkdir(mode=0o750, exist_ok=True)
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unprotected installation bridge directory')
        os.chown(self.directory, 0, self.account.pw_gid)
        os.chmod(self.directory, 0o750)
        # An exclusive root lock prevents another console from stealing the
        # listener. After a crash the lock is released, allowing stale cleanup.
        self.lock_fd = os.open(self.directory / 'console.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.lock_fd)
            raise ValueError('Installation review is already open on another local console')
        self.path.unlink(missing_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.server.bind(str(self.path))
            os.chown(self.path, 0, self.account.pw_gid)
            os.chmod(self.path, 0o660)
            self.server.listen(4)
            self.server.settimeout(.25)
        except BaseException:
            self.server.close()
            os.close(self.lock_fd)
            raise
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stopping.set()
        self.server.close()
        self.thread.join(timeout=4)
        self.path.unlink(missing_ok=True)
        os.close(self.lock_fd)
