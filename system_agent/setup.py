"""Local console setup. Privileged steps are never exposed as agent tools."""
import json
import os
import shutil
import subprocess
import sys
import time
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
    def __init__(self, live, distro="nixos"):
        self.live = live
        self.distro = distro
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
                              env=env, capture_output=capture, text=True, umask=0o077)

    def connect(self):
        # Consume the pinned installer readiness/networking implementation.
        from core.checks import Readiness
        profile = json.loads((Path(__file__).resolve().parent.parent / f"profiles/{self.distro}.json").read_text())
        checks = Readiness(profile, auth_endpoints=["https://docs.openclaw.ai/"])
        while not checks.ready():
            answer = choose("The connection is not ready yet.", ["Set up Wi-Fi or Ethernet", "Try again", "Back"])
            if answer == 1:
                from .networking import connect
                connect()
            if answer == 3:
                return False
        return True

    def sign_in(self):
        if not self.connect():
            return
        print("\nOpenClaw is already installed and ready. We just need to connect your AI account.")
        choice = choose("Which account would you like to connect?", [
            "ChatGPT subscription — short code on your phone or another computer",
            "OpenAI API key — separate usage billing",
            "Another provider",
            "Back"])
        if choice == 4:
            return
        account = ("chatgpt", "openai-api", "other")[choice - 1]
        if account == "chatgpt":
            print("Open the short website shown next on your phone or another computer, then enter its code.\n"
                  "Keep this screen open while you approve. You do not need a browser on this USB.", flush=True)
        # Stop the gateway while the official wizard updates its private config.
        subprocess.run(["systemctl", "stop", "controlstack-agent.service"], check=True)
        try:
            result = self.agent("connect-account", account)
        finally:
            # Pin the local access policy independently of onboarding's tool suggestions.
            self.agent("local-policy")
            subprocess.run(["systemctl", "start", "controlstack-agent.service"], check=True)
        if result.returncode:
            print("Sign-in did not finish. You can retry from this menu.")
        else:
            print("Sign-in setup finished. Opening the conversation to check a real reply.")
            self.chat()

    def chat(self):
        if not self.connect():
            return
        print("\nConnecting to your assistant...", flush=True)
        deadline = time.monotonic() + 120
        while self.agent("health", capture=True).returncode:
            if time.monotonic() >= deadline:
                print("The assistant is not ready yet. Try again shortly, or open the troubleshooting shell.")
                return
            time.sleep(2)
        print("\nOpening your system assistant. Press Ctrl+D to return to this menu.\n"
              "A successful assistant reply confirms model access; a running service alone does not.")
        try:
            self.agent("chat", "--welcome")
        except KeyboardInterrupt:
            print("\nBack at the setup menu.")

    def keyboard(self):
        from .profile import LAYOUTS
        layout = LAYOUTS[choose("Which keyboard layout should this USB session use?", ["US", "UK", "German", "French", "Spanish"]) - 1]
        keymap = ("/etc/controlstack-agent/keymaps/" + layout if self.distro == "nixos" else
                  {"us": "us", "gb": "uk", "de": "de-latin1", "fr": "fr", "es": "es"}[layout])
        subprocess.run(["loadkeys", "-C", "/dev/tty0", "--quiet", keymap], check=True)
        subprocess.run(["systemctl", "start", "controlstack-agent.service"], check=True)
        saved = self.agent("setup-choice", "keyboard", layout, capture=True)
        if saved.returncode:
            print("The keyboard changed, but please choose it again during installation review.")
        print("Keyboard layout changed. The installation review will let you keep or change it.")

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
        if sys.stdout.isatty():
            print("\033[2J\033[H", end="", flush=True)
        print("\nWelcome to your OpenClaw System Assistant.\n"
              + ("You are running from the USB. Sign-in stays in memory and disappears after reboot.\n"
                 "OpenClaw will also be installed as your computer's resident assistant.\nThe USB starts with a US keyboard. Choose Change keyboard layout below if needed."
                 if self.live else "OpenClaw is installed on this computer. Your conversations stay here.\n"
                 "Please sign in again if this is your first installed boot; USB credentials were not copied."), flush=True)
        while True:
            labels = ["Connect your AI account or change provider", "Talk to the assistant", "Connect to Wi-Fi or Ethernet"]
            if self.live:
                labels += [("Review choices and install NixOS" if self.distro == "nixos" else "Review choices and install Arch Linux"), "Forget this USB session", "Change keyboard layout"]
            labels += ["Troubleshooting shell", "Leave setup"]
            answer = choose("What would you like to do?", labels)
            try:
                if answer == 1:
                    self.sign_in()
                elif answer == 2:
                    self.chat()
                elif answer == 3:
                    from .networking import connect
                    connect()
                elif self.live and answer == 4:
                    if self.distro == "arch":
                        from adapters.arch.install import interactive
                    else:
                        from adapters.nixos.install import interactive
                    result = self.agent("setup-choice", capture=True)
                    suggestions = json.loads(result.stdout) if result.returncode == 0 else {}
                    interactive(self.state, suggestions)
                elif self.live and answer == 5:
                    self.forget()
                elif self.live and answer == 6:
                    self.keyboard()
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
    if facts["distro_id"] not in ("nixos", "arch") or facts["phase"] not in ("live", "installed-candidate"):
        print("Setup needs a confirmed Arch or NixOS live or installed environment.")
        return 1
    try:
        Setup(facts["phase"] == "live", facts["distro_id"]).run()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup closed. You can reopen System Assistant when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
