# Qualification status

This is a development prototype. Status at initial publication on 2026-10-06:

| Check | Result |
| --- | --- |
| Portable lifecycle, readiness and approval unit tests | 22 passed |
| Pinned public installer contract check | Passed |
| NixOS module and VM-test derivation evaluation | Passed |
| Nix lifecycle package build and installed CLI entry points | Passed |
| Arch package shell syntax and file staging | Passed; not native makepkg/service qualification |
| Independent lifecycle/ZFS VM | Implemented; awaiting completed run |
| Real OpenClaw gateway/conversation/backup VM | Implemented; local dependency acquisition blocked by network resets/timeouts; hosted run pending |
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

A build, service template or health endpoint is not a completed authentication
or installed-system qualification. Pending tests must not be reported as passes.
Local cache attempts encountered HTTP/2 framing/resume errors; a retry using the
official cache over HTTP/1.1 made progress but npm/cache connections subsequently
reset or timed out. Pins, hashes and signature checks remain unchanged.
