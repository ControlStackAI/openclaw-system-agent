import argparse
import json
import os
import sys
from pathlib import Path
from .facts import discover, verify_boot
from .handoff import validate
from .state import initialize, write_observation
from runtimes.openclaw import runtime


def main():
    parser = argparse.ArgumentParser(description="Your local system assistant")
    parser.add_argument("--state", default=os.environ.get("OPENCLAW_STATE_DIR", "/var/lib/controlstack-agent"))
    parser.add_argument("--config", default=os.environ.get("OPENCLAW_CONFIG_PATH"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sub.add_parser("refresh")
    init = sub.add_parser("initialize")
    init.add_argument("--identity", default=str(Path(__file__).resolve().parent.parent / "identity"))
    init.add_argument("--seed-config", type=Path)
    handoff = sub.add_parser("import-handoff")
    handoff.add_argument("file", type=Path)
    sub.add_parser("verify-boot")
    sub.add_parser("local-policy")
    sub.add_parser("onboard")
    chat = sub.add_parser("chat")
    chat.add_argument("--welcome", action="store_true")
    sub.add_parser("health")
    backup = sub.add_parser("backup")
    backup.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "initialize":
            result = initialize(args.state, args.identity, args.config, args.seed_config)
        elif args.command in ("inspect", "refresh"):
            result = discover()
            if args.command == "refresh":
                write_observation(args.state, "facts.json", result)
        elif args.command == "import-handoff":
            result = validate(json.loads(args.file.read_text()))
            from .state import create_private, private_dir
            directory = private_dir(Path(args.state) / "lifecycle")
            create_private(directory / "installation.json", json.dumps(result, indent=2))
        elif args.command == "verify-boot":
            expected = validate(json.loads((Path(args.state) / "lifecycle/installation.json").read_text()))
            result = verify_boot(discover(), expected)
            write_observation(args.state, "boot-verification.json", result)
            print(json.dumps(result, indent=2))
            return 0 if result["installed_boot_verified"] else 1
        elif args.command == "local-policy":
            result = runtime.local_policy(args.state, args.config)
        elif args.command == "onboard":
            return runtime.onboard(args.state, args.config)
        elif args.command == "chat":
            command = ["tui"]
            if args.welcome:
                command += ["--message", "Help me with this computer. Check where you are running and my saved intentions, then ask just the next useful question. Do not assume that live media means I want to erase or install."]
            return runtime.invoke(args.state, command, args.config)
        elif args.command == "health":
            return runtime.invoke(args.state, ["health", "--json"], args.config)
        elif args.command == "backup":
            destination = args.destination.absolute()
            state = Path(args.state).resolve()
            if destination.resolve().is_relative_to(state):
                raise ValueError("Save the recovery archive outside the agent state directory.")
            from .state import private_dir
            private_dir(destination)
            os.umask(0o077)
            return runtime.invoke(args.state, ["backup", "create", "--verify", "--output", str(destination), "--json"], args.config)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"I could not complete that step: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
