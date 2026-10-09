#!/usr/bin/env python3
"""Boot the real hybrid ISO as USB; attach only disposable regular-file disks."""
import argparse
import base64
import hashlib
import json
import os
import shutil
import shlex
import socket
import subprocess
import time
import tempfile
from pathlib import Path
import pexpect

ROOT = Path(__file__).resolve().parents[1]


class Guest:
    def __init__(self, iso, area, uefi=False, installed=False, offline=False, encrypted=False, memory=4096, keyboard="us", gpu="std", live_login=False):
        self.keyboard = keyboard
        self.area = area
        self.control = tempfile.TemporaryDirectory(prefix="cs-iso-", dir="/tmp")
        self.socket_path = Path(self.control.name) / "qmp.sock"
        self.log = (area / ("installed.log" if installed else "live.log")).open("a")
        args = ["-vga", gpu, "-machine", "q35", "-m", str(memory), "-smp", "2", "-display", "none", "-monitor", "none",
                "-device", "qemu-xhci,id=xhci", "-device", "usb-tablet,bus=xhci.0",
                "-chardev", "stdio,id=serial0,signal=off", "-serial", "chardev:serial0", "-qmp", f"unix:{self.socket_path},server=on,wait=off",
                "-nic", "none" if offline else "user,model=virtio-net-pci", "-no-reboot"]
        if os.access("/dev/kvm", os.R_OK | os.W_OK):
            args += ["-enable-kvm", "-cpu", "host"]
        else:
            args += ["-accel", "tcg", "-cpu", "max"]
        if not installed:
            args += ["-drive", f"if=none,id=live,format=raw,readonly=on,file={iso}",
                     "-device", "usb-storage,drive=live,bootindex=1"]
        if uefi and not installed:
            extra_usb = area / "extra-usb.raw"
            with extra_usb.open("wb") as stream:
                stream.truncate(128 * 1024 * 1024)
            args += ["-drive", f"if=none,id=extrausb,format=raw,file={extra_usb}",
                     "-device", "usb-storage,drive=extrausb,serial=CS_FIXTURE_USB,bootindex=3"]
        if uefi:
            firmware = Path(os.environ.get("CONTROLSTACK_OVMF_DIR", "/usr/share/OVMF"))
            code = firmware / "OVMF_CODE_4M.fd"
            variables = area / "OVMF_VARS.fd"
            if not variables.exists():
                shutil.copyfile(firmware / "OVMF_VARS_4M.fd", variables)
            args += ["-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                     "-drive", f"if=pflash,format=raw,file={variables}"]
            disk = area / "target.qcow2"
            if not disk.exists():
                subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "48G"], check=True)
            args += ["-drive", f"if=none,id=target,format=qcow2,file={disk}",
                     "-device", "virtio-blk-pci,drive=target,serial=CONTROLSTACK-VM-ONLY,bootindex=2"]
        self.process = pexpect.spawn("qemu-system-x86_64", args, encoding="utf-8", codec_errors="replace", timeout=300)
        self.process.logfile = self.log
        self.count = 0
        try:
            if installed and encrypted:
                # Only the disposable test disk uses this public fixture passphrase.
                time.sleep(30)
                self.qmp("screendump", {"filename": str(area / "unlock.png"), "format": "png"})
                self.type_console("vmencryptiontest")
            if installed:
                self.process.expect("login:")
                self.process.sendline("owner")
                self.process.expect("Password:")
                self.process.sendline("vmonlytestpassword")
                self.process.expect(r"owner@[^\r\n]*\$")
                self.process.sendline("sudo -i")
                self.process.expect("password for owner:")
                self.process.sendline("vmonlytestpassword")
            if live_login and not installed:
                self.process.expect("login:")
                self.process.sendline("root")
            self.process.expect(r"root[^\r\n]*@[^\r\n]*#")
            if live_login or installed:
                self.process.sendline("exec bash --noprofile --norc")
                self.process.expect(r"bash-[0-9.]+#")
            self.process.sendline("bind 'set enable-bracketed-paste off'; stty -echo; umask 077; export PS1='CS_READY> '")
            self.process.expect(r"[\r\n]CS_READY> ")
        except Exception:
            try:
                if self.process.isalive():
                    self.qmp("screendump", {"filename": str(area / "boot-failure.png"), "format": "png"})
            finally:
                self.process.terminate(force=True)
                self.log.close()
                self.control.cleanup()
            raise

    def command(self, command, timeout=300):
        self.count += 1
        marker = f"CS_DONE_{self.count}"
        self.process.sendline(command + (" " if command.rstrip().endswith("&") else "; ") + f"printf '\\n{marker}:%s\\n' \"$?\"")
        try:
            self.process.expect(marker + r":(\d+)", timeout=timeout)
        except pexpect.TIMEOUT:
            self.process.sendcontrol("c")
            self.process.expect("CS_READY> ", timeout=30)
            raise
        output = self.process.before
        if self.process.match.group(1) != "0":
            raise RuntimeError(f"Guest command failed: {command}\n{output[-4000:]}")
        self.process.expect("CS_READY> ")
        return output

    def gateway_ready(self, state):
        probe = ("runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=" + state +
                 " OPENCLAW_CONFIG_PATH=" + state + "/openclaw.json OPENCLAW_NIX_MODE=0 system-agent health")
        self.command("timeout 120 bash -c " + shlex.quote(
            "until " + probe + " >/tmp/gateway-health.log 2>&1; do sleep 2; done") +
            " || { journalctl -b -u controlstack-agent --no-pager -n 100; cat /tmp/gateway-health.log; exit 1; }", timeout=180)

    def put(self, path, data):
        payload = base64.b64encode(data.encode()).decode()
        self.command(f"echo {payload} | base64 -d > {path}")

    def qmp(self, execute, arguments):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(30)
            sock.connect(str(self.socket_path))
            with sock.makefile("rwb", buffering=0) as stream:
                stream.readline()
                for command in ({"execute": "qmp_capabilities"}, {"execute": execute, "arguments": arguments}):
                    stream.write(json.dumps(command).encode() + b"\n")
                    while True:
                        response = json.loads(stream.readline())
                        if "error" in response:
                            raise RuntimeError(response)
                        if "return" in response:
                            break

    def screen_text(self):
        screen = self.area / "screen.png"
        self.qmp("screendump", {"filename": str(screen), "format": "png"})
        return subprocess.run(["tesseract", str(screen), "stdout", "--psm", "11"],
                              capture_output=True, text=True, check=True).stdout

    def focus_assistant(self):
        # The sole application occupies the screen center, both in GNOME's
        # overview thumbnail and on the desktop. Select it as an owner would.
        self.qmp("input-send-event", {"events": [
            {"type": "abs", "data": {"axis": "x", "value": 16383}},
            {"type": "abs", "data": {"axis": "y", "value": 13107}},
            {"type": "btn", "data": {"down": True, "button": "left"}},
        ]})
        time.sleep(0.1)
        self.qmp("input-send-event", {"events": [
            {"type": "btn", "data": {"down": False, "button": "left"}},
        ]})
        time.sleep(1)

    def wait_screen_text(self, expected, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if " ".join(expected.casefold().split()) in " ".join(self.screen_text().casefold().replace("usemame", "username").split()):
                return
            time.sleep(2)
        raise RuntimeError("Graphical screen did not show: " + expected)

    def type_console(self, text):
        for key in text:
            shifted = key.isupper()
            key = key.lower()
            if self.keyboard == "de" and key in "yz":
                key = "z" if key == "y" else "y"
            code = {"-": "minus", " ": "spc", "/": "slash", ".": "dot"}.get(key, key)
            keys = ([{"type": "qcode", "data": "shift"}] if shifted else [])
            keys.append({"type": "qcode", "data": code})
            self.qmp("send-key", {"keys": keys, "hold-time": 50})
            time.sleep(0.08)
        self.qmp("human-monitor-command", {"command-line": "sendkey ret"})
        time.sleep(0.5)

    def close(self):
        if self.process.isalive():
            self.process.sendcontrol("c")
            time.sleep(0.2)
            self.process.sendline("poweroff")
            try:
                self.process.expect(pexpect.EOF, timeout=60)
            except pexpect.TIMEOUT:
                self.process.terminate(force=True)
        self.process.close()
        self.log.close()
        self.control.cleanup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("--mode", choices=["bios-offline", "uefi-install"], required=True)
    parser.add_argument("--distro", choices=["nixos", "arch"], default="nixos")
    parser.add_argument("--desktop", choices=["none", "plasma", "gnome", "hyprland"], default="none")
    parser.add_argument("--encrypted", action="store_true")
    parser.add_argument("--keyboard", choices=["us", "de"], default="us")
    parser.add_argument("--memory-mib", type=int, help="Guest RAM; use at least 8192 to cover Arch automatic copy-to-RAM behavior")
    args = parser.parse_args()
    if args.memory_mib is not None and args.memory_mib < 2048:
        parser.error("VM qualification requires at least 2048 MiB of guest RAM")
    iso = args.iso.resolve()
    if not iso.is_file():
        parser.error("ISO must be a regular file")
    area = ROOT / ".build/iso-test" / (args.distro + "-" + args.mode + "-" + args.desktop + ("-encrypted" if args.encrypted else "") + "-" + args.keyboard)
    area.mkdir(parents=True, exist_ok=True)
    # Each invocation needs a genuinely blank target and firmware, never a resumed result.
    for name in ("target.qcow2", "OVMF_VARS.fd", "result.json", "qmp.sock"):
        (area / name).unlink(missing_ok=True)
    installing = args.mode == "uefi-install"
    memory = args.memory_mib or (4096 if args.desktop == "none" else 8192)
    guest = Guest(iso, area, uefi=installing, offline=not installing, memory=memory, keyboard=args.keyboard, gpu="virtio" if args.desktop == "hyprland" else "std", live_login=args.distro == "arch")
    try:
        guest.command("system-agent inspect | grep '\"phase\": \"live\"'")
        guest.command("timeout 180 bash -c 'until systemctl is-active --quiet NetworkManager && systemctl is-active --quiet controlstack-agent; do sleep 2; done'")
        guest.command("systemctl start wpa_supplicant.service; systemctl is-active wpa_supplicant.service")
        guest.command("test $(findmnt -n -o FSTYPE /run) = tmpfs")
        guest.command("test $(stat -c %a /run/controlstack-agent/gateway-token) = 600")
        guest.command("openclaw --version | grep -F " + ("2026.9.9" if args.distro == "arch" else "2026.9.5"))
        if args.distro == "arch":
            guest.command("grep -w copytoram=n /proc/cmdline && test -f /run/archiso/bootmnt/arch/controlstack/target.sfs")
            guest.command("test $(stat -Lc %u /usr/local/bin/openclaw) = 0; test -x /opt/codex/bin/codex-code-mode-host")
        guest.command("openclaw onboard --help > /tmp/onboard-help; for flag in --skip-daemon --skip-health --skip-ui --skip-skills --skip-channels --skip-bootstrap --skip-hooks --skip-search; do grep -q -- $flag /tmp/onboard-help || exit 1; done")
        guest.command("cat /dev/vcs1 | grep 'Welcome to your OpenClaw'")
        guest.qmp("screendump", {"filename": str(area / "welcome.png"), "format": "png"})
        if args.keyboard == "de":
            guest.type_console("6")
            time.sleep(1)
            guest.type_console("3")
            guest.command("sleep 2; runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent system-agent setup-choice | grep '\"keyboard\": \"de\"'")
        if not installing:
            # Change the real live-console font through the shipped setup menu.
            guest.type_console("7")
            guest.command("cat /dev/vcs1 | grep -a 'Text size for this USB session'")
            guest.type_console("3")
            guest.command("cat /dev/vcs1 | grep -a 'Keep this text size'")
            guest.type_console("1")
            guest.command("sleep 1; cat /dev/vcs1 | grep -a 'Text size saved'; grep -q '20' /run/controlstack-console/tty1.json")
            guest.qmp("screendump", {"filename": str(area / "text-size-large.png"), "format": "png"})
            guest.type_console("")
            # Return to Standard before the existing offline checks.
            guest.type_console("7")
            guest.type_console("2")
            guest.type_console("1")
            guest.command("sleep 1; grep -q '16' /run/controlstack-console/tty1.json")
            guest.type_console("")
            guest.qmp("human-monitor-command", {"command-line": "sendkey 1"})
            guest.qmp("human-monitor-command", {"command-line": "sendkey ret"})
            guest.command("sleep 20; cat /dev/vcs1 | grep 'Internet check failed'", timeout=90)
            guest.qmp("screendump", {"filename": str(area / "offline.png"), "format": "png"})
            # Reproduce the hardware report: failed sign-in first, then networking.
            # This VM intentionally has no NIC. Show a useful explanation, not an
            # empty nmtui listing containing only loopback.
            guest.type_console("3")  # back from readiness to the main menu
            guest.type_console("3")  # connect
            guest.command("sleep 2; cat /dev/vcs1 | grep -F 'No network adapter is available'")
            guest.qmp("screendump", {"filename": str(area / "network-help.png"), "format": "png"})
        else:
            guest.put("/tmp/provider.py", (ROOT / "tests/fixture_provider.py").read_text())
            guest.command("python3 /tmp/provider.py >/tmp/provider.log 2>&1 &")
            # Only this automated fixture uses an argv key; it is not an account credential.
            # The shipped UI uses the official interactive protected input prompts.
            live_env = "runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent OPENCLAW_CONFIG_PATH=/run/controlstack-agent/openclaw.json OPENCLAW_NIX_MODE=0 "
            guest.command(live_env + "openclaw onboard --non-interactive --accept-risk --mode local --skip-daemon --skip-health --skip-ui --skip-skills --skip-channels --skip-bootstrap --skip-hooks --skip-search --auth-choice custom-api-key --custom-base-url http://127.0.0.1:18080/v1 --custom-model-id fixture-model --custom-provider-id fixture --custom-compatibility openai --custom-api-key non-secret-vm-fixture", timeout=180)
            guest.command(live_env + "system-agent local-policy")
            guest.command("systemctl restart controlstack-agent")
            guest.gateway_ready("/run/controlstack-agent")
            guest.command(live_env + "openclaw agent --agent main --session-key agent:main:live-fixture --message live-fixture-response --json", timeout=180)
            if args.distro == "nixos":
                guest.command(live_env + "timeout --foreground --kill-after=5s 60s openclaw mcp doctor nixos --probe --json </dev/null", timeout=90)
                guest.command("python3 -c \"import json; c=json.load(open('/run/controlstack-agent/openclaw.json')); assert set(c['mcp']['servers']) == {'nixos'}; r=json.load(open('/tmp/fixture-request.json')); names={t['function']['name'] for t in r['tools']}; assert 'nixos__nix' in names; assert not any(n.startswith('hypruse__') for n in names)\"")
            else:
                guest.command("python3 -c \"import json; c=json.load(open('/run/controlstack-agent/openclaw.json')); assert not c.get('mcp', {}).get('servers', {})\"")
            # Exercise the actual gateway tool against a separate emulated USB.
            # The serial belongs only to the blank regular-file drive attached above.
            guest.command("set -- /dev/disk/by-id/usb-*CS_FIXTURE_USB*; test $# = 1 && usb=$(readlink -f \"$1\"); test -b \"$usb\" && test $(blockdev --getsize64 \"$usb\") = 134217728 && mkfs.ext4 -L CS_FIXTURE_USB \"$usb\" && mkdir -p /mnt/seed && mount \"$usb\" /mnt/seed && echo usb-readable > /mnt/seed/sentinel && umount /mnt/seed")
            guest.command(live_env + "system-agent inspect | grep '\"root_command_verified\": true'")
            guest.command(live_env + "openclaw agent --agent main --session-key agent:main:usb-fixture --message live-usb-access-fixture --json", timeout=180)
            guest.command("findmnt -n /mnt/controlstack-usb-fixture; grep -x usb-readable /mnt/controlstack-usb-fixture/sentinel")
            guest.command(live_env + "sudo -n umount /mnt/controlstack-usb-fixture")
            guest.command(live_env + "system-agent setup-choice hostname vmresident")
            guest.command(live_env + "system-agent name-agent Luna")
            # Isolated tests have no real FIDO key or external release registry.
            guest.command(live_env + "system-agent setup-choice login_policy password")
            guest.command(live_env + "system-agent setup-choice openclaw_release image-pinned")
            guest.command("install -m 600 /dev/null /run/controlstack-agent/live-only-credential-fixture")
            # Drive the shipped local review screen, including separate disk approval.
            # Drive the shipped Ratatui interface on the primary console.
            def answer(prompt, value, timeout=60):
                quoted=shlex.quote(prompt)
                guest.command("timeout " + str(timeout) + " bash -c " + shlex.quote(
                    "until grep -Fq -- " + quoted + " /dev/vcs1; do "
                    "if grep -Fq 'That step did not finish:' /dev/vcs1; then cat /dev/vcs1; exit 1; fi; "
                    "sleep 1; done"), timeout=timeout+10)
                guest.type_console(value)
                time.sleep(.5)
            answer("What would you like to do?", "2")
            guest.command("timeout 120 bash -c " + shlex.quote("until pgrep -u controlstack-agent -f '[s]ystem_agent chat'; do sleep 1; done"), timeout=130)
            guest.command(live_env + "system-agent install-status | grep root-local-console")
            guest.command(live_env + "system-agent request-install")
            answer("Use these choices", "1")
            answer("What will you mainly", "1")
            answer("Name for your local account", "owner")
            answer("Which desktop", str((["none", "plasma", "gnome", "hyprland"] if args.distro == "nixos" else ["hyprland", "none"]).index(args.desktop) + 1))
            answer("Which system language", "1")
            if args.keyboard != "de":
                answer("Which keyboard layout?", "1")
            answer("Which city should", "UTC")
            answer("Encrypt your files?", "1" if args.encrypted else "2")
            answer("Would you like to change anything?", "1")
            answer("Do you have a disk", "2")
            answer("Which disk should hold", "1")
            # Wait for the prepared target and separate exact disk approval.
            guest.command("timeout 900 bash -c " + shlex.quote("until grep -Fq 'Type ERASE CONTROLSTACK-VM-ONLY' /dev/vcs1; do sleep 2; done"),timeout=920)
            guest.qmp("screendump", {"filename":str(area/"ratatui-disk-review.png"),"format":"png"})
            answer("Type ERASE CONTROLSTACK-VM-ONLY", "ERASE TYPO")
            answer("Try the disk confirmation again?", "1")
            answer("Type ERASE CONTROLSTACK-VM-ONLY", "ERASE CONTROLSTACK-VM-ONLY")
            answer("Password for your local account", "vmonlytestpassword")
            answer("Enter it again:", "vmonlytestpassword")
            if args.encrypted:
                answer("Disk unlock passphrase", "vmencryptiontest")
                answer("Enter it again:", "vmencryptiontest")
            answer("Ready to shut down", "2", timeout=900)
            guest.command("timeout 120 bash -c " + shlex.quote("until " + live_env + "system-agent install-status | grep installed-awaiting-reboot; do sleep 1; done"), timeout=130)
            guest.command("timeout 120 bash -c " + shlex.quote("until pgrep -u controlstack-agent -f '[s]ystem_agent chat --resume-install'; do sleep 1; done"), timeout=130)
            guest.process.sendline("poweroff")
            guest.process.expect(pexpect.EOF, timeout=60)

    finally:
        guest.close()
    if installing:
        guest = Guest(iso, area, uefi=True, installed=True, encrypted=args.encrypted, memory=memory, keyboard=args.keyboard, gpu="virtio" if args.desktop == "hyprland" else "std")
        try:
            guest.command("findmnt -n -o FSTYPE / | grep -x zfs")
            guest.put('/tmp/verify-floor.py', 'import json\nfrom pathlib import Path\nfrom system_agent.deployment import verify\nr=verify(Path("/"), ' + repr({'distro': args.distro, 'username': 'owner'}) + ')\nprint(json.dumps(r,indent=2))\nassert r["boot_floor_passed"]\n')
            guest.command('core=$(readlink -f $(command -v system-agent)); PYTHONPATH=$(dirname $(dirname "$core"))/lib/system-agent python3 /tmp/verify-floor.py')
            guest.command("systemctl start wpa_supplicant.service; systemctl is-active wpa_supplicant.service")
            guest.command("test ! -e /etc/agent-installer/live-image; test ! -e /etc/controlstack-agent/live-system-access.json; ! runuser -u controlstack-agent -- sudo -n id -u")
            if args.desktop != "none":
                guest.command("test -r " + ("/run/current-system/sw" if args.distro == "nixos" else "/usr/local") + "/share/applications/controlstack-agent.desktop")
            guest.command("timeout 180 bash -c 'until systemctl is-active --quiet controlstack-agent; do sleep 2; done'; systemctl is-active controlstack-agent controlstack-agent-boot-check || { journalctl -b -u controlstack-agent -u controlstack-agent-boot-check --no-pager; exit 1; }")
            guest.command("test ! -e /var/lib/controlstack-agent/live-only-credential-fixture")
            guest.command("! grep -q non-secret-vm-fixture /var/lib/controlstack-agent/openclaw.json")
            guest.command(f"grep 'desktop: {args.desktop}' /var/lib/controlstack-agent/workspace/USER.md")
            guest.command("grep 'purpose: development' /var/lib/controlstack-agent/workspace/USER.md")
            guest.command("grep -x 'Name: Luna' /var/lib/controlstack-agent/workspace/IDENTITY.md")
            if args.desktop != "none":
                guest.command("timeout 180 bash -c 'until systemctl is-active --quiet " + ("greetd" if args.desktop == "hyprland" else "display-manager") + "; do sleep 2; done'")
            if args.encrypted:
                guest.command("zfs get -H -o value encryption $(findmnt -n -o SOURCE /) | grep -x aes-256-gcm")
            guest.command("grep '\"installed_boot_verified\": true' /var/lib/controlstack-agent/lifecycle/boot-verification.json")
            guest.qmp("screendump", {"filename": str(area / "login.png"), "format": "png"})
            if args.desktop == "none":
                guest.type_console("owner")
                time.sleep(3)
            else:
                if args.desktop == "hyprland":
                    guest.command("systemctl is-active greetd; pgrep -x gtkgreet; ! systemctl is-active --quiet sddm")
                    guest.wait_screen_text("Username")
                    guest.type_console("owner")
                    guest.wait_screen_text("Password")
                else:
                    guest.wait_screen_text("owner")
                if args.desktop == "gnome":
                    guest.qmp("human-monitor-command", {"command-line": "sendkey ret"})
                    guest.command("timeout 60 bash -c 'until pgrep -f \"[p]am/gdm-password\"; do sleep 1; done'")
                    time.sleep(2)
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-a"})
            guest.type_console("vmonlytestpassword")
            guest.command("timeout 120 bash -c 'until pgrep -u root -f \"[p]ython3.*system_agent.setup\"; do sleep 2; done'")
            if args.desktop == "none":
                guest.command("cat /dev/vcs1 | grep 'OpenClaw is installed on this computer'")
            else:
                shell_name = {"gnome": "gnome-shell", "plasma": "plasmashell", "hyprland": "Hyprland"}[args.desktop]
                shell_probe = "pgrep -u owner -x Hyprland" if args.distro == "arch" else "pgrep -u owner -f '/bin/[^ ]*" + shell_name + "'"
                guest.command("timeout 120 bash -c " + shlex.quote("until " + shell_probe + "; do sleep 2; done"))

            if args.desktop == "hyprland":
                owner_env = "runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
                guest.command(owner_env + "systemctl --user is-active graphical-session.target controlstack-shell controlstack-polkit controlstack-notifications " + ("hypridle" if args.distro == "nixos" else "controlstack-idle"))
                guest.command("runuser -u owner -- test -w /home/owner/.config/quickshell/controlstack/shell.qml")
                guest.command("test -s /home/owner/.config/hypr/hyprland.lua")
                guest.command(owner_env + "systemd-run --user --quiet --wait --pipe hyprctl -j configerrors > /tmp/hypr-errors.json")
                guest.command("python3 -c " + shlex.quote("import json; errors = json.load(open('/tmp/hypr-errors.json')); assert not any(line.strip() for line in errors), errors"))
                guest.wait_screen_text("OpenClaw")
                guest.qmp("human-monitor-command", {"command-line": "sendkey meta_l-r"})
                guest.wait_screen_text("Applications")
                guest.qmp("screendump", {"filename": str(area / "launcher.png"), "format": "png"})
                guest.type_console("mousepad")
                guest.command("timeout 60 bash -c " + shlex.quote("until pgrep -u owner -f '[m]ousepad'; do sleep 1; done"))
                focused_app = owner_env + "systemd-run --user --quiet --wait --pipe hyprctl -j activewindow"
                check_mousepad = "import json,sys; assert 'mousepad' in json.load(sys.stdin).get('class', '').lower()"
                guest.command("timeout 60 bash -c " + shlex.quote("until " + focused_app + " | python3 -c " + shlex.quote(check_mousepad) + "; do sleep 1; done"))
                guest.qmp("human-monitor-command", {"command-line": "sendkey meta_l-c"})
                guest.wait_screen_text("What would you like to do?")
                ui = owner_env + "systemd-run --user --quiet --wait --pipe quickshell -c controlstack ipc call shell "
                guest.command(ui + "monitor")
                guest.wait_screen_text("Resident system agent")
                guest.command("systemctl stop controlstack-agent")
                guest.wait_screen_text("Stopped")
                guest.command("systemctl start controlstack-agent")
                guest.wait_screen_text("Running")
                guest.qmp("screendump", {"filename": str(area / "monitor.png"), "format": "png"})
                guest.command(ui + "controls")
                guest.wait_screen_text("Microphone")
                guest.qmp("screendump", {"filename": str(area / "audio.png"), "format": "png"})
                guest.command(ui + "network")
                guest.wait_screen_text("Ethernet")
                guest.qmp("screendump", {"filename": str(area / "network.png"), "format": "png"})
                guest.qmp("human-monitor-command", {"command-line": "sendkey esc"})
                guest.wait_screen_text("What would you like to do?")
                guest.command("runuser -l owner -c 'set -e; test \"$EDITOR\" = nvim; codex --version; claude --version; nvim --headless +qall'")
                guest.command("! journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager | grep -E 'Failed to load configuration|ReferenceError|TypeError'")

            guest.put("/tmp/provider.py", (ROOT / "tests/fixture_provider.py").read_text())
            guest.command("python3 /tmp/provider.py >/tmp/provider.log 2>&1 &")
            guest.put("/tmp/provider-config.py", '''import json
from pathlib import Path
p=Path('/var/lib/controlstack-agent/openclaw.json')
c=json.loads(p.read_text())
c['agents']['defaults']['model']={'primary':'fixture/fixture-model'}
c['models']={'providers':{'fixture':{'baseUrl':'http://127.0.0.1:18080/v1','api':'openai-completions','apiKey':'non-secret-vm-fixture','models':[{'id':'fixture-model','name':'VM fixture','contextWindow':32768,'maxTokens':1024}]}}}
p.write_text(json.dumps(c))
''')
            guest.command("python3 /tmp/provider-config.py; systemctl restart controlstack-agent")
            guest.gateway_ready("/var/lib/controlstack-agent")
            guest.command("runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/var/lib/controlstack-agent OPENCLAW_CONFIG_PATH=/var/lib/controlstack-agent/openclaw.json OPENCLAW_NIX_MODE=0 openclaw agent --agent main --session-key agent:main:installed --message installed-fixture-response --json", timeout=180)
            guest.command("grep -q 'Owner.s chosen system' /tmp/fixture-request.json")
            if args.distro == "nixos":
                guest.command("python3 -c \"import json; r=json.load(open('/tmp/fixture-request.json')); assert 'nixos__nix' in {t['function']['name'] for t in r['tools']}\"")
            else:
                guest.command("python3 -c \"import json; r=json.load(open('/tmp/fixture-request.json')); assert not any(t['function']['name'].startswith('nixos__') for t in r['tools'])\"")
            if args.desktop == "hyprland":
                if args.distro == "arch":
                    guest.command("python3 -c \"import json; r=json.load(open('/tmp/fixture-request.json')); calls={c['id']:c['function']['name'] for m in r['messages'] for c in (m.get('tool_calls') or [])}; results=[m for m in r['messages'] if m.get('role') == 'tool']; search=[m for m in results if calls.get(m.get('tool_call_id')) == 'tool_search']; desktop=[m for m in results if calls.get(m.get('tool_call_id')) == 'tool_call']; assert 'hypruse__desktop' in json.dumps(search); assert desktop and 'monitors' in json.dumps(desktop) and 'windows' in json.dumps(desktop), desktop\"")
                else:
                    guest.command("python3 -c \"import json; r=json.load(open('/tmp/fixture-request.json')); assert 'hypruse__desktop' in {t['function']['name'] for t in r['tools']}\"")

            if args.desktop == "none":
                guest.type_console("2")
                guest.command("timeout 120 bash -c 'until grep -q \"resident conversation works\" /dev/vcs1; do sleep 2; done'")
                guest.qmp("screendump", {"filename": str(area / "conversation.png"), "format": "png"})
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-d"})
                guest.command("sleep 3; grep -q \"What would you like to do?\" /dev/vcs1")

            if args.desktop != "none":
                if args.desktop == "gnome":
                    # Dismiss GNOME's first-login tour dialog. The overview can
                    # remain afterward, so select the assistant window below.
                    guest.qmp("human-monitor-command", {"command-line": "sendkey esc"})
                    time.sleep(1)
                guest.wait_screen_text("What would you like to do?")
                guest.focus_assistant()
                guest.type_console("2")
                guest.wait_screen_text("resident conversation works")
                guest.qmp("screendump", {"filename": str(area / "conversation.png"), "format": "png"})
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-d"})
                guest.wait_screen_text("What would you like to do?")

            guest.qmp("screendump", {"filename": str(area / "installed.png"), "format": "png"})
            if args.desktop == "hyprland":
                # Invoke the same Quickshell action used by the panel's lock button.
                # This runs from its user service, without a login-session ID.
                guest.command(owner_env + "systemd-run --user --quiet --wait --pipe quickshell -c controlstack ipc call shell lock")
                lock_status = owner_env + "systemd-run --user --quiet --wait --pipe hyprctl locked"
                guest.command("timeout 60 bash -c " + shlex.quote("until " + lock_status + " | grep -qx true; do sleep 1; done"))
                time.sleep(2)
                guest.qmp("screendump", {"filename": str(area / "locked.png"), "format": "png"})
                guest.type_console("vmonlytestpassword")
                guest.command("timeout 60 bash -c " + shlex.quote("until " + lock_status + " | grep -qx false; do sleep 1; done"))
                guest.wait_screen_text("What would you like to do?")
                guest.command("printf '\\n// owner customization survives reboot\\n' >> /home/owner/.config/quickshell/controlstack/shell.qml")
                guest.command("cat /proc/sys/kernel/random/boot_id > /home/owner/desktop-test-boot-id")
                guest.close()
                guest = Guest(iso, area, uefi=True, installed=True, encrypted=args.encrypted,
                              memory=memory, keyboard=args.keyboard, gpu="virtio")
                guest.command("test $(cat /proc/sys/kernel/random/boot_id) != $(cat /home/owner/desktop-test-boot-id)")
                if args.desktop == "hyprland":
                    guest.command("systemctl is-active greetd; pgrep -x gtkgreet; ! systemctl is-active --quiet sddm")
                    guest.wait_screen_text("Username")
                    guest.type_console("owner")
                    guest.wait_screen_text("Password")
                else:
                    guest.wait_screen_text("owner")
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-a"})
                guest.type_console("vmonlytestpassword")
                guest.wait_screen_text("OpenClaw")
                guest.wait_screen_text("What would you like to do?")
                guest.command("grep -q 'owner customization survives reboot' /home/owner/.config/quickshell/controlstack/shell.qml")
                guest.command(owner_env + "systemctl --user is-active controlstack-shell graphical-session.target")
                guest.command("grep '\"installed_boot_verified\": true' /var/lib/controlstack-agent/lifecycle/boot-verification.json")
                guest.qmp("screendump", {"filename": str(area / "desktop-reboot.png"), "format": "png"})
        except Exception:
            if guest.process.isalive():
                guest.qmp("screendump", {"filename": str(area / "installed-failure.png"), "format": "png"})
                print(guest.command("journalctl -b -u display-manager -u controlstack-agent --no-pager -n 100; journalctl -b _UID=1000 --no-pager -n 160; loginctl list-sessions; ps -eo user,comm,args | grep -E 'sddm|gdm|plasmashell|gnome-shell|Hyprland|quickshell|xterm|system_agent.setup' || true")[-22000:], flush=True)
            raise
        finally:
            guest.close()
    with iso.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = {"distro": args.distro, "mode": args.mode, "iso_sha256": digest, "passed": True,
               "live_wifi_backend_available": True,
               "installed_wifi_backend_available": installing,
               "offline_signin_then_network_setup": not installing,
               "live_console_text_size": not installing,
               "live_nixos_mcp_discovery": installing and args.distro == "nixos", "live_hypruse_disabled": installing,
               "installed_nixos_mcp_discovery": installing and args.distro == "nixos",
               "installed_hypruse_mcp_discovery": installing and args.desktop == "hyprland",
               "live_gateway_usb_mount": installing, "agent_requested_installation": installing,
               "same_conversation_resumed_after_install": installing,
               "live_sudo_absent_from_installed_system": installing,
               "installation": installing, "disk_boot_without_iso": installing, "custom_boot_floor_on_zfs": installing, "ram_mib": memory,
               "desktop": args.desktop, "encryption": args.encrypted, "keyboard": args.keyboard, "graphical_owner_login": installing and args.desktop != "none",
               "greetd_gtkgreet_login": installing and args.desktop == "hyprland",
               "installed_setup_autostart": installing,
               "quickshell_panel_and_launcher": installing and args.desktop == "hyprland",
               "quickshell_launcher_opens_application": installing and args.desktop == "hyprland",
               "desktop_customization_survives_reboot": installing and args.desktop == "hyprland",
               "resident_monitor_tracks_service_stop_start": installing and args.desktop == "hyprland",
               "audio_and_network_panels": installing and args.desktop == "hyprland",
               "development_cli_and_default_editor": installing and args.desktop == "hyprland",
               "desktop_lock_unlock": installing and args.desktop == "hyprland",
               "primary_console_tui_reply": installing and args.desktop == "none",
               "graphical_tui_reply": installing and args.desktop != "none",
               "interactive_install_review": installing, "ratatui_install_review": installing,
               "mistyped_disk_confirmation_retry": installing,
               "provider": "local deterministic fixture" if installing else "none",
               "real_account_login": False, "physical_disks_attached": False}
    (area / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    # Retain receipts/screenshots/logs, not large disposable disks between cases.
    (area / "target.qcow2").unlink(missing_ok=True)
    (area / "extra-usb.raw").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
