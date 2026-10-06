"""Initialize fresh state without overwriting an adopted OpenClaw instance."""
import json
import os
import secrets
from pathlib import Path


def private_dir(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("State paths must not contain symbolic links.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_uid != os.geteuid():
        raise ValueError("The state directory belongs to another account.")
    path.chmod(0o700)
    return path


def create_private(path, data):
    # Never replace existing identity, credentials, databases, or configuration.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def initialize(path, identity, config_path=None):
    state = private_dir(path)
    workspace = private_dir(state / "workspace")
    lifecycle = private_dir(state / "lifecycle")
    for source in sorted(Path(identity).glob("*.md")):
        destination = workspace / source.name
        if not destination.exists() and not destination.is_symlink():
            create_private(destination, source.read_text())
    token = state / "gateway-token"
    if not token.exists() and not token.is_symlink():
        create_private(token, secrets.token_hex(32) + "\n")
    if token.is_symlink() or not token.is_file() or token.stat().st_mode & 0o077:
        raise ValueError("Gateway token must be a private regular file.")
    config = Path(config_path) if config_path else state / "openclaw.json"
    if not config.exists() and not config.is_symlink():
        create_private(config, json.dumps(default_config(state), indent=2) + "\n")
    return {"state": str(state), "workspace": str(workspace), "lifecycle": str(lifecycle)}


def default_config(state):
    return {"gateway": {"mode": "local", "bind": "loopback", "port": 18789,
            "auth": {"mode": "token", "token": {"source": "file", "provider": "gateway", "id": "value"}}},
            "secrets": {"providers": {"gateway": {"source": "file", "path": str(state / "gateway-token"), "mode": "singleValue"}}},
            "agents": {"defaults": {"workspace": str(state / "workspace"), "skipBootstrap": True}},
            "tools": {"profile": "minimal", "elevated": {"enabled": False}},
            "discovery": {"mdns": {"mode": "off"}}}


def write_observation(state, name, value):
    directory = private_dir(Path(state) / "lifecycle")
    destination = directory / name
    temporary = directory / (name + "." + secrets.token_hex(8))
    create_private(temporary, json.dumps(value, indent=2) + "\n")
    os.replace(temporary, destination)
