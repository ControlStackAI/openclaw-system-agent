"""Typed, non-secret installation suggestions; never approvals or observed facts."""
import json
from pathlib import Path
from .profile import validate_choices
from .state import write_observation

DEFAULTS = dict(hostname="my-computer", username="owner", desktop="none", timezone="UTC",
                keyboard="us", locale="en_US.UTF-8", encrypt=False, purpose="mixed", agent_name="OpenClaw",
                power_policy="standard", login_policy="password", openclaw_release="default")


def validate_partial(value):
    if not isinstance(value, dict) or not set(value) <= set(DEFAULTS):
        raise ValueError("Only supported non-secret setup choices are accepted.")
    validate_choices({**DEFAULTS, **value})
    return value


def read(state):
    path = Path(state) / "lifecycle/setup-choices.json"
    if path.is_symlink():
        raise ValueError("Setup choices must not be a symbolic link.")
    if not path.exists():
        return {}
    with path.open() as file:
        data = file.read(8193)
    if len(data) > 8192:
        raise ValueError("Setup choices are too large.")
    return validate_partial(json.loads(data))


def update(state, key, value):
    if key == "encrypt":
        if value not in ("yes", "no"):
            raise ValueError("Choose yes or no for encryption.")
        value = value == "yes"
    choices = validate_partial({**read(state), key: value})
    write_observation(state, "setup-choices.json", choices)
    return {"suggested_choices": choices, "disk_erasure_approved": False}
