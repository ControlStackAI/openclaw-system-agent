# ControlStackAI OpenClaw System Agent

**Infrastructure that onboards itself.**

An open-source **agentic deployment environment** for Linux, powered by
[OpenClaw](https://github.com/openclaw/openclaw). Boot a machine from USB, tell the
agent what it is for, and work through deployment in a conversation—from choosing
your setup to reviewing the disk plan and installing the system.

OpenClaw is already on the image, ready to guide you once you connect your AI
account. It helps you make choices one at a time, then stays on the installed
machine as its resident system assistant. You approve the storage plan and disk
erasure locally. Start with Arch Linux or NixOS, with a desktop or without one.

**Development preview:** both distributions have passed isolated VM installation
and reboot tests with Hyprland. An owner reports successful hardware boot and
YubiKey sign-in, removal locking and key unlock; broader hardware coverage and
real provider accounts remain under test. Use a spare computer and a backed-up
disk. The tested preset **erases one whole internal disk** and does not preserve
partitions. Custom mode uses a separately reviewed native storage plan; its initial
review interface is also limited to one unused internal disk.

![OpenClaw's Ratatui setup interface on the Arch live USB](docs/images/ratatui-live.png)

*The deployment console works without a desktop. Choose a comfortable text size
and connect your ChatGPT account with a short pairing code and phone QR code.*

[Get started](#get-started) · [Build an ISO](#build-an-iso) ·
[Use with your agent](#use-this-with-your-agent) ·
[Desktop and apps](#your-installed-desktop) · [Test status](docs/qualification.md) ·
[Report a problem](https://github.com/ControlStackAI/openclaw-system-agent/issues)

## From first boot to a running system

Use the environment to bring up a development workstation, a lab machine or a
system without a desktop. Describe the job the machine should do; the agent helps
turn that intent into supported operating-system choices.

- **Inspect the machine.** The live agent can examine hardware, networking and
  storage with administrator access.
- **Choose the setup together.** Discuss the desktop, account, region, encryption,
  sign-in and power settings. Review supported choices before committing them.
- **Deploy with local approval.** The agent opens the installation review from
  your conversation. You confirm the exact disk and enter secrets in protected
  local prompts. The conversation resumes after installation.
- **Keep an assistant on the system.** After reboot and fresh provider sign-in,
  the resident agent checks where it is running and keeps its workspace and
  conversations. Its installed privileges are described [below](#what-access-does-the-assistant-have).

Each build starts from a reviewed image lock and produces checksums and a build
receipt. You can give this repository to your own agent to build and test an image,
then use the onboard agent to guide deployment on the target machine.

## Choose your system

The ISO determines the distribution. You choose the desktop **after booting**.
The live USB itself uses a text interface; your chosen desktop runs after installation.

| | Arch Linux image | NixOS image |
| --- | --- | --- |
| Preset desktop choices | Hyprland + Quickshell, or no desktop | Hyprland + Quickshell, KDE Plasma, GNOME, or no desktop |
| System configuration | Native Arch packages and systemd services | Declarative NixOS configuration |
| Storage | ZFS, with optional native encryption | ZFS, with optional native encryption |
| Bundled OpenClaw | 2026.9.9 | 2026.9.5, pinned |
| Installation version policy | Checks the official stable release before installation | Uses the reviewed pin unless explicitly changed and rebuilt |
| Agent integrations | Hypruse with Hyprland | Hypruse with Hyprland; mcp-nixos for NixOS queries |

**Latest stable OpenClaw on Arch, reviewed pins on NixOS.** Arch checks the
official stable release before installation and currently installs the runtime
bundled on the USB. If the stable release has moved ahead, setup stops before
erasing the disk: use a newer image or explicitly choose the image-pinned version. It does not silently install an old
version or download an untested replacement. [Version policy details](docs/owner-preferences.md#openclaw-release-selection).

Hyprland is the most recently tested desktop on both images. Plasma, GNOME,
encryption and other keyboard layouts have earlier test evidence; qualification
is specific to each image. Ubuntu and Debian adapters are not implemented.
Custom mode can configure other desktops natively; each resulting configuration
needs its own validation and does not inherit the preset's test results.

## Get started

### 1. Get an image and prepare a USB

There is currently **no published GitHub release download**. Build one of the
checked-in image locks using [the instructions below](#build-an-iso), or obtain
a development image together with its checksum, lock and qualification receipt
from its builder. Older Actions artifacts are historical builds, not a latest
release; the first NixOS artifact has a known Wi-Fi defect.

For a first test, prepare:

- An x86_64 computer that can boot in **UEFI mode**.
- An unused internal disk of at least **32 GiB** whose contents can be erased.
- A USB drive of **16 GB or larger**, or an existing Ventoy drive with space for the ISO.
- For NixOS desktop installation, **8 GiB of usable RAM**; allow more installed RAM
  if integrated graphics reserves some. The current Arch and NixOS Hyprland images were tested with 8 GiB.
- Ethernet or Wi-Fi and a supported AI provider account. A phone or second
  computer makes ChatGPT device pairing convenient.
- A FIDO-enabled YubiKey if you want the default key-based system sign-in.
  Password-only sign-in is an explicit alternative.

Verify the ISO against its accompanying `SHA256SUMS` (on Linux, run
`sha256sum -c SHA256SUMS` in the build output directory). Copy the ISO onto an
existing Ventoy drive, or write it with your preferred USB image writer.
**Writing an image directly erases the selected USB drive.**

### 2. Connect and talk to OpenClaw

Boot the USB in UEFI mode. Setup opens automatically.

1. Choose your **keyboard layout** and **Text size** if needed. Font changes have
   a timed preview that restores the old size unless you confirm.
2. Choose **Connect to Wi-Fi or Ethernet**. Ethernet normally connects
   automatically. Setup checks the internet connection before clock readiness.
3. Choose **Connect your AI account or change provider**. OpenClaw is already
   installed and configured; this step connects your account.
4. For ChatGPT, scan the QR code or open the **exact short address shown**, then
   enter the pairing code on your phone or other computer. Keep setup open while
   approving. API keys go into protected local fields, never into chat.
5. Choose **Talk to the assistant** and confirm that you receive a reply.

The normal flow stays in Ratatui for provider setup and opens OpenClaw's own
conversation interface for chat. It does not run the general onboarding wizard.
Anthropic appears under **Another provider**, but its methods are not yet
qualified here and do not provide the same short device-code flow.

### 3. Describe the computer you want

Keep **Use the tested setup** for the guided preset, or select **Deployment mode →
Build my own system** for custom native deployment from a minimal base or a preset.
Custom mode tracks your requirements, reviews the storage and access plan locally,
and checks boot essentials separately from desktop and application requirements.
See the [custom workflow and current verifier scope](docs/custom-deployment.md).

For example:

> Set up a development computer with Hyprland, Firefox and Ghostty. Help me
> choose the remaining settings one at a time. Show me the disk plan before
> changing anything.

The assistant is configured to ask about intended use, desktop or no desktop,
computer and account names, language, keyboard, time zone, encryption and sign-in.
You can name your assistant too. Supported choices carry into local installation
review; custom requests must be explained before approval.

**Review the defaults:** the reusable profile currently selects YubiKey sign-in
and always-on power. Always-on disables sleep, hibernation, automatic display
power-off and lid-triggered sleep. It favors performance over laptop battery life.
You can change the policies in review. Plasma and GNOME currently require the
password sign-in policy. [Owner preferences and key recovery](docs/owner-preferences.md).

### 4. Review, install and reboot

Ask the assistant to proceed with installation. It opens the local review screen
automatically with your saved choices. You can also return to setup with
**Ctrl+D** and select **Review choices and install**.

Review the disk's model, size and serial, storage layout, desktop and access plan.
The guided installer requires an exact local erasure confirmation. Account
passwords, key enrollment and the optional disk passphrase stay in protected
local prompts. Installation uses the entire selected internal disk.

When installation finishes, shut down, remove the USB and boot from the internal
disk. Sign in to your account; **System Assistant** opens. Connect your provider
again on the installed computer. USB credentials and conversations are deliberately
not copied; reviewed OS choices and the assistant name are retained.

The resident assistant checks the actual installed root and reboot identity.
Its new workspace, credentials and conversations then persist across restarts.
Reopen **System Assistant** from your application menu whenever you need it.

For the full walkthrough and hardware checks, see [USB setup](docs/usb-setup.md),
[Arch installation](docs/arch-installation.md) and the [test plan](docs/custom-deployment-test-plan.md).

## Your installed desktop

Hyprland includes three compact Quickshell islands: applications and workspaces
on the left, OpenClaw monitoring in the center, and device/system controls on the
right. An icon-based searchable launcher opens applications. Quick settings offer
speaker and microphone selection, volume, network connections and system controls.

The Hyprland preset uses **greetd with gtkgreet**, a lightweight graphical login
screen, on both distributions. Quickshell supplies the desktop islands after
sign-in. For a different greeter, custom company branding or an entirely different
desktop, select **Deployment mode → Build my own system** and describe it to the
agent. [Custom deployment](docs/custom-deployment.md) uses native configuration
and separate instructions; it does not silently substitute the preset login screen.

The development environment includes **Ghostty, Firefox, Neovim, Codex CLI,
Codex Desktop, Claude Code and Claude Desktop**, plus Git, GitHub CLI, language
and build tools, rootless Podman, Yazi, screenshot annotation, clipboard history,
an emoji picker and a calculator. See the [complete desktop guide](docs/development-desktop.md)
for packaging and application-test limits.

| Shortcut | Action |
| --- | --- |
| Super + Enter | Open Ghostty |
| Super + R | Open the application launcher |
| Super + Space | Open System Assistant |
| Super + B | Open Firefox |
| Super + E | Open Yazi |
| Super + F12 | Lock the screen |
| Super + Shift + Backspace | Stop the agent's Hyprland control bridge |

*Super is usually the Windows-logo key.* [More shortcuts and customization](docs/desktop-choices.md).

[Hypruse](docs/hypruse.md) gives the resident agent full control of your logged-in
Hyprland session, including launching applications and accessing files as your
user. Stop or resume that bridge from the center island. NixOS also includes
[mcp-nixos](docs/installed-mcp.md) in the installed system and live environment.

With the YubiKey policy selected, desktop sign-in after reboot requires the key;
removing it locks Hyprland. Screen unlock can use the key or, initially, your
password. The right island can disable password unlock while you are unlocked
and the enrolled key is present, with a fresh key touch. Disk encryption has its
own passphrase. An owner has reported successful sign-in, removal locking and
key unlock; the password-unlock toggle still needs a physical test.
[Hardware feedback](evidence/owner-hardware-feedback-2026-10-08.json).

## What access does the assistant have?

| Where it runs | Access and persistence |
| --- | --- |
| Live USB | Full administrator access through sudo, including disks and USB mounts. Credentials and conversations stay in private RAM and disappear after reboot. |
| Installed service | Dedicated account with persistent private state and no sudo grant. Privileged maintenance uses a separate owner-run mechanism. |
| Installed Hyprland bridge | Full control of the owner's graphical session and processes, even though the resident service itself is restricted. |

Live root access is intentional so the assistant can prepare installations and
help with recovery. Local disk review is a required installer workflow, **not an
OS-enforced barrier against arbitrary root commands**. The gateway is local-only,
token-authenticated, and external messaging channels are off by default.

Installed root maintenance is not yet a complete conversational experience:
the current owner-run broker supports scoped snapshots, scrubs and service
restarts, but its friendly approval interface remains future work. See
[configuration and privileges](docs/configuration.md) and
[state, backups and recovery](docs/state-and-recovery.md).

## Use this with your agent

You can give this repository to a coding or system agent and ask it to prepare
an image for you. For example:

> Use https://github.com/ControlStackAI/openclaw-system-agent to help me prepare
> a Linux deployment image. Read AGENTS.md and docs/agent-guide.md first. Ask whether I
> want Arch or NixOS if I have not already said. Check the build prerequisites,
> use the reviewed image lock, and build and test the ISO on disposable VM disks.
> Tell me which checks passed and how to put it on USB. Do not write a USB or
> erase a physical disk as part of this build request.

Give your agent your desired distribution and desktop, intended use, and whether
you want YubiKey sign-in and always-on power. You do not need to supply passwords,
API keys or your existing agent state. Once you boot the image, its own OpenClaw
assistant guides the actual installation.

The [agent guide](docs/agent-guide.md) provides commands, JSON lock/receipt locations,
test requirements, access boundaries and handoff expectations. It distinguishes
a build machine, a live USB and an installed system so an agent does not assume
it has the same permissions everywhere. Root [AGENTS.md](AGENTS.md) points agents
to that guide; [identity/](identity/) contains the separate instructions shipped
with the resident assistant.

## Build an ISO

Build on **x86_64 Linux** with Git, Python 3.12+ and Nix with `nix-command` and
`flakes` enabled. The host does not need to run the target distribution. Arch
also requires a running Docker daemon accessible to the builder. A dedicated
build VM is recommended. Allow substantial free disk space for dependencies,
staging and the approximately 7 GB output image.

```sh
git clone https://github.com/ControlStackAI/openclaw-system-agent.git
cd openclaw-system-agent

# Choose one:
python3 scripts/image.py build --lock images/nixos.lock.json --output dist/nixos
python3 scripts/image.py build --lock images/arch.lock.json --output dist/arch
```

Each output directory contains the ISO, `SHA256SUMS`, `image.lock.json` and
`build-receipt.json`. Use a fresh output directory for each build. The checked-in
locks bind reviewed source files and dependencies; a build refuses mismatched
source or implicit updates.

To select a different starting point, follow [locked image builds](docs/image-builds.md):
Arch accepts an ISO release plus package-archive snapshot; NixOS accepts a nixpkgs
revision, not an existing stock ISO. `latest` is resolved once into a lock.
Older inputs must still be available and compatible with the adapter. Kernel,
released OpenZFS, module, utilities and initramfs must remain compatible; unsupported
combinations fail rather than silently changing the filesystem.

**Inputs are pinned; independent byte-for-byte reproducibility is not yet proven.**
A newly built or differently pinned image also needs its own VM qualification.
The [Locked distribution image workflow](https://github.com/ControlStackAI/openclaw-system-agent/actions/workflows/images.yml)
provides a manual GitHub Actions build for maintainers or forks with Actions enabled.
Its artifacts alone are not evidence of a successful installation.

## Test, contribute and get help

The latest CUSTOM-DEPLOYMENT images passed BIOS live/offline boot and UEFI Hyprland
installation, real gateway sudo/mount operations on an emulated USB, installation
review from chat, ZFS-root boot with the ISO removed, desktop checks and a second
reboot. Provider replies in these tests used fixtures. See
[qualification status and exact image hashes](docs/qualification.md) for what each
artifact proves. Secure Boot, physical installation, real account/model access,
physical YubiKeys and installed-root recovery are not qualified by those tests.

To run the source checks:

```sh
python3 -m unittest discover -s tests -v
```

Changes to services, access, desktops or installation also need the relevant
[VM checks](flake.nix) and [ISO qualification](scripts/qualify-iso.py), using only
disposable VM disks. Follow [contributor instructions](AGENTS.md), preserve input
pins, and keep credentials, private host configuration and operator state out of
builds and commits.

[Open an issue](https://github.com/ControlStackAI/openclaw-system-agent/issues/new)
with the image name/checksum, hardware model, step that failed and a readable error
or sanitized diagnostic summary. Never include passwords, tokens or provider
credentials. For connection problems, start with [network troubleshooting](docs/networking.md).

Contributions are welcome through issues and pull requests. Portable lifecycle
code lives in `system_agent/`, provider integration in `runtimes/`, and distro
packaging in `adapters/`. Start with the [architecture](docs/architecture.md).
This repository owns resident-agent persistence and lifecycle; it consumes pinned
readiness contracts from the separate [agent-installer](https://github.com/ControlStackAI/agent-installer).

## License and upstream projects

Project source is [MIT licensed](LICENSE). Images also contain third-party
software, including proprietary AI applications, under their respective terms;
the complete image is not an all-free-software distribution. See
[third-party notices](docs/third-party.md).

Thank you to the **[OpenClaw team and contributors](https://github.com/openclaw/openclaw)**
for the agent runtime that makes this project possible. Learn more at
[OpenClaw](https://openclaw.ai/) and its [documentation](https://docs.openclaw.ai/).
This is an independent ControlStackAI project built on OpenClaw.

Thanks also to Arch Linux, NixOS, OpenZFS, Ratatui, Hyprland, Quickshell,
Hypruse and mcp-nixos. Reviewed upstream references and packaging details are
recorded in [upstream evidence](docs/upstream.md).
