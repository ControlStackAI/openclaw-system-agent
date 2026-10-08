"""Local network setup with useful explanations before opening NetworkManager."""
import json
import os
import subprocess


def command(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=20, env=dict(os.environ, LC_ALL="C"))


def status():
    devices = command(['nmcli', '--terse', '--fields', 'DEVICE,TYPE,STATE', 'device', 'status'])
    if devices.returncode:
        return {'manager_ready': False, 'devices': [], 'radios': []}
    rows = [line.split(':', 2) for line in devices.stdout.splitlines()]
    rows = [dict(zip(('name', 'type', 'state'), row)) for row in rows if len(row) == 3 and row[1] != 'loopback']
    radio = command(['rfkill', '--json', '--output', 'TYPE,SOFT,HARD'])
    try:
        radios = json.loads(radio.stdout).get('rfkilldevices', []) if radio.returncode == 0 else []
    except (ValueError, AttributeError):
        radios = []
    return {'manager_ready': True, 'devices': rows, 'radios': radios}


def explain(report):
    if not report['manager_ready']:
        return 'The connection manager could not start. Open the troubleshooting shell or try restarting this USB session.'
    wlan = [r for r in report['radios'] if r.get('type') == 'wlan']
    if any(r.get('hard') in (True, 'blocked', 'yes') for r in wlan):
        return 'Wi-Fi is blocked by the computer. Turn off airplane mode using its wireless key or switch, then try again.'
    if not report['devices']:
        return ('No network adapter is available. “lo” is this computer talking to itself, not Wi-Fi. '
                'The wireless driver or firmware may not have started. Try a USB Ethernet adapter or phone USB tethering; '
                'then the assistant can help investigate. No sign-in is needed to retry network setup.')
    if any(r.get('soft') in (True, 'blocked', 'yes') for r in wlan):
        return 'Wi-Fi is switched off in software. Network setup will try turning it on.'
    if not any(d['type'] == 'wifi' for d in report['devices']):
        return 'No Wi-Fi adapter is available yet. Ethernet or phone USB tethering can still provide a connection.'
    if any(d['type'] == 'wifi' and d['state'] == 'unavailable' for d in report['devices']):
        return 'The Wi-Fi adapter was found but is not ready. Network setup will turn on Wi-Fi; if it stays unavailable, its driver or Wi-Fi service needs investigation.'
    return 'Choose Activate a connection, select your network, and enter its password in the protected prompt.'


def connect():
    started = command(['systemctl', 'start', 'NetworkManager.service', 'systemd-timesyncd.service'])
    if started.returncode:
        print('Network services could not start. You can retry or open the troubleshooting shell.')
        return False
    report = status()
    print(explain(report), flush=True)
    # Selecting Connect authorizes enabling Wi-Fi, not changing saved passwords.
    command(['rfkill', 'unblock', 'wlan'])
    command(['nmcli', 'radio', 'wifi', 'on'])
    if not report['manager_ready'] or not report['devices']:
        return False
    return subprocess.run(['nmtui']).returncode == 0
