"""Runtime observations; image metadata is never proof of a disk boot."""
import json
import os
import platform
import shlex
import subprocess
from pathlib import Path


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def classify(*, chroot, container, live, root_type):
    if chroot is None or container is None:
        return "unconfirmed"
    if chroot:
        return "chroot"
    if container:
        return "container"
    if live:
        return "live"
    if root_type in {"zfs", "ext4", "btrfs", "xfs"}:
        return "installed-candidate"
    return "unconfirmed"


def discover(root=Path("/"), run=command):
    release = {}
    path = root / "etc/os-release"
    for line in path.read_text().splitlines() if path.exists() else []:
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            try:
                release[key] = shlex.split(value)[0]
            except (ValueError, IndexError):
                pass
    def read(rel):
        p = root / rel
        return p.read_text().strip() if p.is_file() else ""
    cr, _ = run(["systemd-detect-virt", "--chroot"])
    co, _ = run(["systemd-detect-virt", "--container"])
    rc, mount = run(["findmnt", "--json", "--target", "/", "--output", "SOURCE,FSTYPE,UUID,OPTIONS"])
    try:
        fs = json.loads(mount)["filesystems"][0] if rc == 0 else {}
    except (ValueError, IndexError, KeyError):
        fs = {}
    markers = ["run/archiso", "etc/agent-installer/live-image", "run/live/medium", "cdrom/casper"]
    cmdline = read("proc/cmdline")
    live = any((root / p).exists() for p in markers) or any(x in cmdline for x in ["boot=live", "boot=casper", "archisobasedir=", "findiso="])
    phase = classify(chroot=None if cr not in (0, 1) else cr == 0,
                     container=None if co not in (0, 1) else co == 0,
                     live=live, root_type=fs.get("fstype", ""))
    return {"schema": 1, "distro_id": release.get("ID", "unknown"),
            "distro_name": release.get("PRETTY_NAME", "Unknown Linux"),
            "kernel": platform.release(), "uid": os.geteuid(), "phase": phase,
            "boot_id": read("proc/sys/kernel/random/boot_id"),
            "machine_id": read("etc/machine-id"), "root": fs}


def verify_boot(facts, expected):
    reasons = []
    if facts["phase"] != "installed-candidate":
        reasons.append("This is not a confirmed disk-boot environment.")
    for key in ("boot_id", "machine_id"):
        if not facts.get(key):
            reasons.append(f"Missing {key}.")
    if facts.get("boot_id") == expected.get("installation_boot_id"):
        reasons.append("The computer has not rebooted since installation.")
    if not expected.get("installation_boot_id"):
        reasons.append("No installation boot record was supplied.")
    if facts.get("distro_id") != expected.get("target_distro"):
        reasons.append("The running distribution differs from the installation plan.")
    if facts.get("machine_id") != expected.get("target_machine_id"):
        reasons.append("The installed machine identity does not match.")
    fs = facts.get("root", {})
    if fs.get("fstype") != expected.get("root_fstype"):
        reasons.append("The root filesystem type does not match.")
    # Dataset names for ZFS, filesystem UUID for other filesystems.
    actual = fs.get("source") if fs.get("fstype") == "zfs" else fs.get("uuid")
    if not actual or actual != expected.get("root_identity"):
        reasons.append("The mounted root does not match the planned installation.")
    if "rw" not in fs.get("options", "").split(","):
        reasons.append("The installed root is not writable.")
    return {"schema": 1, "installed_boot_verified": not reasons,
            "boot_id": facts.get("boot_id"), "reasons": reasons,
            "model_response_verified": False}
