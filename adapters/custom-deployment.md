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
    {"id": "lua", "description": "Native hyprland.lua with the requested shortcuts"},
    {"id": "session", "description": "Custom login launches Hyprland through start-hyprland"},
    {"id": "login", "description": "Custom graphical login with the owner's supplied artwork"},
    {"id": "appearance", "description": "Dark system appearance by default; Ghostty follows it unless explicitly overridden"},
    {"id": "assistant-ui", "description": "Ratatui System Assistant opens in Ghostty after installed login"},
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

## Hyprland: Lua, launch and owner setup

For new Hyprland deployments use **native Lua**, normally
`$XDG_CONFIG_HOME/hypr/hyprland.lua` (default `~/.config/hypr/hyprland.lua`). The
pinned 0.56 package supports it. Read the installed package's version and example
before generating code; do not use historical hyprlang examples or assume every
old image pin has the same API. Do not generate `hyprland.conf`, pass a legacy
`--config` path, or translate legacy directives through Lua string calls.
If an explicitly selected older pin lacks Lua, resolve the version conflict with
the owner rather than silently falling back. This concerns Hyprland's compositor
configuration; hyprlock/hypridle have their own configuration formats.

The shipped `adapters/shared/hyprland/hyprland.lua` is a working reference, not a
requirement to install the preset desktop. For example, native bindings use:

```lua
hl.bind("SUPER + Return", hl.dsp.exec_cmd("ghostty"))
hl.bind("SUPER + B", hl.dsp.exec_cmd("firefox"))
```

On NixOS, generate the owner's Lua file declaratively or seed it once without
overwriting later edits. If Home Manager is selected, use an explicit Lua file
such as `xdg.configFile."hypr/hyprland.lua".text` and check that no other option
generates a competing legacy configuration. Retain the generating source on the
target. Do not assume that generic Hyprland `settings`/`extraConfig` examples emit
Lua: inspect the evaluated output of the selected module version.

### Match terminal and system appearance

Default to dark when the owner has not chosen an appearance. A requested system
theme includes Ghostty's terminal background, foreground and window chrome unless
the owner explicitly asks for a different terminal theme. Set the system's
`org.gnome.desktop.interface color-scheme` preference to `prefer-dark` (or the
chosen light preference), and ensure the session's settings portal exposes it.
On NixOS a writable default can be provided by `programs.dconf.profiles.user.databases`
with `settings."org/gnome/desktop/interface".color-scheme = "prefer-dark"`; do not
lock this preference against later owner changes. Include the appropriate GTK
settings portal for a minimal Hyprland session.

Configure Ghostty itself too. For automatic system appearance use a light/dark
pair that exists in the pinned package, for example:

```ini
theme = dark:Catppuccin Frappe,light:Catppuccin Latte
window-theme = system
```

Check availability with `ghostty +list-themes`. Hard-coded foreground/background
settings override theme colors: migrate conflicting defaults deliberately, while
preserving an explicit owner terminal-theme override. `window-theme = dark` alone
only changes chrome, not the terminal palette. Retain the source that generates
the owner's Ghostty configuration and verify the effective config and a visible
terminal after login. The preset seeds its own dark colors; importing only a
terminal package into a custom system does not import those defaults. If automatic
appearance is unavailable, use the owner's selected fixed theme and explain the
limitation; do not silently fall back to light.

The authenticated session must ultimately execute the selected package's
**start-hyprland**, not `Hyprland` directly. On NixOS use
`${config.programs.hyprland.package}/bin/start-hyprland`; on Arch verify the
package's `/usr/bin/start-hyprland`. UWSM may manage that launcher, for example
`uwsm start -e -D Hyprland -- /absolute/path/to/start-hyprland`. If using a desktop
entry, inspect its actual Exec chain; a session name alone is not proof. A seeding
wrapper named start-hyprland must exec the package path, not recurse into itself.
With UWSM, finalize its environment from the Lua startup event:

```lua
hl.on("hyprland.start", function () hl.exec_cmd("uwsm finalize") end)
```

Do not hide the direct-launch watchdog warning. A process named Hyprland is the
normal compositor child even under the correct launcher; check parent/launcher
processes, UWSM service commands and session logs together.

For the installed owner interface, import the reusable NixOS module alongside
the resident service (replace the source path and owner with the reviewed values):

```nix
(import (source + "/adapters/nixos/owner-setup.nix") {
  owner = "owner";
  graphical = true;
  useGhostty = true;
})
```

Set `services.controlstackAgent.mutableProviderSetup = true` and its pinned
`corePackage` and `package`. The module supplies the terminal, restricted owner
setup command, System Assistant menu entry and XDG autostart; it does not select
a desktop or greeter. The graphical session must actually run XDG autostart
(UWSM does this). For console-only deployments set `graphical = false`; tty1
opens local setup. If a custom session deliberately omits XDG autostart, arrange
one equivalent owner-session launch, avoiding duplicates. Do not grant the
resident service sudo. On Arch reuse the reviewed owner setup/menu/autostart
parts of `adapters/arch/target.py` or implement equivalent native configuration.

Before reboot inspect the generated Lua, executable launcher, selected greeter's
session entry, setup command/owner sudo rule and autostart integration. Keep
actual desktop behavior pending for first boot. After independent installed
login, check `hyprctl configerrors`, test a requested shortcut, confirm the Lua
file being loaded and the start-hyprland launch chain, and observe the Ratatui
setup inside the owner's terminal. Record evidence separately for Lua, session
launch, system/terminal appearance and assistant UI; boot success or gateway health passes none of them.
Existing installations need migration: preserve the old configuration, translate
all owner bindings to Lua, validate, and switch the selected session deliberately.
Changing repository instructions cannot repair an already installed machine.

References: [Hyprland configuration](https://wiki.hypr.land/Configuring/Start/),
[launching Hyprland](https://wiki.hypr.land/Getting-Started/Master-Tutorial/).

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
