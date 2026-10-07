# OpenClaw desktop control on Hyprland

Choosing Hyprland includes [Hypruse](https://github.com/IlyasKhallouki/hypruse),
pinned at `253f6892bf0ba738b60046e64d0442fa48c454fc` (0.11.0, MIT).
The installation review explicitly describes full desktop access. Once the owner
logs in, OpenClaw can inspect and arrange windows/workspaces, launch applications,
capture the screen, use the mouse/keyboard, and read/write the clipboard.

Hypruse is registered only for an installed Hyprland owner.
[mcp-nixos](installed-mcp.md) is enabled in the NixOS live installer and all
installed NixOS profiles. The USB carries package closures for installation.

The installed OpenClaw 2026.9.5 runtime uses its native `mcp.servers.hypruse`
configuration, with `hypruse__*` in its tool policy. Official onboarding and service startup reapply
this integration alongside the local system-agent policy. No mcporter shim or
unversioned uvx download is required. Provider credentials are still entered by
the new owner; no build credentials are copied.

## Session and access

A user service runs the pinned server inside the selected owner's graphical
session, inheriting the current Wayland, Hyprland and session-bus environment.
A local Unix socket bridges OpenClaw's stdio connection to that service. The
socket belongs to the owner and a dedicated desktop group; the bridge additionally
checks peer UIDs. Only the owner and resident service account can connect. There
is no TCP listener and no root desktop process. The gateway retains its separate
systemd restrictions. Desktop control can act as the owner (including launching
owner processes); it is deliberately powerful and not a sandbox for the owner home.

The center island shows whether desktop control is enabled. Clicking its mouse
icon or pressing **Super+Shift+Backspace** stops the service and its connected
servers. The OpenClaw monitor has **Stop desktop access** and **Resume** buttons.
Stopping the bridge cuts off desktop access, while the resident system agent
continues to run. Logging out stops the bridge; a new login starts it with the
new session environment. Pausing is session-local, not a persistent disable.
To disable it declaratively, set `services.controlstackAgent.desktopOwner = null`.

Full control is the requested default, not observation-only mode. Upstream's
normal authentication-dialog guard remains: authentication input requires an
explicit `allow_auth` request. Upstream redacted action journaling and visual
marking are enabled. Journal and screenshot caches stay in the owner's standard
state/runtime directories. No screen images are stored in the bridge or logs.
Native Codex MCP approval mode is `approve`; other OpenClaw session/provider
policies may independently restrict tools. Full access does not authorize work
unrelated to the owner's request.

## Lua and verification limits

Hyprland uses Lua, while Ghostty uses its native key=value format. Hypruse can
read Lua-configured bindings, but cannot execute Lua closures via `use_bind`.
The agent must use native desktop/window/launch/input tools instead; synthetic
keyboard events cannot trigger compositor shortcuts. This upstream limitation
does not prevent direct window, pointer, keyboard or application control.

The Nix package passed 656 upstream tests, with four upstream skips and 15
exclusions (13 require a compositor; two assume a checkout-relative skill path).
The installed skill file is checked separately. Local tests cover peer rejection,
stdio forwarding, preservation of unexpected socket-path files, and restoration
of MCP registration after onboarding. The desktop VM test exercises native
OpenClaw discovery plus actual MCP desktop, typing, screenshot, clipboard,
workspace, and stop/resume operations. Its result must be recorded separately;
implementation and test definitions alone do not qualify the installed image.

References: [OpenClaw 2026.9.5 MCP configuration](https://github.com/openclaw/openclaw/blob/v2026.9.5/docs/tools/mcp.md),
[tool policy](https://github.com/openclaw/openclaw/blob/v2026.9.5/docs/gateway/config-tools/tool-policy.md).
