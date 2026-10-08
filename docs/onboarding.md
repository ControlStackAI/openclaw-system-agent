# Friendly first-run flow

The intended flow asks one concrete question at a time and does the inspection on
the device. The owner should never need to copy inventories into another chat.

1. Explain the local assistant's role: “I can help you look after this computer.”
2. Detect Ethernet. If unavailable, ask “Would you like to connect to Wi-Fi?” and
   use the image's NetworkManager flow. Keep a troubleshooting shell available.
3. Check internet, then secure connections and synchronized time. A disconnect
   after a menu selection must return to this same flow and block sign-in.
4. Ask for the desired provider route. Use a supported official browser/device
   flow or masked interactive secret input. Never reuse the installer’s credentials.
5. Verify a real provider response, then explain the concrete access plan. Reading
   system status is the default. Enabling more access is a separate owner choice.
6. Open the local conversation and retain a clear reopen command.

## Learn the intended system

Provider onboarding and OS choices are separate steps. The agent first inspects
where it is running and establishes the current purpose. Live media can be used
to install or recover; an installed computer normally needs its current task
continued, not another setup interview. Unknown environment facts remain unknown
until inspected. The running distribution is not automatically the desired one.

For a new setup, ask only the next unresolved question. Reuse answers already
given, allow the owner to change them, and explain the effect of each choice.
For example, after learning the intended use:

> Would you like a graphical desktop, no desktop, or help choosing?

If a desktop is wanted, explain a small set of choices verified against the
pinned target adapter, then ask for one choice. The NixOS adapter offers GNOME, KDE Plasma and Hyprland + Quickshell. Arch offers Hyprland + Quickshell. Xfce is not an implemented option. A
headless choice skips the desktop questions. It preserves a local console and
does not silently enable SSH or any other remote service.

The following topics are a guide for the agent, not a form to show all at once:

| Topic | Decision to establish |
| --- | --- |
| Purpose and distribution | Everyday use, shared machine, development, server or another use; retain an existing distribution or choose a supported target |
| Desktop and accessibility | Desktop or no desktop; environment only if wanted; assistive input/display needs |
| Regional settings | Language, keyboard and time zone; confirm detected suggestions |
| Identity and sign-in | Computer name, local accounts and sign-in preferences; credentials through protected input only |
| Connectivity | Ethernet/Wi-Fi needs; advanced addressing only when needed |
| Storage | Data and other OS installations to preserve; concrete disk/dataset plan; ZFS remains the project requirement |
| Encryption | Unlock method and safe recovery-key custody, without recording secrets in conversation |
| Recovery | Portable snapshots, receiving-system compatibility, independent backup destination and retention |
| Maintenance | Update/restart timing; complete distro-supported updates and the released ZFS compatibility guard |
| Power and access | Sleep behavior, whether remote access is wanted, and its separate privilege/security plan |
| Applications | What the owner needs to do; recommend supported applications once the target and needs are known |

Offer sensible defaults and “help me choose.” Keep current settings during
maintenance unless the requested change requires otherwise. Do not require a
novice to choose partition names, kernel package names or bootloader internals.
Do not equate “set it up” or a saved preference with approval to erase a disk.
Before applying changes, summarize the setup and show the concrete privilege,
storage, recovery and verification plan. Material preference changes require a
revised plan; completed operations require fresh observed evidence.

## Remember decisions without confusing them with facts

The shipped USER.md template keeps non-secret intentions in the private OpenClaw
workspace, following the official [workspace convention](https://docs.openclaw.ai/concepts/agent-workspace).
Decisions carry chosen/suggested/deferred/unknown status, source and date. Facts
remain in lifecycle/facts.json; approvals remain in their own mechanism. A saved
desktop choice is never evidence of an installed desktop.

Initialization creates USER.md only if absent and preserves owner edits on
restart. It also preserves existing AGENTS.md, so updating the package does not
silently replace an adopted agent's instructions. Existing deployments need an
explicit reviewed merge of the new guidance. The default service does not allow
workspace writes by the model: an authorized writing tool must be enabled before
the agent can update the durable profile. Until then it should keep answers in
the conversation and say the profile has not been updated. No additional access
is enabled by this change.

The agent can record the supported non-secret choices with `system-agent
setup-choice KEY VALUE`. The local installer reads and validates those suggestions
as the service account, then asks the owner to review them. Disk selection, approval
and credentials cannot be recorded through this command. The deterministic local
screen asks for missing choices one at a time and builds the target before asking
for irreversible disk approval. It is available without a model subscription.

The live and installed Arch and NixOS profiles enable workspace execution as the dedicated
service account, so these typed choices can be saved. The general-purpose service
module still defaults to read-only tools. Neither profile grants the agent root.
The owner-operated setup screen is privileged and is available only to the local
administrator; its troubleshooting shell has administrator access.

The fixture tests establish real CLI integration, not the quality of a real
model's interview. Real-model acceptance must cover setup, no desktop, changed
preferences, maintenance without a setup interview and recovery without implicit
installation. Real subscription/device authentication is not qualified by a
fixture API key. The official provider authentication command owns protected credential input.

After installation the owner signs in again. Only validated OS choices and the
boot handoff transfer; live credentials and conversation state remain in RAM.
Installed conversations then persist across reboots. The boot verifier runs
independently from the model and checks the mounted root and fresh machine boot.

The local interview now records the owner's main use (development, everyday,
gaming, server or mixed) and offers a review where one answer can be changed
without discarding the rest. Main use is context for the resident agent, not a
claim that a separate gaming/server software bundle has been deployed. Existing
application defaults remain the tested development set. The saved main use is
included in the narrow non-secret preferences and installed USER.md.

## Preconfigured live assistant

OpenClaw and its matching provider runtime are part of the image. Connecting an
account does not install OpenClaw or run its general onboarding wizard. The normal
flow is network readiness, one provider connection, then the installation
conversation. ChatGPT uses the official short device-code flow; API-key entry is
hidden. A future Ratatui interface can call the same focused operations.

Keep packaged defaults separate from private session configuration in RAM. The
normal setup screens change supported preferences, not package files or service
policy. This reduces accidental changes while preserving an administrator shell
for deliberate customization. It is a guided live system, not a locked appliance.
Live changes disappear after shutdown; only reviewed non-secret installation
choices are handed to the resident agent. Assistant naming belongs in identity
preferences, separate from provider authentication and disk approval.
