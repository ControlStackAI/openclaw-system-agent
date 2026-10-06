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
pinned target adapter, then ask for one choice. GNOME, KDE Plasma or Xfce are
examples to investigate, not a claim that this prototype installs them. A
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

These are shipped conversation instructions and a persistent profile template,
not a deterministic questionnaire or desktop installation executor. The fixture
VM can verify profile delivery and preservation; it cannot establish whether a
real model reliably asks the right next question. A real-model acceptance check
must cover setup, no-desktop, changed preferences, maintenance without a setup
interview, and recovery from live media without implicit installation.

Implemented: readiness gates before mutable CLI onboarding; isolated runtime
context; official interactive onboarding invocation; declarative Nix service;
identity language and reopen via `system-agent chat`.
Not implemented: a complete continuous novice UI, Wi-Fi menu integration, a
NixOS secret/provider setup UI, and verified subscription login in this image.
Readiness to the project/package endpoints does not prove a provider is reachable;
the native onboarding live inference check must establish that separately.

On Arch, the official interactive wizard owns masked input. No wrapper accepts
API keys as argv. On NixOS, the wrapper refuses mutable onboarding and points to
declarative provider configuration rather than pretending the wizard can rewrite
a store-managed config. A future UI should stage non-secret declarative choices
and write secrets directly to private runtime storage through an approved helper.
