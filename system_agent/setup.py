"""Local console setup. Privileged steps are never exposed as agent tools."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from .facts import discover

ACCOUNT = "controlstack-agent"


def choose(question, options):
    print("\n" + question, flush=True)
    for number, label in enumerate(options, 1):
        print(f"{number}) {label}")
    while True:
        answer = input("Choose a number: ").strip()
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return int(answer)
        print("Please choose one of the numbers above.")


class Setup:
    def __init__(self, live):
        self.live = live
        self.state = Path("/run/controlstack-agent" if live else "/var/lib/controlstack-agent")

    def agent(self, *args, capture=False):
        # A fresh allowlisted environment is built by system-agent's runtime adapter.
        env = {"PATH": os.environ["PATH"], "TERM": os.environ.get("TERM", "linux"),
               "LANG": os.environ.get("LANG", "en_US.UTF-8"), "HOME": str(self.state),
               "OPENCLAW_STATE_DIR": str(self.state),
               "OPENCLAW_CONFIG_PATH": str(self.state / "openclaw.json"), "OPENCLAW_NIX_MODE": "0"}
        for key in ("SSL_CERT_FILE", "NIX_SSL_CERT_FILE"):
            if key in os.environ:
                env[key] = os.environ[key]
        return subprocess.run(["runuser", "-u", ACCOUNT, "--", "system-agent", *args],
                              env=env, capture_output=capture, text=True)

    def connect(self):
        # Consume the pinned installer readiness/networking implementation.
        from core.checks import Readiness
        profile = json.loads((Path(__file__).resolve().parent.parent / "profiles/nixos.json").read_text())
        checks = Readiness(profile, auth_endpoints=["https://docs.openclaw.ai/"])
        while not checks.ready():
            answer = choose("The connection is not ready yet.", ["Set up Wi-Fi or Ethernet", "Try again", "Back"])
            if answer == 1:
                checks.connect()
            if answer == 3:
                return False
        return True

    def sign_in(self):
        if not self.connect():
            return
        print("\nOpenClaw will help you choose an AI provider and sign in.\n"
              "Use its protected sign-in prompts. API billing may be separate from a subscription.")
        # Stop the gateway while the official wizard updates its private config.
        subprocess.run(["systemctl", "stop", "controlstack-agent.service"], check=True)
        try:
            result = self.agent("onboard")
        finally:
            # Pin the local access policy independently of onboarding's tool suggestions.
            self.agent("local-policy")
            subprocess.run(["systemctl", "start", "controlstack-agent.service"], check=True)
        if result.returncode:
            print("Sign-in did not finish. You can retry from this menu.")
        else:
            print("Sign-in setup finished. Open the conversation to check a real reply.")

    def chat(self):
        if not self.connect():
            return
        print("\nOpening your system assistant. Press Ctrl+C to return to this menu.\n"
              "A successful assistant reply confirms model access; a running service alone does not.")
        self.agent("chat", "--welcome")

    def forget(self):
        if not self.live:
            print("Installed history is preserved. Use sign-in setup to change providers.")
            return
        if choose("Forget this USB session, including its sign-in and conversation?", ["Keep it", "Forget it"]) != 2:
            return
        subprocess.run(["systemctl", "stop", "controlstack-agent.service"], check=True)
        if self.state != Path("/run/controlstack-agent") or self.state.is_symlink():
            raise ValueError("Unexpected live state location")
        shutil.rmtree(self.state)
        subprocess.run(["systemctl", "start", "controlstack-agent.service"], check=True)

    def run(self):
        print("\nWelcome to your OpenClaw System Assistant.\n"
              + ("You are running from the USB. Sign-in stays in memory and disappears after reboot.\n"
                 "OpenClaw will also be installed as your computer's resident assistant."
                 if self.live else "OpenClaw is installed on this computer. Your conversations stay here.\n"
                 "Please sign in again if this is your first installed boot; USB credentials were not copied."), flush=True)
        while True:
            labels = ["Sign in or change AI provider", "Talk to the assistant", "Connect to Wi-Fi or Ethernet"]
            if self.live:
                labels += ["Review choices and install NixOS", "Forget this USB session"]
            labels += ["Troubleshooting shell", "Leave setup"]
            answer = choose("What would you like to do?", labels)
            try:
                if answer == 1:
                    self.sign_in()
                elif answer == 2:
                    self.chat()
                elif answer == 3:
                    subprocess.run(["nmtui"])
                elif self.live and answer == 4:
                    from adapters.nixos.install import interactive
                    interactive(self.state)
                elif self.live and answer == 5:
                    self.forget()
                elif answer == len(labels) - 1:
                    subprocess.run(["bash", "-l"])
                else:
                    return
            except (OSError, ValueError, subprocess.CalledProcessError) as error:
                print(f"That step did not finish: {error}. Review the message before retrying.")


def main():
    if len(sys.argv) != 1 or os.geteuid() != 0 or not sys.stdin.isatty():
        print("Open System Assistant from the local console or desktop launcher.")
        return 1
    facts = discover()
    if facts["distro_id"] != "nixos" or facts["phase"] not in ("live", "installed-candidate"):
        print("Setup needs a confirmed NixOS live or installed environment.")
        return 1
    try:
        Setup(facts["phase"] == "live").run()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup closed. You can reopen System Assistant when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
