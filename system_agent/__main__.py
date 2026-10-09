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
    sub.add_parser("sync-mcp")
    choices = sub.add_parser("setup-choice")
    choices.add_argument("key", nargs="?")
    choices.add_argument("value", nargs="?")
    sub.add_parser("install-status")
    sub.add_parser("request-install").add_argument("--retry", action="store_true")
    sub.add_parser("deployment-mode").add_argument("mode", choices=("tested", "custom"), nargs="?")
    sub.add_parser("deployment-review").add_argument("plan", type=Path)
    sub.add_parser("deployment-status")
    sub.add_parser("deployment-guide")
    sub.add_parser("deployment-account")
    sub.add_parser("deployment-encryption-key")
    sub.add_parser("deployment-record").add_argument("record")
    progress = sub.add_parser("deployment-checkpoint")
    progress.add_argument("phase")
    progress.add_argument("detail")
    requirement = sub.add_parser("deployment-requirement")
    requirement.add_argument("id")
    requirement.add_argument("status")
    requirement.add_argument("evidence")
    sub.add_parser("deployment-verify")
    sub.add_parser("deployment-finalize")
    sub.add_parser("onboard")
    sub.add_parser("name-agent").add_argument("name")
    login = sub.add_parser("connect-account")
    login.add_argument("account", choices=("chatgpt", "openai-api", "other"))
    chat = sub.add_parser("chat")
    chat.add_argument("--welcome", action="store_true")
    chat.add_argument("--resume-install", action="store_true")
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
        elif args.command == "setup-choice":
            from . import choices
            if args.key is None and args.value is None:
                result = choices.read(args.state)
            elif args.key is not None and args.value is not None:
                result = choices.update(args.state, args.key, args.value)
            else:
                raise ValueError("Supply both a choice and its value, or neither to read choices.")
        elif args.command in ("install-status", "request-install"):
            from .install_bridge import request
            from .choices import read
            from .deployment import mode
            if args.command == "request-install" and mode(args.state) == "custom":
                raise ValueError("Custom mode uses deployment-review and native configuration, not the preset executor")
            result = request("status") if args.command == "install-status" else request("request", read(args.state), retry=args.retry)
        elif args.command.startswith("deployment-"):
            from . import deployment as d
            if args.command == "deployment-guide":
                print((Path(__file__).resolve().parent.parent / "adapters/custom-deployment.md").read_text())
                return 0
            elif args.command == "deployment-mode":
                result = d.set_mode(args.state, args.mode) if args.mode else {"mode": d.mode(args.state)}
            elif args.command == "deployment-review":
                from .install_bridge import request
                if d.mode(args.state) != "custom":
                    raise ValueError("Select Build my own system in the local setup menu first")
                previous = d.read(args.state, "custom-deployment.json")
                if previous and previous['state'] != 'cancelled':
                    raise ValueError("An approved deployment already exists. Resume it; do not repeat disk approval or erasure.")
                result = request("custom", d.validate_plan(json.loads(args.plan.read_text())))
            elif args.command in ("deployment-account", "deployment-encryption-key"):
                from .install_bridge import request
                record = d.read(args.state, "custom-deployment.json")
                if not record or record['state'] == 'cancelled':
                    raise ValueError("Review the custom deployment first")
                result = request("custom-key" if args.command == "deployment-encryption-key" else "custom-account", record['plan'], retry=True)
            elif args.command == "deployment-record":
                result = d.record_review(args.state, json.loads(args.record))
            elif args.command == "deployment-status":
                result = d.read(args.state, "custom-deployment.json", {"state": "draft"})
            elif args.command == "deployment-checkpoint":
                result = d.checkpoint(args.state, args.phase, args.detail)
            elif args.command == "deployment-requirement":
                result = d.requirement(args.state, args.id, args.status, args.evidence)
            elif args.command == "deployment-verify":
                record = d.read(args.state, "custom-deployment.json")
                if not record:
                    raise ValueError("No reviewed custom deployment")
                result = d.verify(record['plan']['target'], record['plan'])
                print(json.dumps(result, indent=2))
                return 0 if result['boot_floor_passed'] else 1
            else:
                result = d.finalize(args.state)
        elif args.command == "name-agent":
            from .profile import name_agent
            from .choices import update
            result = name_agent(args.state, args.name)
            update(args.state, "agent_name", args.name)
        elif args.command == "sync-mcp":
            result = runtime.sync_installed_mcp(args.state, args.config)
        elif args.command == "local-policy":
            result = runtime.local_policy(args.state, args.config)
        elif args.command == "connect-account":
            return runtime.connect_account(args.state, args.account, args.config)
        elif args.command == "onboard":
            return runtime.onboard(args.state, args.config)
        elif args.command == "chat":
            from .deployment import mode
            selected = mode(args.state)
            # New sessions prevent a mode switch retaining contradictory cached instructions.
            command = ["tui", "--session", "deployment-custom"] if selected == "custom" and discover()['phase'] == 'live' else ["tui"]
            if args.welcome:
                command += ["--message", "Help me with this computer. Check where you are running and my saved intentions, then ask just the next useful question. Do not assume that live media means I want to erase or install."]
            if args.resume_install:
                command += ["--message", "The local installation review returned. Read system-agent install-status and, in custom mode, deployment-status. Explain the actual result and resume only unfinished authorized work. Do not equate copied installation files with a verified installed boot."]
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
