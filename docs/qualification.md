# Qualification status

## Live-console text size — 2026-10-08 UTC

The live-image configuration for both distributions includes Small (14),
Standard (16), Large (20), and Extra large (24) console fonts in Ratatui. Standard is the initial
setting. A 15-second preview restores the previous font unless confirmed;
confirmed choices survive reopening setup during the same live boot.

All 69 Python tests and 3 Rust tests pass. The console VM checks every font,
QR decoding or its complete-code fallback, timeout, Escape, abruptly closing the
frontend, and reloading the saved preference. The exact rebuilt NixOS image also
passed BIOS live boot, font changes through the shipped setup menu, and the
offline sign-in followed by network setup path.

| Text-size image | SHA-256 | Bytes |
| --- | --- | ---: |
| nixos | `61e3bfbc7f37c44cbc441417539e928109475f8c76b4a0eb87668462bc09a26a` | 7,427,911,680 |

The Arch image definitions include the same packaged console component, but its
rebuild stopped at the native package transaction’s free-space check. No new
Arch ISO is released or qualified by this change.

OpenClaw and kernel/ZFS pins are unchanged. Full disk installation was not
repeated for this live-console change; earlier installation results remain bound
to their earlier artifact hashes. Physical display compatibility, phone-camera
scanning and real provider/model access are not qualified by these VM checks.
The new NixOS image remains local while Ventoy is disconnected.

[Exact receipts](../evidence/live-console-text-size-2026-10-08.json) record the
source and artifact hashes and tested scope.

## Ratatui phone QR update — 2026-10-08 UTC

The ChatGPT connection screen now shows a QR below the public verification URL,
`https://auth.openai.com/codex/device`. The QR contains only that address; the
owner still enters the displayed pairing code. Small consoles retain the address
and code without displaying a cropped QR.

All 65 Python tests and 3 Rust tests pass. The console VM independently decodes
the rendered QR from its Linux-console screenshot to the exact verification URL,
and checks navigation, cancellation, protected input, review and terminal exit.
Both rebuilt images passed fresh BIOS live startup and offline-network checks.

| QR image | SHA-256 | Bytes |
| --- | --- | ---: |
| arch | `0bf34c3a7a183109e190518ef672e272369bee6f54a4b3a1bfb2ee5f244b1eca` | 7,208,900,608 |
| nixos | `05fe5215365a259f74362b67354c218fd3e64cc8256bd416e6f70c5199a1c9cc` | 7,427,911,680 |

OpenClaw versions and kernel/ZFS pins are unchanged. Full disk installation was
not repeated for this renderer-only update: the UEFI installation evidence below
belongs to the previous image hashes. Physical phone-camera scanning and real
provider/model access remain unqualified by these automated tests. Anthropic has
no equivalent short device-code method in either pinned runtime; its other
methods remain individually unqualified.

[QR update receipts](../evidence/ratatui-qr-images-2026-10-08.json) record the exact
artifacts and tested scope. These images are local; Ventoy was disconnected when
the update completed, so they have not been copied to it.

## Ratatui Arch and NixOS images — 2026-10-08 UTC

Both images now include the themed Ratatui setup and provider interface. NixOS
keeps OpenClaw 2026.9.5; Arch uses 2026.9.8. All 65 Python tests and the Rust
renderer test pass. The console VM verifies rendering, device-code display,
protected input, cancellation, disk review and terminal exit. The actual pinned
provider orchestration and private credential stores pass API-key and synthetic
device-code tests for both runtimes in an empty network namespace. The upstream
short-URL, polling and token-exchange tests also pass. Real accounts were not used.

| Final image | SHA-256 | Bytes |
| --- | --- | ---: |
| Arch | `0e925ac4fb83f233a59a99bea764b5dfe61f2d8dc51ccbc9c8d59f4fde3bfed7` | 7,208,871,936 |
| NixOS | `47473a8e729b23a2104a7f3105baf32204503c0e3f802fe2252ad983fe9b01b0` | 7,427,911,680 |

Both exact images passed fresh UEFI installation through the shipped Ratatui
interview and exact-disk approval, using disposable 48 GiB VM disks. Arch used
4 GiB RAM and NixOS used 8 GiB. Both booted their ZFS roots without the ISO,
accepted ordinary owner login, retained the chosen assistant name, opened the
resident Ratatui interface, and displayed a native OpenClaw fixture conversation.
The three desktop islands, launcher opening an application, monitor stop/start,
audio/network panels, development CLIs, Neovim default, lock/unlock and saved
customization after another reboot passed. Installed Hypruse was discovered;
NixOS also retained mcp-nixos. Live credentials were excluded and independent
installed-boot verification passed.

Both images additionally passed BIOS live boot and the offline sign-in followed
by missing-adapter network-setup path. Installation still requires UEFI.
A development installation caught naming before identity creation; the ordering
was fixed, regression-tested and both images rebuilt before these final tests.
No guest patches were applied during the final runs.

These final full-image profiles use unencrypted ZFS, Hyprland and a US keyboard.
Other desktops and encryption retain only their earlier separate qualification.
Physical hardware, real provider login/model access, YubiKey, Secure Boot,
installed-root recovery and independent byte-identical rebuilding remain unqualified.
Other provider methods are individually unqualified.
[Exact receipts](../evidence/ratatui-images-2026-10-08.json) bind these checks to the
artifact hashes and source manifests. Build receipts retain their initial
unqualified fields; separate final test results establish the tested scope.

## Earlier Arch installation and focused account connection — 2026-10-08 UTC

The native Arch installer and Hyprland target payload are implemented, with
OpenClaw 2026.9.8 and its matching Codex provider runtime preloaded. NixOS keeps
OpenClaw 2026.9.5. The normal account menu invokes focused official provider
authentication; ChatGPT uses device codes. Synthetic tests exercise the actual
shipped device-code module in both releases, but do not qualify a real account.

All 61 Python tests pass. The shared NixOS desktop VM regression passes after the
asset extraction and runtime change. The final Arch ISO is
`42d7119c6a88de0deb29199104dcdd111656df470a46430fabc69542c16cea23`
(7,208,318,976 bytes), built from `images/arch.lock.json`.

Its fresh UEFI Hyprland installation passed on a disposable 48 GiB disk with
4 GiB RAM: ZFS-root boot without USB, ordinary owner login, automatic assistant
window, launcher opening an application, three Quickshell islands, resident
monitor stop/start, audio/network panels, development CLIs and Neovim default,
Hypruse discovery through OpenClaw Tool Search and a real desktop snapshot,
visible fixture conversation, lock/unlock, and customization after another boot.
Live credentials were excluded and installed boot verification ran independently.

The same Arch ISO also passed encrypted ZFS-root installation, boot unlock and
console assistant conversation in a separate 4 GiB VM with a US keyboard.
The desktop and encryption results belong to separate test profiles.

The refreshed NixOS ISO is
`e6217fb9858a62a62462a5d14597baf6978f357d605eab339688f51b9c7fc880`
(7,427,911,680 bytes), built from `images/nixos.lock.json`. Its full UEFI Hyprland
installation passed on a disposable 48 GiB disk with 8 GiB RAM, including
disk boot without the ISO, owner login, automatic assistant, visible fixture
conversation, both resident MCPs, desktop panels and launcher, lock/unlock,
and customization after another reboot. Both live and installed systems have
a working Wi-Fi backend; physical Wi-Fi association still needs a hardware test.

These are VM results with a synthetic provider, not real provider authentication
or physical-hardware qualification. Development failures are retained in local
logs: an early Arch attempt stopped before erasure on a payload precheck during
host memory pressure; later checks found and fixed SDDM profile startup and
public-directory permissions. Final clean runs did not patch the guests.
Independent byte-identical rebuilding and installed-root recovery remain unqualified.

Both final ISOs also passed direct BIOS live boot and the offline sign-in followed
by network-setup path with no NIC attached. The interface explains a missing
adapter instead of presenting loopback as a connection. Installation requires UEFI.
[Exact build and test receipts](../evidence/arch-installer-device-code-2026-10-08.json)
bind all five VM runs to the hashes above. Build receipts retain their original
unqualified fields; the separate test records establish each tested scope.

## Historical locked builds and Wi-Fi correction — 2026-10-08 UTC

The corrected NixOS ISO is **31073bdedfb8b7d4e1f3f1b1f6084ee5e30661688d17d389032fdd01b7171129**
(SHA256, 7,427,911,680 bytes). Its historical lock is identified by the evidence receipt below.
The first Ventoy image (`a6d3dccf…449692a`) incorrectly disabled NetworkManager's
Wi-Fi backend. Both live and installed configurations now enable the
DBus-controlled supplicant. See [networking](networking.md).

| Historical check | Result |
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
Its historical lock is identified by the evidence receipt below. Its UEFI layout now uses a non-overlapping
GPT with an appended EFI System Partition. It is a live preview only.

[Machine-readable receipts](../evidence/image-builds-2026-10-08.json) bind these
checks to exact source manifests, locks and ISO hashes. Build receipts keep their
initial unqualified fields; separate test results establish the scopes above.
That full install test used unencrypted Hyprland and a US keyboard.
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

The [earlier development ISO](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487/artifacts/11497253654) has SHA-256
`a6d3dccfb490ea0d7d72610072639723cd69e2af42f7773a044662dab449692a` and was built from `ff6e287e34070ff2ae581f1676e25a29b10f28f3`.
Its [Hyprland USB check](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487) passed the complete installation, disk boot,
resident fixture conversation, monitor, panels, launcher, lock and persistence path.
The five-case results above belong to the preceding build `a4441724d56267eaf48d1bd568d672d4381dcf96`;
those other desktop profiles were not rerun against those ISO bytes.

The [desktop interaction VM](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37654485421) passed on
`6b5a5008d04426e67c6807f709a384305be097b2`. It switched synthetic speaker and microphone devices
through the visible UI and verified PipeWire defaults, tested microphone mute and
unmute, checked Neovim and both CLIs with Codex helpers, and rendered the official
Codex sign-in and Claude for Linux welcome screens. It rejected QML/icon errors
and C-library/graphics-driver version mismatches. This does not test authenticated
vendor sessions, physical audio, Wi-Fi association, Bluetooth or Claude Cowork.
That desktop VM and image had identical runtime and desktop sources;
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
