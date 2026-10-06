"""Official CLI adapter, always with an explicit private state location."""
import os
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
    if os.environ.get("OPENCLAW_NIX_MODE") == "1":
        env["OPENCLAW_NIX_MODE"] = "1"
    return env


def invoke(state, args, config=None):
    return subprocess.run(["openclaw", *args], env=environment(state, config)).returncode


def onboard(state, config=None):
    if os.environ.get("OPENCLAW_NIX_MODE") == "1":
        raise ValueError("This installation is managed declaratively. Configure the provider in the Nix module; interactive config mutation is unavailable.")
    from system_agent.readiness import readiness
    ready, message = readiness()
    if not ready:
        raise ValueError(message)
    # The official interactive prompt owns masked input/device login. No key flags.
    return invoke(state, ["onboard", "--skip-daemon", "--workspace", str(Path(state).absolute() / "workspace")], config)
