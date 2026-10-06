# OpenClaw USB image

The NixOS-first implementation lives in this repository and consumes the pinned
agent-installer readiness checks. Its own adapter builds a live ISO, runs official
OpenClaw onboarding and the TUI, then installs the resident service. The shared
installer repository remains unchanged; its Codex dispatcher is not represented
as an OpenClaw implementation.

The live image uses the complete official `openclaw-gateway` Nix package, including
its runtime dependencies. It disables messaging channels and network discovery.
“Minimal” refers to this local purpose, not extracting a single runtime executable.
The build pins remain in flake.lock. Installed desktops are fetched during target
preparation rather than all bundled into the live image.

Live config, identity, sessions and credentials reside under the private tmpfs
`/run/controlstack-agent`. Reboot or the explicit forget action removes the session.
Leaving the setup menu preserves it until reboot so the conversation can reopen.
Installed state lives on its own ZFS dataset under `/var/lib/controlstack-agent`.
Fresh installed authentication is required. The handoff is limited to validated
OS choices and boot facts; arbitrary Markdown, transcripts and credentials do
not cross the boundary. The target USER.md is generated from those typed choices.

Booting USB media alone does not authorize installation. The assistant establishes
whether the owner wants setup, maintenance or recovery. Whole-disk installation
requires a separate local review, built target and exact disk confirmation. The
resident agent has no root permission and cannot approve that review itself.

See [USB setup](usb-setup.md) for the user journey and
[qualification](qualification.md) for exact tested paths. Earlier Codex ISO and
hardware results are not evidence for this image. Secure Boot and physical-device
qualification are not claimed. Installed-root recovery remains separate work.
