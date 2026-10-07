# Hyprland + Quickshell

Choose **Hyprland + Quickshell** during the NixOS USB installation review. The
live USB keeps its text setup screen; the selected desktop starts after installing,
removing the USB and signing into the owner account. The image carries its package
closure alongside Plasma and GNOME. Kernel, OpenZFS and OpenClaw pins are unchanged.

This profile uses pinned Hyprland 0.56.2 and Quickshell 0.3.1. SDDM starts an
UWSM-managed session so the desktop, portals and user services share a proper
session lifecycle. System Assistant opens automatically at login.

## The starting desktop

Three compact, 32-pixel-high Quickshell islands sit at the top of the screen,
with unchanged text and icon sizes and 48 pixels reserved for the top bar. The left opens the
icon-based application launcher and switches workspaces. The center shows the
resident OpenClaw service status; click it for CPU, memory and restart details, or
use its conversation button to open System Assistant. The right holds the tray,
network, speaker, microphone, battery (on laptops), clock and quick settings.

Quick settings separates Audio, Network and System. Audio offers speaker and
microphone selection, volume and mute. Network shows wired and wireless connections
and masked Wi-Fi sign-in. System provides Bluetooth, brightness, resource usage,
keep-awake and desktop customization. Lock and confirmed sign-out remain available.
PipeWire owns audio and NetworkManager owns networking. Mako provides notifications;
Hyprlock locks after ten idle minutes and before suspend. Type your account password
and press Enter to unlock. See [development desktop](development-desktop.md) for
the included editors, coding agents and development tools.

- **Super + Space** opens Applications.
- **Super + A** opens System Assistant.
- **Super + Enter** opens a terminal; **Super + E** opens Files.
- **Super + 1–5** switches workspaces; add Shift to move the current window.
- **Super + Q** closes the focused window; **Super + L** locks the screen.
- Hold Super and drag with the left/right mouse button to move/resize a window.

Super is usually the key with the Windows logo. The panel offers mouse access
to applications and the assistant without requiring shortcut knowledge.

## Building custom components

The first login seeds owner-writable files, without overwriting existing files:

- `~/.config/quickshell/controlstack/shell.qml`: panel, launcher and controls.
- `~/.config/quickshell/controlstack/Theme.js` and the other QML files: colors, icons,
  controls, audio and networking components.
- `~/.config/kitty/kitty.conf`: terminal appearance.
- `~/.config/hypr/hyprland.lua`: compositor, keyboard and shortcuts.
- `~/.config/hypr/hyprlock.conf` and `hypridle.conf`: lock and idle settings.

**Quick settings → System → Customize** opens the QML source in Neovim. Quickshell reloads
saved changes automatically. These files persist on the home ZFS dataset; system
updates and later logins do not overwrite them. Read-only factory defaults remain
in `/etc/controlstack-agent/desktop-defaults`. Keep a copy before major edits;
a broken QML file may stop the panel, while Super + Enter and the other consoles
remain available for repair.

Quickshell supports further custom components such as trays, notification views,
media controls and lock-screen interfaces. They are not all implemented by this
starter shell. See the [official Quickshell guide](https://quickshell.org/docs/v0.3.0/guide/introduction/).
Use the pinned Hyprland Lua configuration and matching documentation rather than
older hyprlang examples. No private host configuration is shipped.

The resident assistant can explain or draft QML in its workspace. Its restricted
service account has no access to the owner's home and no automatic privilege to
apply desktop edits there. Installing this profile does not broaden those rights.

## Qualification

The newer 32-pixel island adjustment passed 33 unit tests, source CI, and a
local Quickshell text-fit geometry check. The image and native VM results below
predate that adjustment: attempts to dispatch fresh checks returned HTTP 500
from GitHub. The downloadable image still has 36-pixel islands.

The [current image check](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37588644780) passed on source `b2534eba90c4c7035b7d170d5a702605e1e5350c`.
It installed onto a disposable 48 GiB disk, booted its ZFS root without the USB,
logged in through SDDM, opened an application from the launcher and displayed an
OpenClaw TUI reply from a local fixture. It verified the monitor during an actual
service stop/start, the audio and Ethernet panels, the CLI/editor defaults,
lock/password unlock and customization retained after another reboot.

The [desktop interaction VM](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37589254877) separately verified speaker
and microphone selection, mute/unmute, both coding CLIs, Neovim and both vendor
apps' first-run screens. See [qualification](qualification.md) for the image
checksum and limits. Real account login, physical GPU/audio/Wi-Fi and suspend/resume
remain unqualified. No operator credentials were used.
