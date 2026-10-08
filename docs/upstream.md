# Reviewed upstream inputs (2026-10-06)

Current Arch source selection (2026-10-08): official npm stable release 2026.9.9,
with matching ACPX/Codex packages. NixOS remains pinned at 2026.9.5. Older
qualification records below describe their original artifacts, not rebuilt ISOs.

- [OpenClaw latest release](https://github.com/openclaw/openclaw/releases/tag/v2026.9.8):
  latest observed GitHub release, published 2026-10-03. Its version differs from
  the official Nix package pin. Do not substitute it without new dependency locks.
- [Official Nix packaging](https://github.com/openclaw/nix-openclaw/tree/f62d33f760bcbdbc6a52ac589eae22bf99201f90):
  used directly by the flake, including its npm dependency lock and helper layout.
  `nix/sources/openclaw-source.nix` pins 2026.9.5. The source repo provides Linux
  packaging and a Home Manager systemd integration; this project supplies its
  own NixOS system service under a dedicated account.
- [Nix behavior](https://docs.openclaw.ai/install/nix): explicit config/state paths,
  read-only config under OPENCLAW_NIX_MODE; mutable onboarding is unavailable.
- [CLI onboarding](https://docs.openclaw.ai/cli/onboard): official guided flow,
  `--skip-daemon` when this project owns service management. Upstream
  `--install-daemon` ordinarily installs a per-user Linux service; it is not used
  to create a competing service here.
- [Gateway CLI](https://docs.openclaw.ai/cli/gateway): foreground `gateway run`
  is supervised by the distro adapter. `health --json` is checked separately.
- [Workspace](https://docs.openclaw.ai/concepts/agent-workspace): AGENTS, SOUL,
  IDENTITY and optional BOOT guidance; SQLite-backed runtime state is separate.
- [Native backup](https://docs.openclaw.ai/cli/backup): full state archive and
  canonical SQLite snapshot verification. Use full backup rather than only config.
- [Released OpenZFS 2.4.4](https://github.com/openzfs/zfs/releases/tag/zfs-2.4.4):
  Linux support range 4.18–7.2. Locked Nixpkgs exposes Linux 7.2.9 and ZFS 2.4.4.
  Its deprecated latestCompatibleLinuxPackages helper does not select the newest
  kernel; this module selects the pinned latest kernel and keeps the module guard.
- [Locked Nixpkgs OpenClaw package](https://github.com/NixOS/nixpkgs/blob/151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4/pkgs/by-name/op/openclaw/package.nix):
  version 2026.6.33 is marked insecure for the project’s broad prompt-injection
  exposure. It is not used, and no permittedInsecurePackages override is added.
  Using another package source does not eliminate that architectural risk; the
  restricted service and explicit capabilities remain necessary.

Live documentation can move ahead of the pinned release. Actual command/config
compatibility is determined by the pinned runtime and VM tests, not documentation
alone. No provider credential, subscription or successful real model response has
been imported from the development host.
