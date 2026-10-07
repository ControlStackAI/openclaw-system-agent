# ControlStackAI System Agent

The new [development desktop](docs/development-desktop.md) adds three Quickshell islands, native device controls and pinned coding tools. Its updated image qualification is in progress; the previously qualified image below predates this redesign.

An OpenClaw-based local Linux assistant that stays with the installed computer.
The aim is to help people inspect, configure, maintain and recover their systems
using plain language and explicit owner authorization.

**VM-tested development prototype.** The NixOS USB opens OpenClaw setup,
offers no desktop, KDE Plasma, GNOME or Hyprland + Quickshell, and installs a resident assistant on ZFS.
The complete USB-to-installed-system journey passed isolated VM tests, including
encrypted Plasma boot, ordinary owner login and visible fixture conversations.
Hyprland + Quickshell also passed screen locking and customization persistence
across another reboot. See the [desktop guide](docs/hyprland-quickshell.md).
Real provider accounts and physical hardware remain unqualified.

[Download the tested development ISO](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37576857541/artifacts/11463339348) and follow the
[owner's USB guide](docs/usb-setup.md). Read the exact
[qualification status](docs/qualification.md), including the ISO checksum, before
trying it. Installation currently uses a whole internal disk in UEFI mode.

The resident lifecycle also passed separate reboot and native backup/restore
tests. Arch packaging is scaffolded and has no native runtime qualification.
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
- `adapters/arch/`: native lifecycle PKGBUILD and restricted systemd service.
- `contracts/`: pinned installer compatibility and the narrow installed-boot handoff.
- `tests/`: unit tests and an isolated NixOS gateway/ZFS VM test.

## Developer check

```sh
python3 -m unittest discover -s tests -v
nix build .#live-iso --out-link result-iso
nix build .#system-agent
nix build .#openclaw
nix build .#checks.x86_64-linux.core-vm --max-jobs 1 --cores 2
nix build .#checks.x86_64-linux.lifecycle-vm --max-jobs 1 --cores 2
```

Only x86_64 Linux is evaluated in this first implementation. Builds use the exact
`flake.lock`; updates must be reviewed. The official Nix packaging currently pins
OpenClaw 2026.9.5. The newer upstream 2026.9.8 is recorded, not silently substituted.

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
The USB and installed-system setup screen wraps official OpenClaw onboarding,
NetworkManager and the local conversation. See [USB setup](docs/usb-setup.md).

The conversation profile distinguishes setup, maintenance and recovery. During
setup it asks about a desktop or no desktop, then other relevant OS decisions
one at a time. A private USER.md template separates owner intentions from system
facts and approvals. The USB profile can record typed non-secret choices for the
local review screen. The NixOS adapter implements no desktop, Plasma, GNOME and Hyprland + Quickshell,
regional settings, a local account and optional native ZFS encryption. Check the
qualification matrix before treating any offered path as validated.

Read the [state/recovery model](docs/state-and-recovery.md),
[live ISO decision](docs/live-iso.md), and [upstream evidence](docs/upstream.md).
