#!/usr/bin/env python3
"""Boot the real hybrid ISO as USB; attach only disposable regular-file disks."""
import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
import pexpect

ROOT = Path(__file__).resolve().parents[1]


class Guest:
    def __init__(self, iso, area, uefi=False, installed=False, offline=False):
        self.area = area
        (area / "qmp.sock").unlink(missing_ok=True)
        self.log = (area / ("installed.log" if installed else "live.log")).open("w")
        args = ["-machine", "q35", "-m", "4096", "-smp", "2", "-display", "none", "-monitor", "none",
                "-serial", "stdio", "-qmp", f"unix:{area}/qmp.sock,server=on,wait=off",
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
            if installed:
                self.process.expect("login:")
                self.process.sendline("owner")
                self.process.expect("Password:")
                self.process.sendline("vm-only-test-password")
                self.process.expect(r"owner@[^\r\n]*\$")
                self.process.sendline("sudo -i")
                self.process.expect("password for owner:")
                self.process.sendline("vm-only-test-password")
            self.process.expect(r"root@[^\r\n]*#")
            self.process.sendline("stty -echo; export PS1='CS_READY> '")
            self.process.expect("CS_READY> ")
        except Exception:
            self.qmp("screendump", {"filename": str(area / "boot-failure.png"), "format": "png"})
            self.process.terminate(force=True)
            self.log.close()
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

    def put(self, path, data):
        payload = base64.b64encode(data.encode()).decode()
        self.command(f"echo {payload} | base64 -d > {path}")

    def qmp(self, execute, arguments):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.area / "qmp.sock"))
            stream = sock.makefile("rwb", buffering=0)
            stream.readline()
            for command in ({"execute": "qmp_capabilities"}, {"execute": execute, "arguments": arguments}):
                stream.write(json.dumps(command).encode() + b"\n")
                while True:
                    response = json.loads(stream.readline())
                    if "error" in response:
                        raise RuntimeError(response)
                    if "return" in response:
                        break

    def close(self):
        if self.process.isalive():
            self.process.sendline("poweroff")
            try:
                self.process.expect(pexpect.EOF, timeout=60)
            except pexpect.TIMEOUT:
                self.process.terminate(force=True)
        self.process.close()
        self.log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("iso", type=Path)
    parser.add_argument("--mode", choices=["bios-offline", "uefi-install"], required=True)
    args = parser.parse_args()
    iso = args.iso.resolve()
    if not iso.is_file():
        parser.error("ISO must be a regular file")
    area = ROOT / ".build/iso-test" / args.mode
    area.mkdir(parents=True, exist_ok=True)
    # Each invocation needs a genuinely blank target and firmware, never a resumed result.
    for name in ("target.qcow2", "OVMF_VARS.fd", "result.json", "qmp.sock"):
        (area / name).unlink(missing_ok=True)
    installing = args.mode == "uefi-install"
    guest = Guest(iso, area, uefi=installing, offline=not installing)
    try:
        guest.command("system-agent inspect | grep '\"phase\": \"live\"'")
        guest.command("timeout 180 bash -c 'until systemctl is-active --quiet NetworkManager && systemctl is-active --quiet controlstack-agent; do sleep 2; done'")
        guest.command("test $(findmnt -n -o FSTYPE /run) = tmpfs")
        guest.command("test $(stat -c %a /run/controlstack-agent/gateway-token) = 600")
        guest.command("openclaw --version")
        guest.command("openclaw onboard --help > /tmp/onboard-help; for flag in --skip-daemon --skip-health --skip-ui --skip-skills --skip-channels --skip-bootstrap --skip-hooks --skip-search; do grep -q -- $flag /tmp/onboard-help || exit 1; done")
        guest.command("cat /dev/vcs1 | grep 'Welcome to your OpenClaw'")
        guest.qmp("screendump", {"filename": str(area / "welcome.png"), "format": "png"})
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
            guest.command("systemctl restart controlstack-agent; sleep 10")
            guest.command(live_env + "openclaw agent --agent main --session-key agent:main:live-fixture --message live-fixture-response --json", timeout=180)
            guest.put("/tmp/install-test.py", '''import json, sys
from pathlib import Path
inputs = json.loads(Path('/etc/controlstack-agent/install-inputs.json').read_text())
sys.path.insert(0, inputs['core'] + '/lib/system-agent')
from adapters.nixos.install import disks, prepare, install
nodes = [n for n in disks() if n['serial'] == 'CONTROLSTACK-VM-ONLY']
assert len(nodes) == 1
choices = dict(hostname='vmresident', username='owner', desktop='none', timezone='UTC', keyboard='us', locale='en_US.UTF-8', encrypt=False)
Path('/run/controlstack-agent/live-only-credential-fixture').write_text('must-not-transfer')
Path('/run/controlstack-agent/live-only-credential-fixture').chmod(0o600)
plan = prepare(nodes[0], choices)
install(plan, 'ERASE CONTROLSTACK-VM-ONLY', 'vm-only-test-password')
print('INSTALL_COMPLETED')
''')
            guest.command("python3 /tmp/install-test.py", timeout=3600)
    finally:
        guest.close()
    if installing:
        guest = Guest(iso, area, uefi=True, installed=True)
        try:
            guest.command("findmnt -n -o FSTYPE / | grep -x zfs")
            guest.command("test ! -e /etc/agent-installer/live-image")
            guest.command("timeout 180 bash -c 'until systemctl is-active --quiet controlstack-agent; do sleep 2; done'; systemctl is-active controlstack-agent controlstack-agent-boot-check || { journalctl -b -u controlstack-agent -u controlstack-agent-boot-check --no-pager; exit 1; }")
            guest.command("test ! -e /var/lib/controlstack-agent/live-only-credential-fixture")
            guest.command("! grep -q non-secret-vm-fixture /var/lib/controlstack-agent/openclaw.json")
            guest.command("grep 'desktop: none' /var/lib/controlstack-agent/workspace/USER.md")
            guest.command("grep '\"installed_boot_verified\": true' /var/lib/controlstack-agent/lifecycle/boot-verification.json")
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
            guest.command("sleep 10; runuser -u controlstack-agent -- env OPENCLAW_STATE_DIR=/var/lib/controlstack-agent OPENCLAW_CONFIG_PATH=/var/lib/controlstack-agent/openclaw.json OPENCLAW_NIX_MODE=0 openclaw agent --agent main --session-key agent:main:installed --message installed-fixture-response --json", timeout=180)
            guest.command("grep -q 'Owner.s chosen system' /tmp/fixture-request.json")
            guest.qmp("screendump", {"filename": str(area / "installed.png"), "format": "png"})
        finally:
            guest.close()
    with iso.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = {"mode": args.mode, "iso_sha256": digest, "passed": True,
               "installation": installing, "disk_boot_without_iso": installing,
               "provider": "local deterministic fixture" if installing else "none",
               "real_account_login": False, "physical_disks_attached": False}
    (area / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
