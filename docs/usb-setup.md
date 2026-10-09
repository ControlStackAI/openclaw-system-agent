# NixOS USB setup (development image)

Use an image built from the current `images/nixos.lock.json`; there is no
published GitHub release download yet. See [image builds](image-builds.md) and
[qualification](qualification.md) for the build instructions, exact tested hashes
and limits. Older Actions artifacts are historical evidence; the first NixOS
image had a Wi-Fi defect and should not be used for new tests.

## What the owner does

Verify the image against its accompanying checksum. Copy its `.iso` onto an
existing Ventoy drive, or select it in your USB image writer; 16 GB or larger is
recommended. Writing an image directly erases that USB drive. Use a spare test
computer and a backed-up target disk while physical installation remains
unqualified; automated qualification uses virtual machines.

1. Start the computer from the USB in UEFI mode. The setup screen opens
   automatically. Choose a keyboard layout, then connect to Wi-Fi if Ethernet
   has not already connected.
2. Choose **Connect your AI account or change provider**. OpenClaw is already
   installed. For ChatGPT, enter the short device code at the address shown on
   another device; API keys use hidden input. Then choose
   **Talk to the assistant**.
3. Explain what this computer is for. The assistant's profile asks for relevant
   choices one at a time, including KDE Plasma, GNOME, Hyprland + Quickshell or no desktop; language,
   keyboard, time zone, computer name, account and encryption. Real-model
   interview quality still needs testing with an actual provider account.
4. Ask the assistant to proceed: it opens the local installation review with
   saved choices. Alternatively, press **Ctrl+D** to return to setup and choose
   installation review. It collects missing choices, prepares the selected system, and shows
   the disk and storage plan. The guided installer waits for the separate local disk
   confirmation before erasing anything. This version uses the whole selected disk and erases its data.
   Account passwords and the optional disk passphrase use hidden local prompts,
   never the chat.
5. After installation, choose shutdown, remove the USB, and start the computer.
   Unlock the disk if encryption was selected, then sign in to the local account.
   System Assistant opens automatically. The system checks that it really booted
   from the installed ZFS root. GNOME may offer a desktop tour; choose **Skip**
   to go straight to the assistant, then click the **System Assistant** window
   in the overview to continue.
6. Sign in to OpenClaw again on the installed computer. This creates persistent
   credentials there; USB credentials are deliberately not copied. The assistant
   retains the chosen OS settings and can continue helping with the computer.
   Later sessions and its workspace persist across restarts. On a desktop, open
   **System Assistant** from the application menu whenever needed.

The installed agent can inspect the system and propose changes. Maintenance that
needs elevated access uses the separate owner-operated approval mechanism;
automatic privileged administration is not enabled by signing in.

For missing adapters or airplane mode, see [network setup](networking.md).
It is safe to choose sign-in before connecting: return to setup and connect,
then retry sign-in.

## Implementation and limits

The live image opens the local setup screen on tty1. Other consoles remain
available. It offers network setup, official OpenClaw sign-in and conversation,
then a separate local installation review. The USB starts with a US keyboard;
choose Change keyboard layout before entering passwords if you use another
layout. The target console map is applied before account/encryption password
entry and included in early boot. The shared network/clock/ZFS checks
are consumed from the pinned agent-installer source; that repository is unchanged.

The experimental installer supports UEFI, a whole disk of at least 32 GiB, ZFS,
and no desktop, KDE Plasma, GNOME or Hyprland + Quickshell.
See the [qualification matrix](qualification.md) for the current image test scope. The console path was tested with 4 GiB
of RAM. Desktop preparation requires 8 GB of usable RAM in this development
image; a smaller machine is stopped before building or changing its disk. Optional
desktop packages are carried on the read-only USB image to avoid filling RAM
with their unpacked downloads. They do not start a desktop in the live session.
It builds the target before erasure, rejects
mounted/in-use disks, binds approval to the observed disk and boot, and requires
the owner to type the disk serial at the local screen. It does not preserve data
on that disk, resize partitions, configure dual boot or install in legacy BIOS
mode. Do not use it on valuable hardware before qualification is complete.

Installation creates separate system, home and agent-state datasets. It uses the
OpenZFS 2.2 compatibility feature set and never upgrades pool features.
Encryption is an explicit setup choice with hidden passphrase input. The initial
bootloader is systemd-boot on a 1 GiB FAT EFI partition. Kernel and released ZFS
remain locked to the project's reviewed inputs and compatibility guard.

The resident OpenClaw service starts on the installed system. The owner signs in
to the local account and System Assistant opens on the first console or graphical
login. On a desktop, reopen it from the System Assistant application-menu entry.
A fresh OpenClaw sign-in is required: live credentials, configuration,
workspace and conversations are not transferred. Only validated OS choices and
a narrow installed-boot record cross the boundary. The service checks the actual
root dataset, machine identity and new boot ID independently of model health.

This image opts into mutable private provider configuration for official
provider authentication; the Nix package and service remain declarative. The existing
resident module defaults to declarative configuration unless this option is set.
The assistant can inspect and edit its own state but has no sudo grant. Privileged
installation remains in the owner-operated local screen. Remote access and
unattended updates are off. Backups still need an independent destination.

The current INSTALL-RECOVERY image passed live BIOS/offline boot and UEFI Hyprland
installation, installed ZFS-root boot without the ISO, and desktop checks through
a second reboot. Replies used a local provider fixture. Other desktops and
encryption have earlier, separately scoped evidence. These VM tests do not qualify
real provider accounts, physical hardware, Secure Boot or installed-root recovery.
Separate owner feedback reports hardware boot and YubiKey sign-in, removal locking
and key unlock; see [qualification](qualification.md) for the exact scope.

## Installation started from the conversation

On newly built images, the live agent can call `system-agent install-status` to
read the root console's payload/capability check, then `system-agent request-install`
after saving the agreed supported choices. Ratatui opens installation review
automatically; the user does not have to navigate back through the menu. The local
screen still owns disk selection, exact erasure approval, key enrollment and
protected password input. Cancellation/failure/success is returned to the same
conversation, without restarting the gateway or copying credentials.

The bridge exists only while root live setup is running. Its socket is root-owned,
group-accessible only to the service account, and checks peer credentials. It
accepts typed choices, not disk paths, scripts, passwords or erasure approvals.
Requests are idempotent; an intentional retry uses `request-install --retry`.
Arbitrary workspace drafts are not an executable installation configuration.
Unsupported requirements must be explained before the owner approves the supported
plan. Older ISOs do not contain this bridge.

### Live system access and conversation-driven installation

The live service account has passwordless `sudo` and shares the host's devices
and mount namespace. OpenClaw can inspect disks, mount an additional USB, and
prepare an authorized recovery or installation without sending the owner to a
shell. `system-agent inspect` reports the image's access profile and a real
noninteractive root-command check. This broad access is intentional on the live
media; it is not copied into the installed resident service.

The gateway remains loopback/token authenticated, external chat channels are off,
and live credentials remain in private RAM. Full sudo grants actual root powers;
the exact-disk review is a required installer workflow, not a security boundary
against an agent choosing arbitrary root commands. The identity directs the agent
to use read-only mounts for inspection, preserve unrelated disks, and obtain a
concrete storage approval before destructive changes.

The agent calls `system-agent request-install` after saving your supported choices.
The primary console opens installation review automatically and returns to the
same conversation after cancellation, failure, or completion. The agent checks
`system-agent install-status` for the root installer's own payload/readiness view.

## Handling installation errors

The INSTALL-RECOVERY images distinguish preparation failures from final cleanup failures in
`system-agent install-status`. These changes are not present in the original
2026-10-08 SYSTEM-ACCESS ISOs.

- **Missing, unreadable or corrupt Arch payload:** state `blocked`, stage
  `payload-check`, and `disk_changes: none-this-attempt`. The message explains
  read-only boot-media recovery or image replacement and retains checksum checks.
- **Mistyped erasure confirmation:** stay in local review and choose Try again or
  Cancel. Retrying preserves the prepared plan and never treats the typo as approval.
- **Failed ZFS export:** state `needs-cleanup`, stage `pool-export`, with the pool,
  exit code and ZFS diagnostic. `disk_changes: system-written` explicitly records
  that installation already wrote the disk; `installed_boot_verified` stays false.
  The current root console refuses to reopen installation even with `--retry` or
  changed preferences. The assistant must inspect confirmed pool holders, including
  mounts retained by live-service namespaces, and preserve unrelated pools.

No service is automatically killed and no pool is force-exported. Unexpected errors
remain `failed` with disk changes marked unknown rather than falsely claiming an
untouched disk. This status belongs to the running console session; restarting it
is not proof that a failed cleanup has been resolved. Inspect actual pool and boot
state before taking further action. Long export diagnostics are bounded and marked
as truncated so the result remains deliverable to the conversation.
