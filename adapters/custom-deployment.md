# Native custom deployment contract

This document is shipped with the live runtime beside its distro adapters. Use
`system-agent deployment-mode` to inspect the selected workflow. Custom mode uses
native tools and the owner's reviewed configuration, not the preset disk executor.

## Plan and local review

Save this schema as a private JSON file in the live workspace, filling in actual
owner choices and the freshly inspected disk. No credentials belong in it.

```json
{
  "schema": 1,
  "distro": "arch",
  "disk": "/dev/nvme0n1",
  "target": "/mnt/controlstack-custom",
  "base": "minimal",
  "storage_action": "erase",
  "storage_plan": "Replace this disk with a 1 GiB EFI partition and portable ZFS root, home and agent datasets.",
  "access_plan": "Owner can administer via sudo; resident service has private persistent state without root access.",
  "recovery_plan": "Keep this USB, preserve generated configuration and arrange an independent backup.",
  "username": "owner",
  "requirements": [
    {"id": "desktop", "description": "Hyprland with a custom Quickshell shell"},
    {"id": "login", "description": "Custom graphical login with the owner's supplied artwork"},
    {"id": "resident", "description": "Persistent OpenClaw with fresh provider sign-in after reboot"}
  ]
}
```

`storage_action` may be `preserve`; describe every intended partition/filesystem
change and data retained. Review currently covers one unused internal disk and
protects the boot USB, mounted devices, imported pools and removable disks.
`base` is `minimal` or `preset`. It describes the intended starting point; it does
not automatically select or unpack packages. Requirements have unique IDs and
are not limited to predefined desktop names.

Call `system-agent deployment-review PLAN.json`. The console interrupts chat,
shows the concrete plan/current disk, retries mistyped erase confirmation, and
returns to the conversation. Read `deployment-status`. Only an approved record
allows the agent to start the reviewed native operations. Inspect the disk again
before the first write. Record progress before operations with
`deployment-checkpoint preparing|writing|configuring|needs-attention "detail"`.
A failure preserves the record; resume from actual observed progress, never repeat
erasure merely because a command failed. Local review is a workflow, not a sandbox
against the live agent's intentional full root access.

## Arch: minimal or preset starting point

Read `/etc/controlstack-agent/arch-target.json`, `/etc/controlstack-agent/image-inputs.json`, the frozen `/etc/pacman.conf`
and the pinned kernel/OpenZFS receipts. The live image has `pacstrap`,
`arch-chroot`, partition/filesystem tools and the complete immutable runtime.

For a minimal base, use `pacstrap` with the selected signed archive configuration
and only the boot/system packages the requested plan needs. Typical starting
packages include base, the matched kernel, firmware/microcode, initramfs tooling,
NetworkManager, wpa_supplicant, sudo, Python and filesystem tools. For ZFS obtain
and signature-verify the exact matching kernel/module/utilities from the image
lock; never perform a partial rolling upgrade. Use the portable compatibility
profile. Keep `/etc/pacman.conf` and a `pacman -Q` manifest on the target.

For a preset starting point, checksum-verify and unpack `payload` from the input
record. It includes the development desktop packages; disable/remove unwanted
services and packages deliberately. Do not call the preset install executor after
custom review: it would request another erasure and impose its own choices.

Reuse `adapters.arch.target.configure(target, runtime, baseline_choices)` only
when its seed defaults are wanted. `desktop: none` seeds the resident service and
console configuration; `hyprland` also seeds the desktop. This function does not
partition, mount, create accounts, generate the initramfs, install a bootloader or
enable units. It is optional; custom native configuration may replace any seeded
file. Copy only the public immutable `/nix` runtime closure and official
`/opt/codex` bundle if using its wrappers, never live agent state. Create the
`controlstack-agent` system account and the owner account, enable the resident
service/boot-check, and configure its persistent private state. No live sudo rule
belongs in the target. Keep NetworkManager as the sole network/DNS owner.

Generate fstab, hostid (ZFS), matching modules/initramfs, and EFI boot entries.
For ZFS the initramfs must contain the ZFS hook/module and the intended root dataset;
verify `modinfo` vermagic against the installed kernel. Install systemd-boot to
`/boot` for the provided verifier. Arbitrary bootloaders need a verifier extension.
Configure only the chosen greeter, its compositor/backend and session command.
A Quickshell greeter must communicate with a real login backend such as greetd;
copying a desktop QML file into a login directory does not implement authentication.

## NixOS: native configuration

Read `/etc/controlstack-agent/install-inputs.json` for the exact nixpkgs, source,
core and runtime store paths. Generate a native NixOS configuration, build it before
disk writes when possible, then install the resulting closure with `nixos-install
--root /mnt/controlstack-custom --system SYSTEM --no-root-passwd --no-channel-copy`.
Retain the expression and all its input references under the target's `/etc/nixos`.
Use the source's `adapters/nixos/module.nix` for the resident lifecycle and
`networking.nix` for NetworkManager. Set `services.controlstackAgent.enable`,
`mutableProviderSetup`, `workspaceExecution`, `package` and `corePackage` explicitly.
The resident ZFS option uses the pinned latest kernel and rejects a build when
the pinned released ZFS module does not support it. Enable it for ZFS; preserve
that compatibility check and never force an incompatible newer kernel.

For a minimal base, do not import `desktop.nix` or `development.nix`. Add any desired
desktop, graphical login, applications and policies directly to the generated
configuration. For a preset base import the relevant modules, then explicitly
remove/override the preset greeter when replacing it; evaluate for service conflicts.
The owner-policy module can supply key authentication and always-on behavior.
A different PAM service name needs its own reviewed key rule. Configure the owner
with `hashedPasswordFile = "/var/lib/controlstack-owner.password"` and create a
locked placeholder before initial activation; protected account setup replaces it.

When generating files, set normal system permissions explicitly: traversable
public system directories, readable non-secret configuration and machine identity,
and private credentials. The live console uses a restrictive umask; blindly
inheriting it can prevent the resident account from reading `/etc/machine-id`.

Provide actual root/EFI mount definitions, firmware and initrd drivers for this
hardware, host identity, local console, owner account and resident service. Keep
remote login off unless requested. Pin all extra inputs and retain generated files;
selecting a pinned ISO does not automatically pin arbitrary later custom downloads.

## Secrets, verification and handoff

After creating the target owner account, call `system-agent deployment-account`.
The root console collects and hashes the password locally and optionally enrolls
and tests a YubiKey. It writes to the target only and returns non-secret status.
The agent must configure the selected greeter's PAM and lock/removal policy; key
enrollment alone does not implement them. Use `deployment-encryption-key` for protected local disk-passphrase entry before
native encryption setup. It stages a 0600 file inside a root-owned 0700 RAM
directory and returns only its path. Feed that file directly to the encryption
tool, never print it, switch the installed unlock method to the reviewed prompt
or key arrangement, and remove the RAM file after use. Do not copy it into the
target, chat, plan files, shell arguments or receipts.

Run `sudo -n system-agent --state /run/controlstack-agent deployment-verify`.
The verifier checks mounted writable root, identity, init, account/PAM, kernel,
modules/initramfs, EFI files and resident service. These are structural checks,
not proof of successful boot or complete hardware support. Also validate matching
kernel/ZFS versions, native build results and each requested feature independently.
Record concrete evidence with `deployment-requirement ID passed|failed|pending
"evidence and limitations"`; these are agent-reported feature tests, clearly
separate from the programmatic boot floor. Failures and unreviewed pending items
block finalization. For tests that require an actual installed boot, keep the
result pending and call `system-agent deployment-first-boot-review`. The root
console asks the owner whether each pending item must finish before reboot,
needs post-boot verification, or is optional work they approve deferring. A final
confirmation saves that schedule without editing the approved plan or evidence.
Cancelled reviews preserve prior records. Changed evidence invalidates its prior
pending-work approval; failed checks cannot be deferred through this review.
The minimum boot/storage checks always remain mandatory.

`sudo -n system-agent --state /run/controlstack-agent deployment-finalize` checks
storage identity, requirements/the local first-boot schedule and the boot floor and creates fresh resident
handoff metadata. Pending tasks remain pending in the lifecycle record and new
USER.md; `requested_features_verified` stays false. It refuses to overwrite existing resident state. It copies no
live credentials or conversation. Preserve generated configuration and package
manifests separately on the target. Then sync, unmount the target and export only
its pool without force. Preserve the installation and diagnose busy mounts rather
than erase it again. Offer reboot only after successful teardown.

After booting the installed disk without the ISO, `system-agent verify-boot`
compares distro, machine identity, filesystem/dataset and a new boot ID. Only then
is boot verified. Desktop/login, actual provider replies and physical keys remain
separate checks. The resident agent reads the reviewed requirements from its new
workspace and lifecycle record and continues maintaining the custom system.
