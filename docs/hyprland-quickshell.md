# Hyprland + Quickshell

Choose **Hyprland + Quickshell** during the NixOS USB installation review. The
live USB keeps its text setup screen; the selected desktop starts after installing,
removing the USB and signing into the owner account. The image carries its package
closure alongside Plasma and GNOME. Kernel, OpenZFS and OpenClaw pins are unchanged.

This profile uses pinned Hyprland 0.56.2 and Quickshell 0.3.1. SDDM starts an
UWSM-managed session so the desktop, portals and user services share a proper
session lifecycle. System Assistant opens automatically at login.

## The starting desktop

The Quickshell panel provides Applications, five workspace buttons, Assistant,
Controls and a clock. The searchable application launcher opens installed apps.
Controls opens network setup, sound, files, the shell editor, screen locking and
a confirmed sign-out. PipeWire supplies audio, NetworkManager supplies networking,
and GTK/Hyprland portals provide application integration. Mako supplies basic
notifications and Hyprlock supplies locking; these are not custom Quickshell UIs.
Automatic locking starts after ten idle minutes, with locking before suspend.

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
- `~/.config/quickshell/controlstack/ShellButton.qml`: reusable button style.
- `~/.config/hypr/hyprland.lua`: compositor, keyboard and shortcuts.
- `~/.config/hypr/hyprlock.conf` and `hypridle.conf`: lock and idle settings.

**Controls → Customize this desktop** opens the QML source. Quickshell reloads
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

The new profile is awaiting its USB installation VM qualification. The earlier
published four-case image did not contain this desktop; use the artifact and
checksum recorded in the current qualification report once the new run passes.
Real GPU hardware, suspend/resume and a real AI provider remain unqualified.
