# Qualification status

This is a development prototype. Validation recorded on 2026-10-06:

| Check | Result |
| --- | --- |
| Portable lifecycle, readiness and approval unit tests | 22 passed |
| Pinned public installer contract check | Passed |
| NixOS module and VM-test derivation evaluation | Passed |
| Nix lifecycle package build and installed CLI entry points | Passed |
| Arch package shell syntax and file staging | Passed; not native makepkg/service qualification |
| Independent lifecycle/ZFS VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37503462931) |
| Real OpenClaw gateway/conversation/backup VM | [Passed](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37522513941), using a local provider fixture |
| Owner profile loading, reboot persistence and native backup/restore | Passed in the OpenClaw fixture VM |
| Real-model guided OS choices and desktop installation | Not qualified; instructions/template only, no desktop executor |
| Real account login and model response | Not tested; no operator credentials used |
| BIOS/UEFI OpenClaw live ISO | Not built or qualified |
| Physical disk installation, ZFS-root boot/recovery | Not implemented or qualified |
| Novice provider setup UI, especially declarative NixOS | Incomplete |
| Boot-critical updates, disk erasure, pool feature upgrades | No executor |

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

The guest root is an ext4 test disk with ZFS pools on guest-only files. This is not
a ZFS-root installation or recovery test. Boot verification correctly refuses to
qualify an installation without a matching producer handoff. The producer contract
is proposed and not yet emitted by the installer. Exact tested revisions and
check lists are in [validation.json](../evidence/validation.json).

A build, service template or health endpoint is not completed model authentication
or installed-system qualification.
Local cache attempts encountered HTTP/2 framing/resume errors; a retry using the
official cache over HTTP/1.1 made progress but npm/cache connections subsequently
reset or timed out. Pins, hashes and signature checks remain unchanged.
