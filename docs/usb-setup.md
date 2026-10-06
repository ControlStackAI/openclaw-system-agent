# NixOS USB setup (under qualification)

The live image opens the local setup screen on tty1. Other consoles remain
available. It offers network setup, official OpenClaw sign-in and conversation,
then a separate local installation review. The USB starts with a US keyboard;
choose Change keyboard layout before entering passwords if you use another
layout. The target console map is applied before account/encryption password
entry and included in early boot. The shared network/clock/ZFS checks
are consumed from the pinned agent-installer source; that repository is unchanged.

The experimental installer supports UEFI, a whole disk of at least 32 GiB, ZFS,
and no desktop, KDE Plasma or GNOME. The console path was tested with 4 GiB
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

This image opts into mutable private provider configuration for the official
onboarding wizard; the Nix package and service remain declarative. The existing
resident module defaults to declarative configuration unless this option is set.
The assistant can inspect and edit its own state but has no sudo grant. Privileged
installation remains in the owner-operated local screen. Remote access and
unattended updates are off. Backups still need an independent destination.

Qualification is in progress. Source/guard tests and Nix evaluation do not prove
USB boot, installation, encryption, desktop startup or actual provider sign-in.
The workflow builds the real ISO, boots it as a USB in BIOS and UEFI VMs, checks
offline gating, installs onto a disposable disk and boots that disk without the
ISO. Its model endpoint is a non-secret fixture, never an operator account.
