# Qualification status

This is a development prototype. Validation recorded on 2026-10-06:

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
| BIOS/UEFI OpenClaw live ISO | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37540467951): direct USB boot, tty1 startup, offline gating |
| No-desktop UEFI installation and ZFS-root boot without USB | Passed on a disposable VM disk, with installed OpenClaw fixture response |
| Physical hardware, encrypted boot, desktop login, ZFS-root recovery | Not yet qualified |
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

The older lifecycle VM uses an ext4 root with ZFS file-backed vdevs. The new ISO
workflow independently installs onto a blank 48 GiB virtual disk and boots the
ZFS root with the USB detached. The NixOS adapter emits the narrow handoff;
verification checks a new boot ID, matching machine identity and the real writable
root dataset. The latest console-qualified ISO digest is
`96dd5422982a9c1b898ad04d6d0c18e7fb41468d9613b91884bf39a5914df8f4`, source
`918705b`. This newer run passed the complete interactive console installation,
guided shutdown, primary-console owner login, automatic setup and a visible
native OpenClaw TUI fixture reply. Its desktop preparation step failed before
disk erasure, so the overall workflow did not pass. Desktop and encryption
qualification remains in progress. Exact revisions and check lists are in
[validation.json](../evidence/validation.json).

A build, service template or health endpoint is not completed model authentication
or installed-system qualification.
Local cache attempts encountered HTTP/2 framing/resume errors; a retry using the
official cache over HTTP/1.1 made progress but npm/cache connections subsequently
reset or timed out. Pins, hashes and signature checks remain unchanged.
