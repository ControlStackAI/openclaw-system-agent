"""Install the shared owner policy into a fresh Arch target only."""
import json
from pathlib import Path
from .target import write, script

SHARED = Path(__file__).resolve().parents[1] / 'shared'
POWER = json.loads((SHARED / 'power-policy.json').read_text())


def configure(root, runtime, choices):
    owner = choices['username']
    policy = {'owner': owner, 'power_policy': choices.get('power_policy', 'standard'),
              'login_policy': choices.get('login_policy', 'password')}
    write(root, 'etc/controlstack-agent/owner-policy.json', json.dumps(policy) + '\n')
    if policy['power_policy'] == 'always-on':
        write(root, 'etc/sddm.conf.d/90-controlstack-power.conf', '[X11]\nServerArguments=-nolisten tcp -s 0 -dpms\n')
        write(root, 'etc/systemd/logind.conf.d/90-controlstack.conf', '[Login]\n' +
              '\n'.join(f'{k}={v}' for k, v in POWER['logind'].items()) + '\n')
        write(root, 'etc/systemd/sleep.conf.d/90-controlstack.conf', '[Sleep]\n' +
              '\n'.join(f'{k}=no' for k in POWER['sleep']) + '\n')
        for unit in ['sleep.target', 'suspend.target', 'hibernate.target', 'hybrid-sleep.target',
                     'suspend-then-hibernate.target', 'tlp.service', 'power-profiles-daemon.service']:
            path = root / 'etc/systemd/system' / unit
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True); path.symlink_to('/dev/null')
        write(root, 'etc/NetworkManager/conf.d/90-controlstack-power.conf', '[connection]\nwifi.powersave=2\n')
        write(root, 'usr/share/controlstack/always-on.py', (SHARED / 'always-on.py').read_text())
        write(root, 'etc/udev/rules.d/90-controlstack-power.rules',
              'ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"\n'
              'ACTION=="add", SUBSYSTEM=="pci", TEST=="power/control", ATTR{power/control}="on"\n')
        write(root, 'etc/systemd/system/controlstack-performance.service', '''[Unit]
Description=Apply always-on performance policy
[Service]
Type=oneshot
ExecStart=/usr/bin/python /usr/share/controlstack/always-on.py
[Install]
WantedBy=multi-user.target
''')
    if policy['login_policy'] == 'yubikey':
        # All modules come from the same pinned runtime closure on both distros.
        module = runtime + '/lib/controlstack-security/pam_u2f.so'
        args = ' authfile=/var/lib/controlstack-security/u2f-keys origin=pam://controlstack-system appid=pam://controlstack-system cue userpresence=1\n'
        for service in ['sddm', 'login']:
            write(root, 'etc/pam.d/' + service, 'auth required ' + module + args +
                  'account include system-login\npassword include system-login\nsession include system-login\n')
        write(root, 'etc/pam.d/hyprlock',
              'auth [success=ignore default=1] pam_exec.so quiet /usr/local/bin/system-agent-key password-check\n'
              'auth sufficient pam_unix.so\n' + 'auth required ' + module + args +
              'account required pam_unix.so\n')
        write(root, 'etc/sudoers.d/controlstack-key',
              owner + ' ALL=(root) NOPASSWD: /usr/local/bin/system-agent-key password on, /usr/local/bin/system-agent-key password off\n', 0o440)
        write(root, 'etc/systemd/system/controlstack-key-watch.service', '''[Unit]
Description=Lock on security-key removal
After=systemd-logind.service
[Service]
ExecStart=/usr/local/bin/system-agent-key watch
Restart=on-failure
RestartSec=1
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
''')
