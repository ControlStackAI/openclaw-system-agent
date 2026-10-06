"""Portable, typed owner choices, independent of installation mechanisms."""
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DESKTOPS = ("none", "plasma", "gnome")
LAYOUTS = ("us", "gb", "de", "fr", "es")
LOCALES = ("en_US.UTF-8", "en_GB.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8", "es_ES.UTF-8")


def validate_choices(choices):
    keys = {"hostname", "username", "desktop", "timezone", "keyboard", "locale", "encrypt"}
    if not isinstance(choices, dict) or set(choices) != keys:
        raise ValueError("Incomplete or unexpected system choices")
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


