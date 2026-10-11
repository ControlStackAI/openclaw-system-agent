# Reviewed upstream inputs (2026-10-11)

Both images now select official OpenClaw npm release 2026.10.1, with matching
ACPX/Codex packages in a complete dependency lock. NixOS keeps that explicit pin;
Arch checks stable before installation. Historical qualification records retain
the versions of their original artifacts.

- [OpenClaw 2026.10.1](https://github.com/openclaw/openclaw/releases/tag/v2026.10.1):
  latest observed official release. The versioned npm artifact and its integrity
  hash are recorded in `runtimes/openclaw/npm/package-lock.json`.
- [Official Nix packaging](https://github.com/openclaw/nix-openclaw/tree/f62d33f760bcbdbc6a52ac589eae22bf99201f90):
  the flake reuses its dependency staging, runtime layout and executable wrapper.
  Its upstream release pin is still 2026.9.5. This project overrides the runtime
  with its own complete 2026.10.1 npm lock and matching bundled plugins, retaining
  released JavaScript and checking the required artifact surfaces during build.
  The source repo provides Linux packaging and Home Manager integration; this
  project supplies its own NixOS system service under a dedicated account.
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
