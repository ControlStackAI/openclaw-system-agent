# Qualification status

## Locked builds and Wi-Fi correction — 2026-10-08 UTC

The corrected NixOS ISO is **31073bdedfb8b7d4e1f3f1b1f6084ee5e30661688d17d389032fdd01b7171129**
(SHA256, 7,427,911,680 bytes). Build with `images/nixos.lock.json`.
The first Ventoy image (`a6d3dccf…449692a`) incorrectly disabled NetworkManager's
Wi-Fi backend. Both live and installed configurations now enable the
DBus-controlled supplicant. See [networking](networking.md).

| Current check | Result |
| --- | --- |
| Unit tests | 55 passed |
| NixOS BIOS live boot | Passed, including offline sign-in followed by network setup |
| NixOS UEFI Hyprland installation | Passed on a blank 48 GiB VM disk with 8 GiB RAM |
| Installed ZFS-root boot without USB | Passed; independent boot verification and saved intended use |
| Live and installed Wi-Fi backend | Available and starts successfully |
| Simulated WPA2 Wi-Fi | Discovery, authentication, radio-off and reconnection passed on Linux 7.2.9 |
| Hyprland desktop, resident monitor, settings after another reboot | Passed |
| Resident NixOS and Hypruse MCPs | Passed with the local provider fixture |
| Arch preview BIOS and UEFI | Passed: console startup, RAM permissions, gateway health and offline gating |
| Physical AX211 Wi-Fi correction | Awaiting hardware retest |
| Real account/YubiKey sign-in | Not tested |
| Independent byte-identical rebuilding | Not qualified |
| Arch disk installation and desktop deployment | Not implemented |

The Arch preview ISO SHA256 is
`95500738daf6539486cc269080a35b33bad08c557d33b2cb4f015b7a96a82df8`.
Build with `images/arch.lock.json`. Its UEFI layout now uses a non-overlapping
GPT with an appended EFI System Partition. It is a live preview only.

[Machine-readable receipts](../evidence/image-builds-2026-10-08.json) bind these
checks to exact source manifests, locks and ISO hashes. Build receipts keep their
initial unqualified fields; separate test results establish the scopes above.
The current full install test used unencrypted Hyprland and a US keyboard.
Other desktops and encryption retain only the historical qualification below.
No host disks, homes, provider credentials or production services entered tests.

## Historical qualification

| Check | Result |
| --- | --- |
| Portable lifecycle, readiness, choices and approval unit tests | 33 passed |
| Pinned public installer contract check | Passed |
| NixOS module and VM-test derivation evaluation | Passed |
| Nix lifecycle package build and installed CLI entry points | Passed |
| Arch package shell syntax and file staging | Passed; not native makepkg/service qualification |
| Independent lifecycle/ZFS VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37503462931) |
| Real OpenClaw gateway/conversation/backup VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37522513941), using a local provider fixture |
| Owner profile loading, reboot persistence and native backup/restore | Passed in the OpenClaw fixture VM |
| Guided OS choices | Typed-choice handoff and questionnaire implemented; real-model interview quality unqualified |
| Real account login and model response | Not tested; no operator credentials used |
| BIOS/UEFI OpenClaw live ISO | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37585485964): direct USB boot, tty1 startup, offline gating |
| No-desktop UEFI installation and ZFS-root boot without USB | Passed on a disposable VM disk, with installed OpenClaw fixture response |
| Plasma and GNOME owner login, automatic assistant window and visible TUI reply | Passed with the local provider fixture |
| Hyprland + Quickshell login, panel, launcher and visible assistant reply | Passed with the local provider fixture |
| Hyprland lock/unlock and customized QML retained after another reboot | Passed in VM |
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
[full ISO workflow](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37585485964) independently installed onto blank 48 GiB virtual
disks and booted their ZFS roots with the USB detached. It passed all five cases:
BIOS/offline live boot, a 4 GiB no-desktop installation, an 8 GiB encrypted Plasma
installation with a German keyboard, an 8 GiB GNOME installation, and an 8 GiB
Hyprland + Quickshell installation. Each
installed case used the shipped questionnaire, separate exact disk approval,
guided shutdown, ordinary owner login and automatic setup entry point. All three
desktops and the primary console displayed a native OpenClaw TUI fixture reply
and returned to the menu with Ctrl+D. GNOME's first-login tour was dismissed and
the assistant window selected through normal input events.

The independent boot check verified a new boot ID, matching machine identity and
the actual writable ZFS root. Tests also checked that live credentials/configuration
were absent and that the installed owner choices reached a new provider request.
The model endpoint was a deterministic fixture throughout; this does not qualify
real account sign-in, real-model interview quality, or physical hardware.

The [current development ISO](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487/artifacts/11497253654) has SHA-256
`a6d3dccfb490ea0d7d72610072639723cd69e2af42f7773a044662dab449692a` and was built from `ff6e287e34070ff2ae581f1676e25a29b10f28f3`.
Its [Hyprland USB check](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487) passed the complete installation, disk boot,
resident fixture conversation, monitor, panels, launcher, lock and persistence path.
The five-case results above belong to the preceding build `a4441724d56267eaf48d1bd568d672d4381dcf96`;
those other desktop profiles have not been rerun against the current ISO bytes.

The [desktop interaction VM](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37654485421) passed on
`6b5a5008d04426e67c6807f709a384305be097b2`. It switched synthetic speaker and microphone devices
through the visible UI and verified PipeWire defaults, tested microphone mute and
unmute, checked Neovim and both CLIs with Codex helpers, and rendered the official
Codex sign-in and Claude for Linux welcome screens. It rejected QML/icon errors
and C-library/graphics-driver version mismatches. This does not test authenticated
vendor sessions, physical audio, Wi-Fi association, Bluetooth or Claude Cowork.
The desktop VM and current image have identical runtime and desktop sources;
the later test revision corrects detection of the stopped Hypruse service.

The image exposes mcp-nixos during live setup and retains it after installation.
Hypruse is absent from the live tool catalog and present after the owner logs into
installed Hyprland. The desktop VM probes both servers with the official CLI,
queries a public Nix store fixture, and exercises actual Hypruse desktop input,
screenshot, clipboard, workspace switching and owner stop/resume. This does not
qualify autonomous tool selection by an authenticated model.

Exact scoped receipts and retained earlier evidence are in
[validation.json](../evidence/validation.json). Encrypted replication,
installed-root recovery and real-provider interruption/reconnection remain separate
work. The installer supports whole-disk UEFI installation; preserving partitions,
dual boot and BIOS installation are not implemented.

A build, service template or health endpoint is not completed model authentication
or installed-system qualification.
