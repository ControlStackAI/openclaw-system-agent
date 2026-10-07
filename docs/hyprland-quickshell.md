# Hyprland + Quickshell

Choose **Hyprland + Quickshell** during the NixOS USB installation review. The
live USB keeps its text setup screen; the selected desktop starts after installing,
removing the USB and signing into the owner account. The image carries its package
closure alongside Plasma and GNOME. Kernel, OpenZFS and OpenClaw pins are unchanged.

This profile uses pinned Hyprland 0.56.2 and Quickshell 0.3.1. SDDM starts an
UWSM-managed session so the desktop, portals and user services share a proper
session lifecycle. System Assistant opens automatically at login.

## The starting desktop

Three compact Quickshell islands sit at the top of the screen. The left opens the
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

The earlier starter desktop [five-case USB workflow](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37576857541) passed on source
`982254d06685519c7377b6bd9d3586c3f2aca8f1`. The Hyprland case installed onto a disposable 48 GiB disk,
booted without the USB, logged in through SDDM, displayed the Quickshell panel and
launcher, opened Mousepad through it, and displayed a native OpenClaw TUI reply from a local provider fixture.
It checked active graphical session services, no Hyprland configuration errors,
owner write access to the shell, screen lock/password unlock, and preservation of
an owner QML change across another reboot and graphical login.

See [qualification](qualification.md) for the image download and SHA-256.
Real GPU hardware, suspend/resume and a real AI provider remain unqualified.
The fixture response proves the local interface path, not actual model access.

The redesigned desktop and development applications are being qualified separately;
this earlier result does not qualify those additions.
