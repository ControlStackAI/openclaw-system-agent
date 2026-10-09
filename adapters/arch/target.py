"""Native Arch installed-system configuration, applied only to a fresh payload."""
import json
import os
import shutil
from pathlib import Path


def write(root, name, content, mode=0o644):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def script(root, name, content):
    write(root, 'usr/local/bin/' + name, '#!/bin/bash\nset -euo pipefail\n' + content, 0o755)


def configure(root, runtime, choices):
    # The setup screen intentionally uses umask 077 for secrets. Public system
    # configuration needs traversable parents for the desktop and service users.
    previous = os.umask(0o022)
    try:
        return _configure(root, runtime, choices)
    finally:
        os.umask(previous)


def _configure(root, runtime, choices):
    """Called by the root installer, never from the agent tool interface."""
    root = Path(root)
    owner = choices['username']
    desktop = choices['desktop'] == 'hyprland'
    from .owner_policy import configure as configure_owner_policy
    configure_owner_policy(root, runtime, choices)
    assets = Path(__file__).resolve().parents[1] / 'shared/hyprland'
    write(root, 'etc/hostname', choices['hostname'] + '\n')
    write(root, 'etc/locale.gen', choices['locale'] + ' UTF-8\n')
    write(root, 'etc/locale.conf', 'LANG=' + choices['locale'] + '\n')
    keymap = {'us': 'us', 'gb': 'uk', 'de': 'de-latin1', 'fr': 'fr', 'es': 'es'}[choices['keyboard']]
    write(root, 'etc/vconsole.conf', 'KEYMAP=' + keymap + '\n')
    (root / 'etc/localtime').unlink(missing_ok=True)
    (root / 'etc/localtime').symlink_to('/usr/share/zoneinfo/' + choices['timezone'])
    (root / 'etc/resolv.conf').unlink(missing_ok=True)
    (root / 'etc/resolv.conf').symlink_to('/run/NetworkManager/resolv.conf')
    write(root, 'etc/NetworkManager/conf.d/controlstack.conf', '[main]\ndns=default\n[device]\nwifi.backend=wpa_supplicant\n')
    write(root, 'etc/xdg/nvim/sysinit.vim', "lua dofile('/etc/xdg/nvim/controlstack.lua')\n")
    write(root, 'etc/xdg/nvim/controlstack.lua', "vim.opt.number = true\nvim.opt.relativenumber = true\nvim.opt.mouse = 'a'\nvim.opt.clipboard = 'unnamedplus'\nvim.opt.expandtab = true\nvim.opt.shiftwidth = 2\nvim.opt.tabstop = 2\n")
    write(root, 'etc/environment', 'EDITOR=nvim\nVISUAL=nvim\nTERMINAL=ghostty\nQT_QUICK_CONTROLS_STYLE=Basic\n')
    write(root, 'etc/sudoers.d/controlstack', '%wheel ALL=(ALL:ALL) ALL\n' + owner + ' ALL=(root) NOPASSWD: /usr/local/bin/system-agent-setup ""\n', 0o440)
    for name in ('openclaw', 'system-agent', 'system-agent-setup', 'system-agent-admin', 'system-agent-codex-login', 'system-agent-key', 'claude'):
        link = root / 'usr/local/bin' / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        link.symlink_to(runtime + '/bin/' + name)
    # Official Codex bundle includes its helper executables, separate from the desktop app.
    for name in ('codex', 'codex-code-mode-host'):
        (root / 'usr/local/bin' / name).symlink_to('/opt/codex/bin/' + name)
    for name in ('chatgpt', 'claude-desktop'):
        script(root, name, 'export LIBGL_DRIVERS_PATH="' + runtime + '/lib/dri"\nexec ' + runtime + '/bin/' + name + ' "$@"\n')
    # Desktop metadata/icons come from the same pinned GUI runtime.
    for directory in ('applications', 'icons'):
        source = Path(runtime) / 'share' / directory
        if source.exists():
            shutil.copytree(source, root / 'usr/local/share' / directory, dirs_exist_ok=True, symlinks=True)
    state = '/var/lib/controlstack-agent'
    env = '\n'.join('Environment=' + k + '=' + v for k, v in {
        'HOME': state, 'OPENCLAW_HOME': state, 'OPENCLAW_STATE_DIR': state,
        'OPENCLAW_CONFIG_PATH': state + '/openclaw.json', 'OPENCLAW_NIX_MODE': '0',
        'OPENCLAW_DISABLE_BONJOUR': '1', 'XDG_CACHE_HOME': state + '/cache',
        'XDG_CONFIG_HOME': state + '/config', 'XDG_DATA_HOME': state + '/data',
        'PATH': '/usr/local/bin:/usr/bin'}.items())
    write(root, 'etc/systemd/system/controlstack-agent.service', '''[Unit]
Description=ControlStackAI resident OpenClaw system agent
After=network.target
RequiresMountsFor=/var/lib/controlstack-agent
[Service]
User=controlstack-agent
Group=controlstack-agent
StateDirectory=controlstack-agent
StateDirectoryMode=0700
UMask=0077
''' + env + '''
ExecStartPre=/usr/local/bin/system-agent initialize
ExecStartPre=/usr/local/bin/system-agent local-policy
ExecStartPre=/usr/local/bin/system-agent refresh
ExecStart=/usr/local/bin/openclaw gateway run
CPUAccounting=true
MemoryAccounting=true
Restart=on-failure
RestartSec=5
TimeoutStopSec=120
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
ReadWritePaths=/var/lib/controlstack-agent
[Install]
WantedBy=multi-user.target
''')
    write(root, 'etc/systemd/system/controlstack-agent-boot-check.service', '''[Unit]
Description=Verify the installed ZFS root independently of model access
After=controlstack-agent.service
ConditionPathExists=/var/lib/controlstack-agent/lifecycle/installation.json
[Service]
Type=oneshot
User=controlstack-agent
''' + env + '''
ExecStart=/usr/local/bin/system-agent verify-boot
RemainAfterExit=true
[Install]
WantedBy=multi-user.target
''')
    mcp = {'hypruse': {'enabled': True, 'transport': 'stdio',
        'command': '/usr/local/bin/controlstack-hypruse-mcp', 'connectionTimeoutMs': 10000,
        'requestTimeoutMs': 60000, 'supportsParallelToolCalls': False,
        'codex': {'defaultToolsApprovalMode': 'approve'}}} if desktop else {}
    write(root, 'etc/controlstack-agent/installed-mcp.json', json.dumps(mcp) + '\n')
    write(root, 'etc/controlstack-agent/capabilities.json', '{"datasets":[],"pools":[],"services":[]}\n')
    write(root, 'etc/profile.d/controlstack.sh', '''export EDITOR=nvim VISUAL=nvim TERMINAL=ghostty
# Display managers also source profiles from non-interactive login shells.
case $- in *i*)
if [ "$(id -un)" = "''' + owner + '''" ] && [ -t 0 ] && [ "$(tty)" = /dev/tty1 ] && [ "${CONTROLSTACK_SETUP_OPENED:-}" != 1 ]; then
  export CONTROLSTACK_SETUP_OPENED=1
  sudo /usr/local/bin/system-agent-setup
fi
;; esac
''')
    if not desktop:
        return
    defaults = root / 'usr/share/controlstack/hyprland'
    shutil.copytree(assets, defaults, dirs_exist_ok=True)
    write(root, 'usr/share/controlstack/hyprland/hyprland.lua', (assets / 'hyprland.lua').read_text().replace('@keyboard@', choices['keyboard']))
    hint = 'Enter to touch YubiKey, or type password if enabled' if choices.get('login_policy') == 'yubikey' else 'Enter your account password'
    write(root, 'usr/share/controlstack/hyprland/hyprlock.conf', (assets / 'hyprlock.conf').read_text().replace('@unlock-hint@', hint).replace('size = 300, 60', 'size = 560, 60'))
    script(root, 'start-hyprland', '''cfg="${XDG_CONFIG_HOME:-$HOME/.config}"
mkdir -p "$cfg/hypr" "$cfg/quickshell/controlstack" "$cfg/ghostty" "$cfg/rofi"
seed() { if [ ! -e "$2" ]; then cp --no-clobber "$1" "$2"; chmod u+w "$2"; fi; }
base=/usr/share/controlstack/hyprland
for file in hyprland.lua hyprlock.conf hypridle.conf; do seed "$base/$file" "$cfg/hypr/$file"; done
for path in "$base/"*.qml "$base/Theme.js"; do seed "$path" "$cfg/quickshell/controlstack/$(basename "$path")"; done
seed "$base/ghostty.conf" "$cfg/ghostty/config"
seed "$base/rofi.rasi" "$cfg/rofi/config.rasi"
exec /usr/bin/start-hyprland "$@"
''')
    write(root, 'usr/share/wayland-sessions/controlstack-hyprland.desktop', '''[Desktop Entry]
Name=Hyprland + Quickshell
Comment=Customizable ControlStack desktop
Exec=uwsm start -e -D Hyprland -- /usr/local/bin/start-hyprland
Type=Application
DesktopNames=Hyprland
''')
    write(root, 'etc/greetd/config.toml', '[terminal]\nvt = 1\n[default_session]\nuser = "greeter"\ncommand = "/usr/local/bin/controlstack-greeter"\n')
    script(root, 'controlstack-greeter', 'export XKB_DEFAULT_LAYOUT=' + choices['keyboard'] + '\nexec /usr/bin/cage -s -- /usr/bin/gtkgreet -s /usr/share/controlstack/greeter.css -c Hyprland-Quickshell\n')
    script(root, 'Hyprland-Quickshell', 'exec uwsm start -e -D Hyprland -- /usr/local/bin/start-hyprland\n')
    write(root, 'usr/share/controlstack/greeter.css', (assets.parent / 'greeter.css').read_text())
    write(root, 'etc/xdg/autostart/controlstack-agent.desktop', '''[Desktop Entry]
Type=Application
Name=System Assistant
Comment=Talk to your resident computer assistant
Icon=computer
Categories=System;
Exec=ghostty --title="System Assistant" -e sudo /usr/local/bin/system-agent-setup
Terminal=false
''')
    write(root, 'usr/local/share/applications/controlstack-codex-sign-in.desktop', '''[Desktop Entry]
Type=Application
Name=Coding Assistant Sign-in
Comment=Connect Codex using your browser or a short device code
Icon=dialog-password
Categories=Development;
Exec=ghostty --title="Coding Assistant Sign-in" -e system-agent-codex-login
Terminal=false
''')
    shutil.copy2(root / 'etc/xdg/autostart/controlstack-agent.desktop', root / 'usr/local/share/applications/controlstack-agent.desktop')
    write(root, 'etc/xdg/gtk-3.0/settings.ini', '[Settings]\ngtk-application-prefer-dark-theme=1\ngtk-icon-theme-name=Papirus-Dark\ngtk-font-name=Inter 10\n')
    write(root, 'etc/xdg/mako/config', 'font=Inter 10\nbackground-color=#0d1b2ef0\ntext-color=#e4edf8\nborder-color=#29435f\nborder-size=1\nborder-radius=12\npadding=16\nmargin=12\nwidth=360\ndefault-timeout=7000\n')
    write(root, 'etc/xdg/mimeapps.list', '[Default Applications]\ntext/html=firefox.desktop\nx-scheme-handler/http=firefox.desktop\nx-scheme-handler/https=firefox.desktop\ntext/plain=nvim.desktop\nimage/png=imv.desktop\nimage/jpeg=imv.desktop\nimage/webp=imv.desktop\n')
    write(root, 'etc/xdg/xdg-desktop-portal/hyprland-portals.conf', '[preferred]\ndefault=hyprland;gtk\n')
    script(root, 'controlstack-desktop-status', 'exec python /usr/share/controlstack/hyprland/desktop-status.py\n')
    script(root, 'controlstack-desktop-menu', '''case "${1:-}" in
shortcuts) exec ghostty -e less /usr/share/controlstack/hyprland/shortcuts.txt ;;
search) rofi -dmenu -i -p 'Keyboard shortcuts' < /usr/share/controlstack/hyprland/shortcuts.txt >/dev/null || true ;;
power)
choice=$(printf '%s\\n' 'Cancel' 'Lock' 'Sign out' 'Restart' 'Power off' | rofi -dmenu -i -p Power) || exit 0
case "$choice" in
Lock) exec hyprlock ;; 'Sign out') exec uwsm stop ;;
Restart) exec systemctl reboot ;; 'Power off') exec systemctl poweroff ;; esac ;;
esac
''')
    script(root, 'controlstack-hypruse-mcp', 'exec socat STDIO UNIX-CONNECT:/run/controlstack-hypruse/mcp.sock\n')
    script(root, 'controlstack-desktop-control', '''case "${1:-}" in
start|stop) exec systemctl --user "$1" controlstack-hypruse.service ;;
*) echo 'Use start or stop' >&2; exit 2 ;; esac
''')
    # Keep the bridge source shared with NixOS; only its service integration differs.
    bridge = Path(__file__).resolve().parents[1] / 'shared/hypruse/bridge.py'
    write(root, 'usr/share/controlstack/hypruse-bridge.py', bridge.read_text())
    write(root, 'etc/tmpfiles.d/controlstack-desktop.conf', f'd /run/controlstack-hypruse 2750 {owner} controlstack-desktop -\n')
    units = {
        'shell': '/usr/bin/quickshell -c controlstack',
        'clipboard': '/usr/bin/wl-paste --type text --watch /usr/bin/cliphist store',
        'polkit': '/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1',
        'notifications': '/usr/bin/mako',
        'idle': '/usr/bin/hypridle',
        'hypruse': '/usr/bin/python /usr/share/controlstack/hypruse-bridge.py /run/controlstack-hypruse/mcp.sock ' + runtime + '/bin/hypruse controlstack-agent',
    }
    for name, command in units.items():
        unit = 'controlstack-' + name + '.service'
        extras = ''
        if name == 'hypruse':
            extras = '''Environment=HYPRUSE_READONLY=0 HYPRUSE_CLIPBOARD=1 HYPRUSE_SCREENSHOT_MODE=image HYPRUSE_AUTH_GUARD=1 HYPRUSE_MARK=1 HYPRUSE_JOURNAL=1
ExecStopPost=/usr/bin/rm -f /run/controlstack-hypruse/mcp.sock
KillMode=control-group
'''
        write(root, 'etc/systemd/user/' + unit, f'''[Unit]
Description=ControlStack {name}
ConditionUser={owner}
PartOf=graphical-session.target
After=graphical-session-pre.target
[Service]
ExecStart={command}
Environment=PATH=/usr/local/bin:/usr/bin
Restart=on-failure
RestartSec=2
UMask=0077
{extras}[Install]
WantedBy=graphical-session.target
''')
        link = root / 'etc/systemd/user/graphical-session.target.wants' / unit
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to('../' + unit)
