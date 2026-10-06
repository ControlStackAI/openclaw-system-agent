# ControlStackAI System Agent

An OpenClaw-based local Linux assistant that stays with the installed computer.
The aim is to help people inspect, configure, maintain and recover their systems
using plain language and explicit owner authorization.

**Development prototype, not a qualified OS installer or unattended administrator.**
The resident lifecycle and NixOS service have passed isolated VM tests, including
gateway health, fixture conversations across reboot, private state and native
backup/restore. Arch packaging is an adapter under qualification. An owner-run broker implements narrowly scoped ZFS snapshots, pool scrub requests
and service restarts. The daemon gets no sudo permission. Disk erasure and
boot-critical updates have no executor.
See the exact [validation status](docs/qualification.md) before trying it.

This repository is separate from [agent-installer](https://github.com/ControlStackAI/agent-installer),
which owns live installation environments. No private host configuration or prior
agent state is included. All project history begins with generic source.

## What lives here

- `system_agent/`: environment facts, state initialization, handoff, reboot checks,
  readiness gates and capability planning.
- `identity/`: OpenClaw AGENTS, SOUL, IDENTITY, owner preferences and startup guidance.
- `runtimes/openclaw/`: official CLI/provider integration and reviewed input metadata.
- `adapters/nixos/`: declarative package/service and guarded kernel/ZFS selection.
- `adapters/arch/`: native lifecycle PKGBUILD and restricted systemd service.
- `contracts/`: pinned installer compatibility and a proposed narrow handoff.
- `tests/`: unit tests and an isolated NixOS gateway/ZFS VM test.

## Developer check

```sh
python3 -m unittest discover -s tests -v
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
The eventual friendly first-run flow is specified in [onboarding](docs/onboarding.md);
provider setup on NixOS is not yet a novice-ready UI.

The conversation profile distinguishes setup, maintenance and recovery. During
setup it asks about a desktop or no desktop, then other relevant OS decisions
one at a time. A private USER.md template separates owner intentions from system
facts and approvals. Profile writing needs an authorized workspace tool; desktop
installation and a deterministic setup questionnaire are not implemented.

Read the [state/recovery model](docs/state-and-recovery.md),
[live ISO decision](docs/live-iso.md), and [upstream evidence](docs/upstream.md).
