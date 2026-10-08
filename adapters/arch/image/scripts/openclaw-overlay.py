#!/usr/bin/env python3
"""Runs only inside the disposable Arch build root."""
import json
from pathlib import Path
import subprocess

runtime = Path('/root/controlstack-runtime-path').read_text().strip()
if not runtime.startswith('/nix/store/') or not (Path(runtime) / 'bin/openclaw').is_file():
    raise ValueError('The complete locked OpenClaw runtime is missing')
for name in ('openclaw', 'system-agent', 'system-agent-setup', 'system-agent-admin', 'claude'):
    link = Path('/usr/local/bin') / name
    link.unlink(missing_ok=True)
    link.symlink_to(runtime + '/bin/' + name)
conf = Path('/etc/controlstack-agent')
conf.mkdir(parents=True, exist_ok=True)
(conf / 'installed-mcp.json').write_text('{}\n')
(conf / 'image-capabilities.json').write_text(json.dumps({
    'schema': 1, 'distro': 'arch', 'runtime': 'openclaw',
    'installation': True, 'desktops': ['hyprland', 'none'],
    'explanation': 'Arch UEFI installation uses a verified native payload with ZFS and persistent OpenClaw.'
}) + '\n')
marker = Path('/etc/agent-installer')
marker.mkdir(parents=True, exist_ok=True)
(marker / 'live-image').write_text('arch\n')
(marker / 'image.json').write_text('{"schema":1,"distro":"arch","runtime":"openclaw"}\n')
Path('/etc/sysusers.d').mkdir(parents=True, exist_ok=True)
Path('/etc/sysusers.d/controlstack-agent.conf').write_text('u controlstack-agent - "System Assistant" /run/controlstack-agent\n')
subprocess.run(['systemd-sysusers'], check=True)
service = '''[Unit]
Description=OpenClaw System Assistant (live RAM session)
After=network.target
[Service]
User=controlstack-agent
Group=controlstack-agent
RuntimeDirectory=controlstack-agent
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
Environment=HOME=/run/controlstack-agent
Environment=OPENCLAW_HOME=/run/controlstack-agent
Environment=OPENCLAW_STATE_DIR=/run/controlstack-agent
Environment=OPENCLAW_CONFIG_PATH=/run/controlstack-agent/openclaw.json
Environment=OPENCLAW_DISABLE_BONJOUR=1
Environment=OPENCLAW_NIX_MODE=0
Environment=PATH=/usr/local/bin:/usr/bin
UMask=0077
ExecStartPre=/usr/local/bin/system-agent initialize
ExecStartPre=/usr/local/bin/system-agent local-policy
ExecStartPre=/usr/local/bin/system-agent refresh
ExecStart=/usr/local/bin/openclaw gateway run
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadWritePaths=/run/controlstack-agent
[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/controlstack-agent.service').write_text(service)
# Replace only the stock live root's login hooks, never an operator home.
hook = '''if [ "$(tty)" = /dev/tty1 ] && [ "${CONTROLSTACK_SETUP_OPENED:-}" != 1 ]; then
  export CONTROLSTACK_SETUP_OPENED=1
  system-agent-setup
fi
'''
for name in ('.bash_profile', '.zlogin'):
    (Path('/root') / name).write_text(hook)
Path('/etc/motd').write_text('OpenClaw Arch installer. Setup opens on the first console.\nChoose Hyprland or no desktop during setup.\n')
Path('/etc/modules-load.d/controlstack-zfs.conf').write_text('zfs\n')
# Setup uses the same compiled console maps on both distro images.
maps = conf / 'keymaps'
maps.mkdir(exist_ok=True)
for layout, console in {'us':'us', 'gb':'uk', 'de':'de-latin1', 'fr':'fr', 'es':'es'}.items():
    # loadkeys accepts both plain and compressed maps. Store a plain map from kbd.
    result = subprocess.run(['loadkeys', '--mktable', console], capture_output=True, text=True)
    # This preview uses native map names in Setup.keyboard; no unverified generated map is shipped.
    if result.returncode:
        raise ValueError('Console map unavailable: ' + console)
