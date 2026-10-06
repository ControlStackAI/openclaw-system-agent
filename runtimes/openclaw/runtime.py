"""Official CLI adapter, always with an explicit private state location."""
import os
import json
import secrets
import subprocess
from pathlib import Path


def environment(state, config=None):
    # Allowlist environment: no inherited provider keys or operator profile paths.
    state = Path(state).absolute()
    env = {k: os.environ[k] for k in ("PATH", "TERM", "LANG", "SSL_CERT_FILE", "NIX_SSL_CERT_FILE") if k in os.environ}
    env.update(HOME=str(state), XDG_CONFIG_HOME=str(state / "config"),
               XDG_CACHE_HOME=str(state / "cache"), XDG_DATA_HOME=str(state / "data"),
               OPENCLAW_HOME=str(state), OPENCLAW_STATE_DIR=str(state),
               OPENCLAW_CONFIG_PATH=str(config or state / "openclaw.json"),
               OPENCLAW_DISABLE_BONJOUR="1")
    if os.environ.get("OPENCLAW_NIX_MODE") in ("0", "1"):
        env["OPENCLAW_NIX_MODE"] = os.environ["OPENCLAW_NIX_MODE"]
    return env


def invoke(state, args, config=None):
    return subprocess.run(["openclaw", *args], env=environment(state, config), umask=0o077).returncode


def onboard(state, config=None):
    if os.environ.get("OPENCLAW_NIX_MODE") == "1":
        raise ValueError("This installation is managed declaratively. Configure the provider in the Nix module; interactive config mutation is unavailable.")
    from system_agent.readiness import readiness
    ready, message = readiness()
    if not ready:
        raise ValueError(message)
    # The official interactive prompt owns masked input/device login. No key flags.
    return invoke(state, ["onboard", "--skip-daemon", "--skip-health", "--skip-ui", "--skip-skills", "--skip-channels",
                          "--skip-bootstrap", "--skip-hooks", "--skip-search", "--workspace", str(Path(state).absolute() / "workspace")], config)


def local_policy(state, config_path=None):
    """Reapply the installer access boundary as the unprivileged service account."""
    from system_agent.state import private_dir, create_private, default_config
    state = private_dir(state)
    path = Path(config_path or state / "openclaw.json")
    if path != state / "openclaw.json" or path.is_symlink():
        raise ValueError("Only the private mutable runtime config can be updated.")
    config = json.loads(path.read_text())
    defaults = default_config(state)
    config["gateway"] = defaults["gateway"]
    config.setdefault("secrets", {}).setdefault("providers", {})["gateway"] = defaults["secrets"]["providers"]["gateway"]
    config.setdefault("agents", {}).setdefault("defaults", {}).update(workspace=str(state / "workspace"), skipBootstrap=True)
    config["tools"] = {"profile": "full", "allow": ["read", "session_status", "exec", "process", "write", "edit"], "elevated": {"enabled": False}}
    config["channels"] = {}
    temporary = state / ("config-" + secrets.token_hex(8))
    create_private(temporary, json.dumps(config, indent=2) + "\n")
    os.replace(temporary, path)
    return {"local_policy": "applied", "elevated": False}
