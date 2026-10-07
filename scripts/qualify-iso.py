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
    def __init__(self, iso, area, uefi=False, installed=False, offline=False, encrypted=False, memory=4096, keyboard="us"):
        self.keyboard = keyboard
        self.area = area
        self.control = tempfile.TemporaryDirectory(prefix="cs-iso-", dir="/tmp")
        self.socket_path = Path(self.control.name) / "qmp.sock"
        self.log = (area / ("installed.log" if installed else "live.log")).open("w")
        args = ["-machine", "q35", "-m", str(memory), "-smp", "2", "-display", "none", "-monitor", "none",
                "-chardev", "stdio,id=serial0,signal=off", "-serial", "chardev:serial0", "-qmp", f"unix:{self.socket_path},server=on,wait=off",
                "-nic", "none" if offline else "user,model=virtio-net-pci", "-no-reboot"]
        if os.access("/dev/kvm", os.R_OK | os.W_OK):
            args += ["-enable-kvm", "-cpu", "host"]
        else:
            args += ["-accel", "tcg", "-cpu", "max"]
        if not installed:
            args += ["-drive", f"if=none,id=live,format=raw,readonly=on,file={iso}",
                     "-device", "qemu-xhci,id=xhci", "-device", "usb-storage,drive=live,bootindex=1"]
        if uefi:
            code = Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
            variables = area / "OVMF_VARS.fd"
            if not variables.exists():
                shutil.copyfile("/usr/share/OVMF/OVMF_VARS_4M.fd", variables)
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
            self.process.expect(r"root@[^\r\n]*#")
            self.process.sendline("stty -echo; umask 077; export PS1='CS_READY> '")
            self.process.expect("CS_READY> ")
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
        self.process.expect(marker + r":(\d+)", timeout=timeout)
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

    def wait_screen_text(self, expected, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if expected.casefold() in self.screen_text().casefold():
                return
            time.sleep(2)
        raise RuntimeError("Graphical screen did not show: " + expected)

    def type_console(self, text):
        for key in text:
            if self.keyboard == "de" and key in "yz":
                key = "z" if key == "y" else "y"
            self.qmp("send-key", {"keys": [{"type": "qcode", "data": "minus" if key == "-" else key}], "hold-time": 50})
            time.sleep(0.08)
        self.qmp("human-monitor-command", {"command-line": "sendkey ret"})

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
    parser.add_argument("--desktop", choices=["none", "plasma", "gnome"], default="none")
    parser.add_argument("--encrypted", action="store_true")
    parser.add_argument("--keyboard", choices=["us", "de"], default="us")
    args = parser.parse_args()
    iso = args.iso.resolve()
    if not iso.is_file():
        parser.error("ISO must be a regular file")
    area = ROOT / ".build/iso-test" / (args.mode + "-" + args.desktop + ("-encrypted" if args.encrypted else "") + "-" + args.keyboard)
    area.mkdir(parents=True, exist_ok=True)
    # Each invocation needs a genuinely blank target and firmware, never a resumed result.
    for name in ("target.qcow2", "OVMF_VARS.fd", "result.json", "qmp.sock"):
        (area / name).unlink(missing_ok=True)
    installing = args.mode == "uefi-install"
    memory = 4096 if args.desktop == "none" else 8192
    guest = Guest(iso, area, uefi=installing, offline=not installing, memory=memory, keyboard=args.keyboard)
    try:
        guest.command("system-agent inspect | grep '\"phase\": \"live\"'")
        guest.command("timeout 180 bash -c 'until systemctl is-active --quiet NetworkManager && systemctl is-active --quiet controlstack-agent; do sleep 2; done'")
        guest.command("test $(findmnt -n -o FSTYPE /run) = tmpfs")
        guest.command("test $(stat -c %a /run/controlstack-agent/gateway-token) = 600")
        guest.command("openclaw --version")
        guest.command("openclaw onboard --help > /tmp/onboard-help; for flag in --skip-daemon --skip-health --skip-ui --skip-skills --skip-channels --skip-bootstrap --skip-hooks --skip-search; do grep -q -- $flag /tmp/onboard-help || exit 1; done")
        guest.command("cat /dev/vcs1 | grep 'Welcome to your OpenClaw'")
        guest.qmp("screendump", {"filename": str(area / "welcome.png"), "format": "png"})
        if args.keyboard == "de":
            guest.type_console("6")
            time.sleep(1)
            guest.type_console("3")
            guest.command("sleep 2; runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/run/controlstack-agent system-agent setup-choice | grep '\"keyboard\": \"de\"'")
        if not installing:
            guest.qmp("human-monitor-command", {"command-line": "sendkey 1"})
            guest.qmp("human-monitor-command", {"command-line": "sendkey ret"})
            guest.command("sleep 20; cat /dev/vcs1 | grep 'Internet check failed'", timeout=90)
            guest.qmp("screendump", {"filename": str(area / "offline.png"), "format": "png"})
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
            guest.command(live_env + "system-agent setup-choice hostname vmresident")
            guest.command("install -m 600 /dev/null /run/controlstack-agent/live-only-credential-fixture")
            # Drive the shipped local review screen, including separate disk approval.
            guest.process.sendline("system-agent-setup")
            def answer(prompt, value, timeout=60):
                found = guest.process.expect_exact([prompt, "That step did not finish:", "Those did not match.", "Please choose one of the numbers above."], timeout=timeout)
                if found:
                    if found == 1:
                        guest.process.expect_exact("Choose a number:", timeout=30)
                        guest.process.sendline("8")  # Leave the live setup menu cleanly.
                    else:
                        guest.process.sendcontrol("d")
                    guest.process.expect_exact("CS_READY> ", timeout=30)
                    details = guest.command("cat /run/controlstack-install/*.build.log 2>/dev/null || true")
                    print(details[-12000:], flush=True)
                    raise RuntimeError("The local setup screen rejected a test step: " + prompt)
                guest.process.sendline(value)
            answer("Choose a number:", "4")
            answer("Choose a number:", "2")
            answer("Choose a number:", "1")
            answer("Choose a number:", "1")
            answer("Name for your local account [owner]:", "owner")
            answer("Choose a number:", str(["none", "plasma", "gnome"].index(args.desktop) + 1))
            answer("Choose a number:", "1")
            if args.keyboard != "de":
                answer("Choose a number:", "1")
            answer("[UTC]:", "UTC")
            guest.process.expect_exact("Encrypt your files?")
            answer("Choose a number:", "1" if args.encrypted else "2")
            answer("anything else cancels:", "ERASE CONTROLSTACK-VM-ONLY", timeout=900)
            answer("Password for your local account (hidden):", "vmonlytestpassword")
            answer("Enter it again:", "vmonlytestpassword")
            if args.encrypted:
                answer("Disk unlock passphrase (hidden; keep a safe copy elsewhere):", "vmencryptiontest")
                answer("Enter it again:", "vmencryptiontest")
            guest.process.expect_exact("Installation files are ready.", timeout=900)
            answer("Choose a number:", "1")
            guest.process.expect(pexpect.EOF, timeout=60)

    finally:
        guest.close()
    if installing:
        guest = Guest(iso, area, uefi=True, installed=True, encrypted=args.encrypted, memory=memory, keyboard=args.keyboard)
        try:
            guest.command("findmnt -n -o FSTYPE / | grep -x zfs")
            guest.command("test ! -e /etc/agent-installer/live-image")
            guest.command("test -r /run/current-system/sw/share/applications/controlstack-agent.desktop")
            guest.command("timeout 180 bash -c 'until systemctl is-active --quiet controlstack-agent; do sleep 2; done'; systemctl is-active controlstack-agent controlstack-agent-boot-check || { journalctl -b -u controlstack-agent -u controlstack-agent-boot-check --no-pager; exit 1; }")
            guest.command("test ! -e /var/lib/controlstack-agent/live-only-credential-fixture")
            guest.command("! grep -q non-secret-vm-fixture /var/lib/controlstack-agent/openclaw.json")
            guest.command(f"grep 'desktop: {args.desktop}' /var/lib/controlstack-agent/workspace/USER.md")
            if args.desktop != "none":
                guest.command("timeout 180 bash -c 'until systemctl is-active --quiet display-manager; do sleep 2; done'")
            if args.encrypted:
                guest.command("zfs get -H -o value encryption $(findmnt -n -o SOURCE /) | grep -x aes-256-gcm")
            guest.command("grep '\"installed_boot_verified\": true' /var/lib/controlstack-agent/lifecycle/boot-verification.json")
            guest.qmp("screendump", {"filename": str(area / "login.png"), "format": "png"})
            if args.desktop == "none":
                guest.type_console("owner")
                time.sleep(3)
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
                shell_name = "gnome-shell" if args.desktop == "gnome" else "plasmashell"
                guest.command("timeout 120 bash -c " + shlex.quote(
                    "until pgrep -u owner -f '/bin/[^ ]*" + shell_name + "'; do sleep 2; done"))

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
            if args.desktop == "none":
                guest.type_console("2")
                guest.command("timeout 120 bash -c 'until grep -q \"resident conversation works\" /dev/vcs1; do sleep 2; done'")
                guest.qmp("screendump", {"filename": str(area / "conversation.png"), "format": "png"})
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-d"})
                guest.command("sleep 3; grep -q \"What would you like to do?\" /dev/vcs1")

            if args.desktop != "none":
                if args.desktop == "gnome":
                    # GNOME starts in overview. Its faint search placeholder is
                    # not reliable OCR; Escape closes overview before typing.
                    guest.qmp("human-monitor-command", {"command-line": "sendkey esc"})
                    time.sleep(1)
                guest.wait_screen_text("Choose a number")
                guest.type_console("2")
                guest.wait_screen_text("resident conversation works")
                guest.qmp("screendump", {"filename": str(area / "conversation.png"), "format": "png"})
                guest.qmp("human-monitor-command", {"command-line": "sendkey ctrl-d"})
                guest.wait_screen_text("What would you like to do?")

            guest.qmp("screendump", {"filename": str(area / "installed.png"), "format": "png"})
        except Exception:
            guest.qmp("screendump", {"filename": str(area / "installed-failure.png"), "format": "png"})
            print(guest.command("journalctl -b -u display-manager -u controlstack-agent --no-pager -n 160; loginctl list-sessions; ps -eo user,comm,args | grep -E 'sddm|gdm|plasmashell|gnome-shell|xterm|system_agent.setup' || true")[-16000:], flush=True)
            raise
        finally:
            guest.close()
    with iso.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = {"mode": args.mode, "iso_sha256": digest, "passed": True,
               "installation": installing, "disk_boot_without_iso": installing, "ram_mib": memory,
               "desktop": args.desktop, "encryption": args.encrypted, "keyboard": args.keyboard, "graphical_owner_login": installing and args.desktop != "none",
               "installed_setup_autostart": installing,
               "primary_console_tui_reply": installing and args.desktop == "none",
               "graphical_tui_reply": installing and args.desktop != "none",
               "interactive_install_review": installing,
               "provider": "local deterministic fixture" if installing else "none",
               "real_account_login": False, "physical_disks_attached": False}
    (area / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    # Retain receipts/screenshots/logs, not large disposable disks between cases.
    (area / "target.qcow2").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
