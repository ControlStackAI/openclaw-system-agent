# Development desktop

The Hyprland option uses an owner-editable Quickshell desktop with three separate
islands. The left holds applications and workspaces, the center monitors the
resident OpenClaw service, and the right opens audio, connections and system
settings. Empty space between islands passes pointer input through to the desktop.
The launcher is a centered overlay: type to search, use arrow keys to select,
Enter to open and Escape to close. Application icons and descriptions come from
the installed desktop entries, including terminal applications.

Audio settings list speakers and microphones separately, with default-device
selection, volume and mute. Connections show NetworkManager's actual wired and
wireless devices. Wi-Fi passwords are masked and passed directly to NetworkManager
through D-Bus, never through command arguments or shell logs. Enterprise networks
and advanced profiles use NetworkManager's graphical connection editor. A saved
network can be retried; a failed password prompts again. Bluetooth, brightness,
system usage, screen lock, sign-out and a temporary keep-awake control are also
available. Keep-awake resets with the shell; manual locking remains available.
Battery percentage appears only when a laptop battery is present.

The OpenClaw island monitors the project’s `controlstack-agent.service`, with
memory, CPU usage and restart count in its detail panel. “Running” means the
service is active, not that a provider is signed in or a model response succeeded.
Unavailable counters stay unavailable. The unprivileged telemetry helper reads
only allowlisted systemd properties and `/proc` statistics; it cannot read the
resident agent's private state, credentials or conversations.

## Included development tools

All installed profiles use Neovim as `EDITOR` and `VISUAL`, with `vi` and `vim`
aliases. Small readable defaults apply before the owner's `~/.config/nvim/init.lua`.
Git, Git LFS, GitHub CLI, delta, ripgrep, fd, fzf, jq, yq, tmux, btop and standard
archive/network tools are included. Language tooling includes Python/uv, Node/pnpm,
Go, Rust/Cargo, C/C++, CMake, Ninja, Make, pkg-config and GDB. Nix tooling includes
nixd, nixfmt, direnv and nix-direnv. Podman provides rootless containers; no Docker
socket or remote SSH server is enabled by this profile. Use per-project Nix shells
for exact language versions. Hyprland also includes Kitty, Firefox, a file manager,
a graphical password/keyring manager and the audio mixer.

Codex CLI, Claude Code CLI, Codex Desktop (inside the official ChatGPT Linux app)
and Claude Desktop are pinned through the public `numtide/llm-agents.nix` input.
Their upstream Linux binaries and NixOS compatibility wrappers are included, with
all runtime helpers. Owner sign-in happens after installation; no operator login
or live installer credentials are imported. Desktop sign-in requires network access.
NixOS is outside the vendors' listed supported Linux distributions, so NixOS launch
qualification and authenticated product functionality must be reported separately.

This repository's source is MIT licensed. The development image also contains
proprietary vendor applications under their own terms; it is not an all-free-software
image. Nix input revisions and upstream artifact hashes remain pinned. The system
kernel and released OpenZFS pins are independent of these application packages.

## References

- [Quickshell audio API](https://quickshell.org/docs/v0.3.0/types/Quickshell.Services.Pipewire/Pipewire/)
- [Quickshell NetworkManager API](https://quickshell.org/docs/v0.3.0/types/Quickshell.Networking/Networking/)
- [Official ChatGPT/Codex Linux app](https://learn.chatgpt.com/docs/linux/linux-app)
- [Official Claude Desktop Linux support](https://code.claude.com/docs/en/desktop-linux)
- [Pinned public AI packaging](https://github.com/numtide/llm-agents.nix/tree/59d0417c2017794f8872b5556f133c8b0b413734)

Virtual machines qualify software interactions, not physical audio quality,
Bluetooth pairing, laptop backlight behavior or real wireless coverage. Those
hardware checks remain separate from synthetic audio/device tests. Vendor desktop
launch tests do not qualify signed-in conversations or Claude Cowork's nested VM.

The current application pin provides Codex CLI 0.160.0, Claude Code 2.1.289,
ChatGPT/Codex Desktop 26.930.41038 and Claude Desktop 2.9939.4. NixOS updates
replace those packages through reviewed pins. The ChatGPT wrapper also repairs
the ELF loader paths of vendor runtime bundles downloaded into the owner's cache;
those later downloads are not part of the image's reproducible build or VM
qualification. Claude's compatibility wrapper uses a normal user FHS environment.
