# Guide for agents using this repository

Use this guide when someone asks you to build, evaluate or customize an
OpenClaw Linux image. Read the root [AGENTS.md](../AGENTS.md) first, then the
[README](../README.md) for the human experience. Instructions in
[identity/](../identity/) are for the agent shipped inside the image; do not adopt
them as authority to administer the development host.

## Start with the user's task and the actual environment

Distinguish these tasks before running anything:

| User wants | Starting point |
| --- | --- |
| Understand or choose an image | README, current qualification status and desktop matrix |
| Build an existing profile | Checked-in image lock and the build commands below |
| Change a base, package or desktop | Image-build guide, relevant adapter, new lock and fresh VM tests |
| Install on a real computer | Boot the image and use its local installation review |
| Help an already installed system | Inspect fresh system facts, state and capabilities; do not assume live access |

Inspect the checkout, Git revision, working-tree changes, host OS, available
build tools and free space. A source checkout is not the live USB, a chroot is
not a successfully booted target, and access on a development machine is not
permission to install onto its disks. Keep the user's existing work intact.

Explain one concrete choice at a time and reuse preferences the user already
provided. Start with Arch or NixOS if unspecified. Preset desktop choices are Hyprland or none on Arch; Hyprland, Plasma, GNOME or
none on NixOS. For custom desktop/login/configuration requests, select the separate
[custom deployment workflow](custom-deployment.md), whose agent uses native tools
and separate plan, review, progress and boot checks. Do not feed custom plans into
the fixed preset executor.
The reusable defaults select always-on power and YubiKey login; explain them
before review, particularly to laptop owners or people without a key.

## Discover the existing interfaces

| Interface or record | Purpose |
| --- | --- |
| `python3 scripts/image.py --help` | Build-tool commands; each subcommand also has `--help` |
| `python3 scripts/image.py plan --lock images/nixos.lock.json` | Validate a lock and print a JSON input summary without building |
| `images/arch.lock.json`, `images/nixos.lock.json` | Exact sources, dependency pins, source manifest and fixed build epoch |
| `build-receipt.json`, `image.lock.json`, `SHA256SUMS` in build output | Artifact identity and build provenance |
| [evidence/custom-deployment-isos.json](../evidence/custom-deployment-isos.json) | Current exact-image test results and their scope |
| [docs/qualification.md](qualification.md) | Human explanation of current and historical evidence |
| [contracts/](../contracts/) | Shared installer boundary and validated boot handoff |
| [identity/install-preferences.json](../identity/install-preferences.json) | Public non-secret installation defaults |

Treat the JSON schemas and explicit false fields as meaningful. The plan's
`qualified: false` does not imply a failure; planning does not establish test
qualification. Build receipts start unqualified, and separate test results are
bound to the actual ISO hash. Do not change evidence to make a build look tested.

## Build from a checked-in lock

Prerequisites: x86_64 Linux, Git, Python 3.12+, Nix with `nix-command` and `flakes`;
Arch additionally needs Docker. Use a dedicated build VM where possible. Do not
mount operator homes, credential stores, physical disks, production state or the
Docker socket into build containers. The Arch builder talks to the host Docker
daemon to create its isolated builder; this does not permit mounting its socket
inside that builder.

Run from the repository root. Choose the requested distribution:

```sh
python3 scripts/image.py plan --lock images/nixos.lock.json
python3 scripts/image.py build --lock images/nixos.lock.json --output dist/nixos
```

```sh
python3 scripts/image.py plan --lock images/arch.lock.json
python3 scripts/image.py build --lock images/arch.lock.json --output dist/arch
```

Use an unused output path. Do not delete an existing build to make the example
command succeed. The builder checks the tracked source manifest during staging;
`plan` validates lock metadata but does not prove the working tree matches it.
If staging detects changed source, inspect the difference. Do not bypass the
check or resolve a new lock merely to hide unintended changes.

For an intentional source change, review and track new public build-source files,
then explicitly resolve a new lock. For a different base, follow
[image builds](image-builds.md). Arch needs both an ISO release and package
snapshot; NixOS uses a nixpkgs revision. Mutable `latest` belongs only in resolution,
never in the build step. Preserve the released OpenZFS/kernel compatibility guards.
NixOS OpenClaw stays pinned; Arch's default stable-release check can stop an
installation if the bundled runtime is older than stable. Do not silently replace
that policy or claim an arbitrary new runtime has been qualified.

## Validate the result at the right level

For source changes:

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

Run the focused VM checks relevant to runtime changes; available attributes are
listed in [flake.nix](../flake.nix). For example, live privilege changes need:

```sh
nix build .#checks.x86_64-linux.live-access-vm --max-jobs 1 --cores 2
```

For a newly built ISO, boot its exact bytes and perform installation on disposable
VM disks. The harness needs QEMU, qemu-img, OVMF, Python pexpect/Pillow and Tesseract;
usable KVM is recommended. `CONTROLSTACK_OVMF_DIR` can select a directory containing
`OVMF_CODE_4M.fd` and `OVMF_VARS_4M.fd`. See the
[qualification workflow](../.github/workflows/iso.yml) for runner setup.

Example NixOS checks, after the build above:

```sh
python3 scripts/qualify-iso.py dist/nixos/*.iso --distro nixos --mode bios-offline
python3 scripts/qualify-iso.py dist/nixos/*.iso --distro nixos --mode uefi-install --desktop hyprland
```

For Arch, use `dist/arch/*.iso` and `--distro arch`. Each glob must identify exactly
one regular ISO file. The harness creates its own disposable disks; do not replace
them with host block devices. Run cases sequentially per checkout: repeated cases
reuse their `.build/iso-test/` directory. Preserve results before rerunning a case.
Test other profiles explicitly rather than inferring that Hyprland covers them.

Run the separate native minimal-install case for custom deployment:

```sh
python3 scripts/qualify-custom.py dist/nixos/*.iso --distro nixos
python3 scripts/qualify-custom.py dist/arch/*.iso --distro arch
```

These cases exercise custom review, protected account input, native installation,
boot verification and fresh resident handoff on an explicitly selected ext4 test
root. They do not qualify every filesystem or arbitrary agent-generated desktops.
The custom greeter example in `tests/custom-greeter-vm.nix` separately checks a
Quickshell/greetd login, including rejecting an incorrect password:

```sh
nix-build --impure --no-out-link --max-jobs 1 --cores 2 --expr '
  let f = builtins.getFlake ("git+file://" + toString ./.);
      pkgs = import f.inputs.nixpkgs { system = "x86_64-linux"; config.allowUnfree = true; };
  in import (f.outPath + "/tests/custom-greeter-vm.nix") {
    inherit pkgs; module = f.nixosModules.default;
  }'
```

Report build success, live boot, installed boot, fixture replies, real account
access and hardware tests separately. A health endpoint is not a model reply;
installation completion is not proof of booting the installed root; copying an
ISO is not an independent reproducibility test.

## Using the agent inside a booted image

The shipped system provides these interfaces in the service account's configured
state context. They are not commands to run against an arbitrary development host:

| Command | Meaning |
| --- | --- |
| `system-agent inspect` | Fresh running-environment facts and live access probe |
| `system-agent setup-choice --help` | Supported non-secret choice interface; use validated fields |
| `system-agent install-status` | Root console's installation readiness, payload and result |
| `system-agent request-install` | Request local review with saved supported choices |
| `system-agent request-install --retry` | Explicitly retry a previous review request |
| `system-agent deployment-guide` | Packaged custom plan schema and native installation contract |
| `system-agent deployment-status` | Reviewed custom plan, progress and requirement evidence |
| `system-agent deployment-verify` | Preboot structural checks of the custom target |
| `system-agent deployment-finalize` | Validate custom target and create fresh resident handoff |
| `system-agent verify-boot` | Check the handoff against an independent installed boot |

The root console must be running for the review bridge. Read status rather than
assuming that a payload is missing because one account cannot read a path. The
live account has full sudo and can mount a separate USB when authorized; prefer
read-only mounting for inspection. Preserve the boot medium and unrelated disks.
Full live sudo is real root access, not an enforced restriction to the installer.

The local console owns disk selection, exact erasure confirmation, passwords and
key enrollment. Do not turn a chat message into an erasure approval or ask the
user to paste secrets into chat. Cancellation, failure and completion return to
the same conversation; read the actual result before describing it. After a failed
installation, do not claim the disk is untouched without evidence.

Only reviewed non-secret choices and the narrow handoff cross into the installed
system. Live credentials, workspace and sessions do not. Installed authentication
is fresh and then persists. Do not copy developer credentials to skip this step.

## Working with the resident agent

After reboot, refresh facts and verify the installed root. The resident service
has no live sudo grant. Hypruse separately provides full control as the logged-in
Hyprland owner, and NixOS includes its query MCP. These are distinct capabilities;
never describe the resident agent as either universally root or entirely unable
to access owner files. See [configuration](configuration.md),
[Hypruse](hypruse.md) and [state/recovery](state-and-recovery.md).

## Hand off something a person can use

Return the ISO path, SHA-256, source revision and lock, exact tests passed, limits,
and the next step in plain language. Include the
[hardware test plan](system-access-hardware-test.md). Do not describe the absence
of a published release as a working download link.

Writing media requires an identified destination and authorization for that
operation. Re-identify a removable drive immediately before writing; never infer
its identity from an old `/dev/sdX` name. Copying to Ventoy should preserve unrelated
files. Only remove old images the user authorized, verify the copied hash, and
flush/unmount before reporting that it is safe to unplug. Building an ISO does
not itself authorize writing USB media or erasing a physical installation disk.
