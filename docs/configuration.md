# Configuration and privilege plan

The NixOS module creates the dedicated `controlstack-agent` account, persists
state under `/var/lib/controlstack-agent` (0700), uses a 0600 gateway token file,
binds the gateway to loopback and enables no messaging channels or elevated tools.
The declarative config lives at `/etc/controlstack-agent/openclaw.json`; it may
contain runtime SecretRefs but must never contain actual secrets in the Nix store.
The runtime receives OPENCLAW_NIX_MODE=1. Mutable onboarding/config/update commands
are deliberately unavailable in that mode.

The service can read system files allowed to its account. Its only persistent
writable area is its state directory. It has a private temporary directory and
cannot see operator homes or host devices. It receives no sudo permission.
`workspaceExecution = true` explicitly permits shell and edits as this account;
it does not authorize root work and can damage this account's own state.

Use `services.controlstackAgent.settings` for provider/model configuration.
Provision provider credentials separately with a secret manager or private file
readable only by the service account, referenced by OpenClaw's file SecretRef.
Do not supply keys on command lines, in exported environment variables or in Nix
strings. The current prototype needs administrator configuration; it must not be
presented as a completed novice onboarding flow.

The Arch unit has the same privilege shape. Its PKGBUILD packages this project's
lifecycle code only; a complete pinned upstream runtime must be supplied separately.
It does not install an unversioned AUR package or execute a download-and-run script.
Do not enable it until the runtime and fresh provider setup are verified in a VM.

The optional NixOS ZFS profile pins released ZFS 2.4.4 with Linux 7.2.9 from the
locked package set. Compatibility guards remain enabled. The module changes
kernel selection only when the explicit ZFS option is enabled; it does not run a
pool upgrade, format storage or enable feature flags. A disk layout, bootloader,
initramfs and recovery plan still need target-specific review and boot tests.

## Owner-run maintenance

`services.controlstackAgent.capabilities` accepts exact `datasets`, `pools`, and
`services` lists, all empty by default. These control the separate root-only
`system-agent-admin` command. `plan snapshot pool/data` produces the exact target,
resource identity, boot ID, expiration and approval digest without making changes.
The owner reviews that plan before `apply PLAN_ID --approve DIGEST`. The service
account cannot access root-private plans or grant itself administrator authority.
Arch administrators must provision the same root-owned policy at
`/etc/controlstack-agent/capabilities.json`; absent policy denies all actions.
This CLI is currently an administrator workflow, not the finished novice UI.

`RestrictSUIDSGID` is explicitly disabled because systemd's filter returns ENOSYS
for `openat2`, which OpenClaw requires for safe gateway-lock path resolution.
The first hosted gateway VM found this conflict before the health endpoint could
start. NoNewPrivileges, the empty capability set and filesystem protections remain.
See [systemd's seccomp implementation](https://github.com/systemd/systemd/blob/main/src/shared/seccomp-util.c)
and [upstream issue 43314](https://github.com/systemd/systemd/issues/43314).
