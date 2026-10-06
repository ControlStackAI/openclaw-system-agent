# Should OpenClaw have its own live ISO?

Accepted direction: use one installer image architecture and an optional OpenClaw
runtime profile. OpenClaw is
useful in recovery when its durable runtime and tool ecosystem are needed, but
its Node runtime, gateway, database, provider plugins and credential setup add
more moving parts than a single console client.

A “minimal” profile must retain the official full gateway runtime and required
helpers; it means disabling unused channels/plugins and background automation,
not extracting just one JavaScript entry point. Measure closure size, boot memory,
auth latency and offline behavior before making it the default. The pinned official
Nix `openclaw-gateway` package supplies the runtime; the batteries-included tool
bundle is not needed for the first resident integration.

The existing installer's AgentRuntime interface has authenticated, login, start
and forget methods. Its dispatcher currently selects Codex only. This repository
does not claim that a manifest alone registers OpenClaw or that the prototype is
an OpenClaw ISO. A future shared runtime extension must be reviewed in the installer
repo, with implementation owned or consumed here as an explicit dependency.

In live mode, state/config/workspace/credentials must all be under a private 0700
`/run/controlstack-agent` tmpfs tree, with 0600 files and cleanup on exit. Fresh
installed authentication is mandatory. Handoff carries only validated target facts
and revision identifiers; arbitrary Markdown, transcripts and credential paths do
not cross this boundary. The narrow contract is proposed here; the installer does
not yet emit it. Existing-instance adoption is a different, explicitly approved
full-state migration operation.

The profile must establish the current purpose as well as its environment:
installation, maintenance or recovery. Booting live media alone never selects
installation. The resident identity includes the guided OS-choice behavior in
[onboarding](onboarding.md), including desktop or no desktop. Durable owner
preferences use the private workspace USER.md on the installed system. Live
preferences remain in RAM; transferring them will require a separately reviewed,
typed non-secret preferences contract. Do not copy the live workspace or expand
the current facts-only handoff to arbitrary Markdown. That transfer is not wired
into the installer today.

A future ISO needs direct BIOS and UEFI console tests, automatic first-console
startup, separate troubleshooting consoles, reconnect after login selection,
RAM-state checks, module/initramfs matching, full/incremental snapshot transfers,
and a real installed-root reboot. Earlier Codex ISO results apply only to their
exact image digest and are not qualification for this project. No OpenClaw ISO or
Secure Boot claim is published by this prototype.
