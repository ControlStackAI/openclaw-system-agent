# Arch USB to resident desktop

Build the Arch image from `images/arch.lock.json` using the repository image
builder. The lock selects the Arch ISO, package archive, signed kernel/ZFS
packages, complete OpenClaw runtime and this project's reviewed source. Building
needs x86_64 Linux, Nix and Docker; the build host does not need to run Arch.

Boot the USB in UEFI mode. NetworkManager handles Ethernet and Wi-Fi. OpenClaw
is already installed: **Connect your AI account** configures only authentication.
ChatGPT uses a short device code approved on a phone or another computer. API
keys use the provider's protected prompt. A reply, rather than a service status,
confirms that the provider works. A troubleshooting root shell remains available.

The owner chooses Hyprland + Quickshell or no desktop, account name, computer
name, intended use, language, keyboard, time zone and optional disk encryption.
Plasma and GNOME remain NixOS choices until native Arch integration is qualified.
The complete native Arch payload is checked before disk approval. Installation
can finish without downloading desktop packages from the live session.

Only one unused internal disk of at least 32 GiB can be selected. USB, removable,
mounted, active-pool and unidentified disks are excluded. The review describes
privileges, storage and full Hypruse desktop control. The owner must type the
selected disk's serial confirmation before partitioning. Existing contents of
that disk are lost; dual boot and partition reuse are not supported.

The installed layout is a 1 GiB EFI partition and a ZFS pool with separate root,
home and agent-state datasets. The OpenZFS 2.2 compatibility profile limits
features for portable snapshots. Encryption is ZFS native encryption, with an
early keyboard-aware unlock prompt. Snapshots still require separate backups.
The kernel, ZFS module, utilities and initramfs are installed as a matched set.
Their package upgrades are held in pacman until an owner reviews a new matched
set. The package archive remains the selected snapshot; changing it is an
explicit maintenance decision, not an automatic rolling upgrade.

After shutdown and USB removal, sign in to the local account. The desktop opens
System Assistant. Installed state is fresh: no USB credentials, tokens, sessions
or workspace are copied. Only reviewed OS preferences and a typed installation
handoff are retained. Boot verification checks the new boot, machine identity,
distribution and writable ZFS root independently of model access.

The desktop shares the NixOS theme and Nova shortcuts: three compact islands,
OpenClaw monitoring in the center, audio/network controls on the right, an icon
launcher, Ghostty, Firefox, Neovim and the selected development tools. Hypruse
runs in the owner's graphical session and exposes desktop control to the resident
agent over a peer-checked local socket. The owner can stop it from the center
island or Super+Shift+Backspace. NixOS MCP is not installed on Arch.

The OS, compositor and services are native Arch packages. OpenClaw and the AI
applications use complete immutable Nix-built runtime closures without requiring
a Nix daemon. Arch currently pins released OpenClaw 2026.9.8; NixOS retains its
2026.9.5 packaging pin. Configuration, credentials and conversations remain in
private writable state, outside the application closure. Advanced users can
change live configuration in RAM or customize their installed desktop; desktop
seed files never overwrite existing owner files.

See [qualification](qualification.md) for completed VM checks and limitations.
A successful build alone does not qualify installation or physical hardware.
