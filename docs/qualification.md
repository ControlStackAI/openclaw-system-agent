# Qualification status

This is a development prototype. Validation recorded on 2026-10-07 UTC:

| Check | Result |
| --- | --- |
| Portable lifecycle, readiness, choices and approval unit tests | 31 passed |
| Pinned public installer contract check | Passed |
| NixOS module and VM-test derivation evaluation | Passed |
| Nix lifecycle package build and installed CLI entry points | Passed |
| Arch package shell syntax and file staging | Passed; not native makepkg/service qualification |
| Independent lifecycle/ZFS VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37503462931) |
| Real OpenClaw gateway/conversation/backup VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37522513941), using a local provider fixture |
| Owner profile loading, reboot persistence and native backup/restore | Passed in the OpenClaw fixture VM |
| Guided OS choices | Typed-choice handoff and questionnaire implemented; real-model interview quality unqualified |
| Real account login and model response | Not tested; no operator credentials used |
| BIOS/UEFI OpenClaw live ISO | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37553931672): direct USB boot, tty1 startup, offline gating |
| No-desktop UEFI installation and ZFS-root boot without USB | Passed on a disposable VM disk, with installed OpenClaw fixture response |
| Plasma and GNOME owner login, automatic assistant window and visible TUI reply | Passed with the local provider fixture |
| Encrypted ZFS-root boot and German keyboard | Passed in the Plasma VM |
| Physical hardware, Secure Boot and installed ZFS-root recovery | Not yet qualified |
| Provider setup | Official interactive wizard wrapped by local menu; native synthetic custom-provider flow tested; real account login untested |
| Boot-critical updates and pool feature upgrades | No executor |
| Local whole-disk installer | Implemented; interactive questionnaire, exact disk approval and guided shutdown passed in VM |

`core-vm` does not start OpenClaw. It tests lifecycle and the owner-run broker with
actual ZFS on guest-only file-backed vdevs. `lifecycle-vm` starts the pinned real
OpenClaw package but its model API is a deterministic local fixture, not a real
model. It checks identity loading, conversation persistence, health, backup and
restore separately. Neither test attaches host disks, homes or operator state.

The gateway VM tested OpenClaw 2026.9.5, Linux 7.2.9 and released OpenZFS 2.4.4.
It passed authenticated CLI health, loaded the resident identity into an actual
provider request, preserved the conversation across a guest reboot, created a
native verified backup and restored the workspace sentinel into a fresh directory.
The updated VM also verified private USER.md permissions, preserved an owner
preference across reboot, delivered it to a fresh session independently of old
conversation history, and restored it from the native backup. The model API was a deterministic fixture. Real subscription/API authentication,
an actual model response, and resuming a conversation from the restored archive
are not qualified. Snapshot execution is tested through the owner-run broker;
service-restart and scrub-start branches still need dedicated native tests.

The older lifecycle VM uses an ext4 root with ZFS file-backed vdevs. The
[full ISO workflow](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37553931672) independently installed onto blank 48 GiB virtual
disks and booted their ZFS roots with the USB detached. It passed all four cases:
BIOS/offline live boot, a 4 GiB no-desktop installation, an 8 GiB encrypted Plasma
installation with a German keyboard, and an 8 GiB GNOME installation. Each
installed case used the shipped questionnaire, separate exact disk approval,
guided shutdown, ordinary owner login and automatic setup entry point. Both
desktops and the primary console displayed a native OpenClaw TUI fixture reply
and returned to the menu with Ctrl+D. GNOME's first-login tour was dismissed and
the assistant window selected through normal input events.

The independent boot check verified a new boot ID, matching machine identity and
the actual writable ZFS root. Tests also checked that live credentials/configuration
were absent and that the installed owner choices reached a new provider request.
The model endpoint was a deterministic fixture throughout; this does not qualify
real account sign-in, real-model interview quality, or physical hardware.

The [tested development ISO](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37553931672/artifacts/11455361400) has SHA-256
`54d684eb2e8964e7237932b7327e6eb0de15ba92f1aba871784ad52bab054e4e` and was built from source
`cbacb60268ecc1f9cee5c39905592ea3afc6565e`. All four receipts identify those same ISO bytes.
Exact receipts and retained earlier lifecycle evidence are in
[validation.json](../evidence/validation.json). No-desktop and GNOME used
unencrypted roots; encrypted root was tested with Plasma. Encrypted replication,
installed-root rollback/recovery, real-provider interruption/reconnection, and a
friendly privileged-maintenance approval UI remain separate work. The installer
supports whole-disk UEFI installation only; BIOS installation and preserving an
existing partition layout are not implemented.

A build, service template or health endpoint is not completed model authentication
or installed-system qualification.
