# NixOS queries and persistent desktop MCP tools

| Environment | mcp-nixos | Hypruse |
| --- | --- | --- |
| NixOS live USB installer | Enabled for installation planning | Not enabled |
| Installed NixOS without a desktop | Enabled | Not enabled |
| Installed NixOS with GNOME or Plasma | Enabled | Not enabled |
| Installed NixOS with Hyprland | Enabled | Enabled during the owner's graphical session |

The live NixOS agent uses mcp-nixos to look up packages, options and documentation
while planning the target system. Hypruse is carried in the read-only USB store
for installation but is not registered or started in the live environment.
Live agent state remains private RAM state; installation creates fresh persistent
configuration rather than copying live credentials.

[mcp-nixos](https://github.com/utensils/mcp-nixos) is version 3.0.1 from our
pinned nixpkgs revision `151fa4e8ddfdd8dd25d945ad94ed54a13de9f6e4`.
That package pins upstream `v3.0.1` with source hash
`sha256-S6elg+nneCdUwpG6Y9ABMr/bbRfzCvls0ba2Vva22Lk=`. It runs directly
from the immutable Nix store using stdio. No `uvx` or unpinned `nix run` is used
at runtime, and no network listener is opened.

OpenClaw registers it as `mcp.servers.nixos`, with `nixos__*` permitted by tool
policy. Its query tools cover package and configuration information, documentation,
versions, and Nix store/flake inspection. Remote searches need internet access;
they do not install packages, authorize a rebuild, or prove compatibility with
the machine's pinned kernel/OpenZFS/nixpkgs.

The root-owned `/etc/controlstack-agent/installed-mcp.json` contract determines
which system integrations are active. Official onboarding and subsequent resident
service starts merge this contract into mutable OpenClaw config without replacing
provider setup, credentials, unrelated MCP definitions, sessions, or workspace
history. Disabling a managed integration removes its definition and tool grant
on the next service start. Declarative OpenClaw instances use the same definitions
directly in their generated config.

Set `services.controlstackAgent.nixosMcp.enable = false` to disable NixOS queries.
Set `services.controlstackAgent.desktopOwner = null` to disable Hypruse. The
Hyprland monitor additionally offers a session-local stop/resume control.

The VM check probes both definitions through the official OpenClaw CLI. It also
checks mcp-nixos tool discovery and reads a public store fixture through its real
stdio server, without requiring an external search service. Search-service
availability and authenticated model use are separate qualification claims.
