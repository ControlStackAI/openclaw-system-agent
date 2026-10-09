"""Shared local installation review and disk eligibility; no distribution imports."""
import getpass
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import available_timezones


class InstallationIssue(ValueError):
    """An expected installer failure with an explicit, non-secret recovery state."""
    def __init__(self, message, **status):
        super().__init__(message)
        self.status = {**status, "message": message, "installed_boot_verified": False}


def payload_issue(payload, reason):
    if reason == "missing":
        message = ("The installed-system payload is missing from its expected location. "
                   "No disk was changed by this attempt. Keep the USB connected. "
                   "Check whether Arch copy-to-RAM mode unmounted the boot image; identify "
                   "that same image, remount it read-only, and verify its payload checksum "
                   "before reopening installation review.")
    elif reason == "unreadable":
        message = ("The local installer cannot read the installed-system payload. "
                   "No disk was changed by this attempt. Inspect the boot image mount, "
                   "read errors and installer access before retrying; do not bypass verification.")
    else:
        message = ("The installation payload failed its integrity check. "
                   "No disk was changed by this attempt. Stop and verify or replace the USB image; "
                   "do not use this payload or bypass the checksum check.")
    return InstallationIssue(message, state="blocked", stage="payload-check",
                             disk_erasure_approved=False, disk_changes="none-this-attempt",
                             payload=str(payload), reason=reason)


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def output(args):
    return run(args, capture_output=True).stdout.strip()


def descendants(node):
    yield node
    for child in node.get("children", []):
        yield from descendants(child)


def eligible(node, active_devices=()):
    if node.get("type") != "disk" or node.get("ro") or int(node.get("size", 0)) < 32 * 1024**3:
        return False
    if node.get("tran") == "usb" or node.get("rm"):
        return False
    identity = node.get("serial") or node.get("wwn") or ""
    if not re.fullmatch(r"[A-Za-z0-9_.: -]{1,128}", identity):
        return False
    for child in descendants(node):
        if child.get("fstype") == "iso9660" or any(child.get("mountpoints") or []) or child.get("name") in active_devices:
            return False
        name = Path(child["name"]).name
        holders = Path("/sys/class/block") / name / "holders"
        if holders.exists() and any(holders.iterdir()):
            return False
    return True


def disks():
    tree = json.loads(output(["lsblk", "--json", "--bytes", "--paths", "--output",
                              "NAME,TYPE,SIZE,MODEL,SERIAL,WWN,RO,RM,TRAN,MOUNTPOINTS,FSTYPE"]))
    active = set(output(["swapon", "--show=NAME", "--noheadings"]).splitlines())
    pools = run(["zpool", "status", "-P"], capture_output=True)
    # Imported pool members must not be reselected, even with no mounted datasets.
    active.update(str(Path(word).resolve()) for word in pools.stdout.split() if word.startswith("/dev/"))
    return [node for node in tree["blockdevices"] if eligible(node, active)]


def disk_identity(node):
    return {key: node.get(key) for key in ("name", "size", "model", "serial", "wwn", "children")}


def confirm_disk_erasure(node):
    """Retry typing mistakes without rebuilding the plan or granting approval."""
    from system_agent.setup import choose
    from system_agent.tui import Cancelled
    expected = "ERASE " + str(node["serial"] or node["wwn"])
    try:
        while True:
            confirmation = input(f"Type {expected} to approve this disk, or CANCEL to go back: ").strip()
            if confirmation == expected:
                return confirmation
            if confirmation.casefold() == "cancel":
                return None
            print("That did not match. Nothing has been erased.\n"
                  "Use uppercase ERASE, one space, then the disk identifier exactly as shown.\n"
                  "Your disk selection and setup choices are still here.")
            if choose("Try the disk confirmation again?", ["Try again", "Cancel installation"]) != 1:
                return None
    except (Cancelled, EOFError, KeyboardInterrupt):
        return None


def export_installed_pool(pool):
    """Keep ZFS's error available to the conversation after final cleanup fails."""
    try:
        run(["zpool", "export", pool], capture_output=True)
    except (subprocess.CalledProcessError, OSError) as error:
        code = error.returncode if isinstance(error, subprocess.CalledProcessError) else None
        detail = ((error.stderr or error.stdout or "ZFS returned no diagnostic text.")
                  if isinstance(error, subprocess.CalledProcessError) else str(error)).strip()
        # Leave room for the bridge's other fields in its bounded JSON response.
        truncated = len(detail) > 2000
        detail = detail[:2000] + (" [diagnostic truncated]" if truncated else "")
        raise InstallationIssue(
            f"System files and boot configuration were written, but final cleanup could not export "
            f"the target ZFS pool {pool} (exit {code}). Export error: {detail}\n"
            "The disk has already been changed. Preserve this installation and inspect the pool "
            "and remaining users or mounts, including live-service mount namespaces, before "
            "retrying cleanup. Do not restart installation or force-export the pool. "
            "Installed boot has not yet been verified.",
            state="needs-cleanup", stage="pool-export", disk_erasure_approved=True,
            disk_changes="system-written", pool=pool, exit_code=code,
            diagnostic=detail, diagnostic_truncated=truncated, reinstall_allowed=False,
        ) from error


def secret_twice(prompt):
    while True:
        value = getpass.getpass(prompt)
        if len(value) < 8:
            print("Please use at least eight characters.")
        elif value != getpass.getpass("Enter it again: "):
            print("Those did not match. Please try again.")
        else:
            return value


def timezone_choice():
    from system_agent.setup import choose
    while True:
        city = input("Which city should we use for your time zone? For example London or Los Angeles [UTC]: ").strip() or "UTC"
        normalized = city.casefold().replace(" ", "_")
        zones = available_timezones()
        exact = next((zone for zone in zones if zone.casefold() == normalized), None)
        matches = [exact] if exact else sorted(zone for zone in zones
                         if zone.rsplit("/", 1)[-1].casefold() == normalized)
        if len(matches) == 1:
            print("Using " + matches[0].replace("_", " ") + ".")
            return matches[0]
        if matches:
            return matches[choose("Which location do you mean?", [m.replace("_", " ") for m in matches]) - 1]
        print("I could not find that city. Try a nearby major city, or enter a time zone such as Europe/London.")


def describe_choices(choices):
    labels = {"agent_name": "Assistant name", "purpose": "Main use", "hostname": "Computer name", "username": "Your account", "desktop": "Desktop",
              "locale": "Language and region", "keyboard": "Keyboard", "timezone": "Time zone",
              "encrypt": "Disk encryption", "power_policy": "Power and lid behavior",
              "login_policy": "Sign-in and screen lock", "openclaw_release": "OpenClaw version policy"}
    names = {"none": "No desktop", "plasma": "KDE Plasma", "gnome": "GNOME", "hyprland": "Hyprland + Quickshell",
             "always-on": "Always on: performance, no sleep, no display blanking, lid ignored",
             "yubikey": "YubiKey required at sign-in; removal locks; password unlock can be toggled",
             "default": "Latest stable on Arch; pinned release on NixOS", "image-pinned": "Explicit image-pinned release",
             "standard": "Distribution defaults", "password": "Account password",
             "us": "US", "gb": "UK", "de": "German", "fr": "French", "es": "Spanish",
             "en_US.UTF-8": "English (United States)", "en_GB.UTF-8": "English (United Kingdom)",
             "de_DE.UTF-8": "German (Germany)", "fr_FR.UTF-8": "French (France)", "es_ES.UTF-8": "Spanish (Spain)"}
    for key, label in labels.items():
        if key in choices:
            value = choices[key]
            display = (("On" if value else "Off") if key == "encrypt" else
                       names.get(value, value) if key in ("desktop", "locale", "keyboard", "power_policy", "login_policy", "openclaw_release") else value)
            print(f"  {label}: {display}")
