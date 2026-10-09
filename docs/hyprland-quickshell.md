# Hyprland + Quickshell

Choose **Hyprland + Quickshell** during the NixOS USB installation review. The
live USB keeps its text setup screen; the selected desktop starts after installing,
removing the USB and signing into the owner account. The image carries its package
closure alongside Plasma and GNOME. Kernel, OpenZFS and OpenClaw pins are unchanged.

This profile uses pinned Hyprland 0.56.2 and Quickshell 0.3.1. The lightweight
greetd/gtkgreet graphical login starts an
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

- **Super + R** opens Applications.
- **Super + Space** opens System Assistant; **Super + A** opens audio selection.
- **Super + Enter** opens Ghostty; **Super + E** opens Files.
- **Super + 1–9 / 0** switches workspaces; add Shift to move the current window.
- **Super + C** closes the focused window; **Super + F12** locks the screen.
- **Super + arrows / H J K L** focuses a window; Shift moves it, Ctrl swaps it.
- **Super + Alt + Left/Right or H/L** moves a window between monitors.
- **Super + S** toggles the scratchpad; Shift sends a window there.
- **Super + Alt + C/X** opens Claude/Codex Desktop.
- **Super + N**, Shift+N and Ctrl+N dismiss, clear and restore notifications.
- Hold Super and drag with the left/right mouse button to move/resize a window.

Super is usually the key with the Windows logo. The panel offers mouse access
to applications and the assistant without requiring shortcut knowledge.

Ghostty uses its native `key=value` configuration; Hyprland uses Lua. The terminal
launcher, terminal application entries, customization editor and resident assistant
all use Ghostty in the Hyprland profile. Optional Nova applications and their
reserved bindings are listed in [the desktop choices](desktop-choices.md).
[Hypruse](hypruse.md) provides the resident agent full desktop control, with
stop/resume buttons in the monitor and Super+Shift+Backspace to stop immediately.

## Building custom components

The first login seeds owner-writable files, without overwriting existing files:

- `~/.config/quickshell/controlstack/shell.qml`: panel, launcher and controls.
- `~/.config/quickshell/controlstack/Theme.js` and the other QML files: colors, icons,
  controls, audio and networking components.
- `~/.config/ghostty/config`: terminal appearance and Ctrl+A leader shortcuts.
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

The resident assistant can draft QML in its workspace and use the Hypruse bridge
to launch owner processes and edit desktop files in the graphical session. This
is full owner-level desktop control. The separate resident service account keeps
its systemd restrictions; privileged system changes still require the maintenance
plan. Stop/resume controls for desktop access are described above.

## Qualification

The 32-pixel islands, Ghostty defaults and MCP integrations are included in the
current image and VM checks below. All 38 local and source-CI tests passed.

The [current image check](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37652171487) passed on source `ff6e287e34070ff2ae581f1676e25a29b10f28f3`.
It installed onto a disposable 48 GiB disk, booted its ZFS root without the USB,
logged in through SDDM, opened an application from the launcher and displayed an
OpenClaw TUI reply from a local fixture. It verified the monitor during an actual
service stop/start, the audio and Ethernet panels, the CLI/editor defaults,
lock/password unlock and customization retained after another reboot.

The [desktop interaction VM](https://github.com/ControlStackAI/openclaw-system-agent/actions/runs/37654485421) separately verified speaker
and microphone selection, mute/unmute, both coding CLIs, Neovim and both vendor
apps' first-run screens. See [qualification](qualification.md) for the image
checksum and limits. Real account login, physical GPU/audio/Wi-Fi and suspend/resume
remain unqualified. No operator credentials were used.

The desktop VM also verified real Hypruse typing, screenshots, clipboard,
workspace control and stop/resume, plus mcp-nixos store queries. The USB test
verified NixOS tools in the live agent and both MCP integrations after installing
Hyprland. See [MCP integration](installed-mcp.md) for their distinct lifecycles.
