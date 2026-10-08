"""Portable, typed owner choices, independent of installation mechanisms."""
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PURPOSES = ("development", "everyday", "gaming", "server", "mixed")
DESKTOPS = ("none", "plasma", "gnome", "hyprland")
LAYOUTS = ("us", "gb", "de", "fr", "es")
LOCALES = ("en_US.UTF-8", "en_GB.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8", "es_ES.UTF-8")


def validate_choices(choices):
    keys = {"hostname", "username", "desktop", "timezone", "keyboard", "locale", "encrypt"}
    if not isinstance(choices, dict) or not keys <= set(choices) or set(choices) - keys - {"purpose", "agent_name"}:
        raise ValueError("Incomplete or unexpected system choices")
    if "purpose" in choices and choices["purpose"] not in PURPOSES:
        raise ValueError("Choose one of the supported uses for this computer.")
    if "agent_name" in choices:
        validate_agent_name(choices["agent_name"])
    for field in ("hostname", "username"):
        if not isinstance(choices[field], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,30}", choices[field]):
            raise ValueError(f"Use a short name with lowercase letters, numbers and hyphens for {field}.")
    if choices["username"] in {"root", "nobody", "controlstack-agent", "nixbld"}:
        raise ValueError("Choose a personal account name.")
    if choices["desktop"] not in DESKTOPS or choices["keyboard"] not in LAYOUTS or choices["locale"] not in LOCALES:
        raise ValueError("That desktop, keyboard or language is not yet supported by this setup screen.")
    if type(choices["encrypt"]) is not bool:
        raise ValueError("Encryption must be an explicit choice.")
    if not isinstance(choices["timezone"], str) or not re.fullmatch(r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+)*", choices["timezone"]):
        raise ValueError("Use a time zone such as Europe/London or America/Los_Angeles.")
    try:
        ZoneInfo(choices["timezone"])
    except ZoneInfoNotFoundError as error:
        raise ValueError("That time zone is not available.") from error
    return choices



def validate_agent_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,47}", name):
        raise ValueError("Use up to 48 letters, numbers, spaces or hyphens for the assistant name.")
    return name


def name_agent(state, name):
    from pathlib import Path
    from .state import create_private
    import os, secrets
    name = validate_agent_name(name)
    path = Path(state) / 'workspace/IDENTITY.md'
    if path.is_symlink() or not path.is_file():
        raise ValueError("A regular assistant identity file is required.")
    text = path.read_text()
    text = re.sub(r'^Name: .*$', 'Name: ' + name, text, count=1, flags=re.M) if re.search(r'^Name: ', text, re.M) else text + '\nName: ' + name + '\n'
    temporary = path.with_name('identity-' + secrets.token_hex(8))
    create_private(temporary, text)
    os.replace(temporary, path)
    return {'assistant_name': name}


def initialize_agent_name(state, name):
    """Seed a fresh installed identity before its first service start."""
    from pathlib import Path
    from .state import private_dir, create_private
    validate_agent_name(name)
    workspace = private_dir(Path(state) / "workspace")
    identity = workspace / "IDENTITY.md"
    if not identity.exists() and not identity.is_symlink():
        template = Path(__file__).resolve().parent.parent / "identity/IDENTITY.md"
        create_private(identity, template.read_text())
    return name_agent(state, name)
