"""Unprivileged, read-only desktop telemetry. Never reads agent state or credentials."""
import json
import subprocess
import time
from pathlib import Path


def service_status(text):
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    # Deliberately export only a fixed allowlist; systemd Environment can contain secrets.
    def number(key):
        try:
            value = int(values.get(key, ""))
            return value if 0 <= value < 2**63 else None
        except ValueError:
            return None
    active = values.get("ActiveState", "unknown")
    if active not in {"active", "activating", "deactivating", "inactive", "failed", "reloading"}:
        active = "unknown"
    return {"state": active, "memory": number("MemoryCurrent"),
            "cpu_ns": number("CPUUsageNSec"), "restarts": number("NRestarts")}


def snapshot():
    try:
        result = subprocess.run(["systemctl", "show", "controlstack-agent.service",
            "--property=ActiveState,MemoryCurrent,CPUUsageNSec,NRestarts"],
            capture_output=True, text=True, timeout=2, check=True)
        agent = service_status(result.stdout)
    except (OSError, subprocess.SubprocessError):
        agent = service_status("")
    try:
        result = subprocess.run(["systemctl", "--user", "is-active", "controlstack-hypruse.service"],
            capture_output=True, text=True, timeout=2)
        desktop_control = "enabled" if result.stdout.strip() == "active" else "stopped"
    except (OSError, subprocess.SubprocessError):
        desktop_control = "unavailable"
    try:
        security = json.loads(subprocess.run(['system-agent-key', 'status'], capture_output=True,
                                             text=True, timeout=2, check=True).stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        security = {'enabled': False, 'key_present': False, 'unlocked': False, 'always_on': False}
    memory = dict((line.split(":")[0], int(line.split()[1])) for line in Path("/proc/meminfo").read_text().splitlines())
    cpu = [int(n) for n in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
    return {"sampled": time.time(), "agent": agent, "desktop_control": desktop_control, "security": security, "memory_percent": round(100 * (1 - memory["MemAvailable"] / memory["MemTotal"])),
            "cpu_total": sum(cpu), "cpu_idle": cpu[3] + cpu[4]}


if __name__ == "__main__":
    print(json.dumps(snapshot()))
