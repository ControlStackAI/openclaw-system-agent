"""Shared local installation review and disk eligibility; no distribution imports."""
import getpass
import json
import re
import subprocess
from pathlib import Path
from zoneinfo import available_timezones

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
              "encrypt": "Disk encryption"}
    names = {"none": "No desktop", "plasma": "KDE Plasma", "gnome": "GNOME", "hyprland": "Hyprland + Quickshell",
             "us": "US", "gb": "UK", "de": "German", "fr": "French", "es": "Spanish",
             "en_US.UTF-8": "English (United States)", "en_GB.UTF-8": "English (United Kingdom)",
             "de_DE.UTF-8": "German (Germany)", "fr_FR.UTF-8": "French (France)", "es_ES.UTF-8": "Spanish (Spain)"}
    for key, label in labels.items():
        if key in choices:
            value = choices[key]
            display = (("On" if value else "Off") if key == "encrypt" else
                       names.get(value, value) if key in ("desktop", "locale", "keyboard") else value)
            print(f"  {label}: {display}")
