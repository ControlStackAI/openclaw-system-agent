# ControlStackAI System Agent

The [development desktop](docs/development-desktop.md) includes three Quickshell islands, native device controls and pinned coding tools. See the exact image revisions and test scopes below.

**Wi-Fi correction:** the first Ventoy NixOS image disabled NetworkManager’s Wi-Fi backend. The source now enables its DBus-controlled supplicant for both live and installed systems. Use the corrected image described in [qualification](docs/qualification.md); the older download below is retained as historical evidence, not the recommended hardware test image.

The [Ratatui setup interface](docs/ratatui.md) adds OpenClaw artwork, protected
provider connection and a guided local installation review on both distributions.

An OpenClaw-based local Linux assistant that stays with the installed computer.
The aim is to help people inspect, configure, maintain and recover their systems
using plain language and explicit owner authorization.

**VM-tested development prototype.** Arch and NixOS USB images open preconfigured
OpenClaw setup and install a resident assistant on ZFS. Arch offers Hyprland +
Quickshell or no desktop; NixOS also offers KDE Plasma and GNOME.
The current Hyprland USB-to-installed-system journey passed isolated VM tests.
The preceding five-case build also passed encrypted Plasma, GNOME and console
installation, ordinary owner login and visible fixture conversations.
Hyprland + Quickshell also passed screen locking and customization persistence
across another reboot. See the [desktop guide](docs/hyprland-quickshell.md).
Real provider accounts and physical hardware remain unqualified.

Follow the [owner's USB guide](docs/usb-setup.md) or the
[Arch installation guide](docs/arch-installation.md). Read the exact
[qualification status](docs/qualification.md), including the ISO checksum, before
trying it. Installation currently uses a whole internal disk in UEFI mode.
The [old development ISO with the Wi-Fi defect](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487/artifacts/11497253654)
is retained only as historical evidence.

The resident lifecycle also passed separate reboot and native backup/restore
tests. The [Arch image](docs/arch-installation.md) now has a native UEFI/ZFS installer with the shared Hyprland desktop. See the qualification matrix for tested artifacts.
An owner-run broker implements narrowly scoped ZFS snapshots, scrub requests and
service restarts; its friendly approval UI remains future work. The daemon has
no sudo grant, disk-erasure executor or boot-critical update executor.

This repository is separate from [agent-installer](https://github.com/ControlStackAI/agent-installer),
whose pinned network/clock/ZFS readiness code is consumed by this image. No private host configuration or prior
agent state is included. All project history begins with generic source.

## What lives here

- `system_agent/`: environment facts, state initialization, handoff, reboot checks,
  readiness gates and capability planning.
- `identity/`: OpenClaw AGENTS, SOUL, IDENTITY, owner preferences and startup guidance.
- `runtimes/openclaw/`: official CLI/provider integration and reviewed input metadata.
- `adapters/nixos/`: declarative package/service and guarded kernel/ZFS selection.
- `adapters/arch/`: native image payload, disk installer, desktop and systemd services.
- `adapters/shared/`: owner-editable desktop assets and the Hypruse bridge.
- `contracts/`: pinned installer compatibility and the narrow installed-boot handoff.
- `tests/`: unit tests and an isolated NixOS gateway/ZFS VM test.

## Image source selection

Use [locked image builds](docs/image-builds.md) to choose an Arch ISO/package
snapshot or a NixOS nixpkgs revision. Resolve `latest` once, then build the saved
lock without updates. Arch supports Hyprland or a console session; NixOS also offers Plasma and GNOME. Byte-identical
independent rebuilds remain unqualified.

Installed desktops also offer [Coding Assistant Sign-in](docs/security-key-sign-in.md)
with browser/device-code login and security-key device support. Physical YubiKey
login is not yet tested, and key insertion alone is not authentication.

## Developer check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/image.py build --lock images/nixos.lock.json --output dist/nixos
nix build .#system-agent
nix build .#openclaw
nix build .#checks.x86_64-linux.networking-vm --max-jobs 1 --cores 2
nix build .#checks.x86_64-linux.core-vm --max-jobs 1 --cores 2
nix build .#checks.x86_64-linux.lifecycle-vm --max-jobs 1 --cores 2
```

Only x86_64 Linux is evaluated in this first implementation. Builds use the exact
`flake.lock`; updates must be reviewed. The official Nix packaging currently pins
OpenClaw 2026.9.5 for NixOS. Arch separately locks the published OpenClaw 2026.9.8 release and its dependency tree. Both include their matching Codex agent runtime.

For a disposable NixOS VM, add this flake as an input, import
`inputs.system-agent.nixosModules.default`, and enable
`services.controlstackAgent.enable`. To test the pinned latest supported kernel,
also enable `services.controlstackAgent.zfs.enable` and provide a unique hostId.
This does not partition disks, install a root filesystem or select a bootloader.
See [configuration](docs/configuration.md) for the explicit service privilege plan.

`system-agent inspect` refreshes observed facts without writing. `refresh` saves
facts in private state. `verify-boot` requires a handoff and an independent reboot.
`health` checks authenticated gateway health. `chat` opens the official local TUI.
These commands are intended to run with the service account's state/config context.
The USB and installed-system setup screen connects a provider with official OpenClaw authentication commands, NetworkManager and the local conversation. ChatGPT uses device-code login; the general onboarding wizard is not part of the normal path. See [USB setup](docs/usb-setup.md).

The conversation profile distinguishes setup, maintenance and recovery. During
setup it asks about a desktop or no desktop, then other relevant OS decisions
one at a time. A private USER.md template separates owner intentions from system
facts and approvals. The USB profile can record typed non-secret choices for the
local review screen. The NixOS adapter implements no desktop, Plasma, GNOME and Hyprland + Quickshell,
regional settings, a local account and optional native ZFS encryption. Check the
qualification matrix before treating any offered path as validated.

Read the [state/recovery model](docs/state-and-recovery.md),
[live ISO decision](docs/live-iso.md), and [upstream evidence](docs/upstream.md).
