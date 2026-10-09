"""A narrow data contract; never import instructions, paths, or credentials."""
import re

FIELDS = {"schema", "target_distro", "installation_boot_id", "target_machine_id",
          "root_fstype", "root_identity", "installer_revision"}


def validate(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("Handoff has missing or unexpected fields; credentials and free text are not accepted.")
    if type(value["schema"]) is not int or value["schema"] not in (1, 2):
        raise ValueError("Unsupported handoff schema.")
    if value["target_distro"] not in {"arch", "nixos"} or value["root_fstype"] not in ({"zfs"} if value["schema"] == 1 else {"zfs", "ext4", "btrfs", "xfs"}):
        raise ValueError("Unsupported distribution or filesystem in handoff.")
    patterns = {"installation_boot_id": r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}",
                "target_machine_id": r"[a-f0-9]{32}", "installer_revision": r"[a-f0-9]{40}",
                "root_identity": r"[A-Za-z][A-Za-z0-9_.:-]*(?:/[A-Za-z0-9_.:-]+)+"}
    if value['root_fstype'] != 'zfs':
        patterns['root_identity'] = r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}"
    for key, pattern in patterns.items():
        if not isinstance(value[key], str) or len(value[key]) > 256 or not re.fullmatch(pattern, value[key]):
            raise ValueError(f"Invalid {key} in installation handoff.")
    if any(part in (".", "..") for part in value["root_identity"].split("/")):
        raise ValueError("Invalid root dataset.")
    return value


def read_image_contract(value):
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("Unsupported installer image contract.")
    if value.get("distro") not in {"arch", "nixos"}:
        raise ValueError("Installer distribution is not supported.")
    if not isinstance(value.get("runtime"), str):
        raise ValueError("Installer runtime is missing.")
    return {k: value[k] for k in ("schema", "distro", "runtime")}
