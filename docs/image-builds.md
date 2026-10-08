# Distribution-specific images and repeatable builds

The image chooses the distribution. Installation chooses the desktop and owner
preferences. NixOS currently implements no desktop, Plasma, GNOME and Hyprland +
Quickshell. The new Arch image is a **live OpenClaw preview**, with installation
explicitly disabled until its separate disk executor and desktop integration
pass VM qualification. It is not a replacement for the tested NixOS installation
image. Ubuntu and Debian adapters are not implemented.

## Select once, build the lock

To reproduce the checked-in inputs without resolving anything:

```sh
python3 scripts/image.py build --lock images/nixos.lock.json --output dist/nixos
python3 scripts/image.py build --lock images/arch.lock.json --output dist/arch
```

Both locks bind the exact reviewed build sources. Arch is a live preview.

Run from a clean checkout with Python 3.12+ and Nix on x86_64 Linux. New build
source files must be tracked in Git before resolution; untracked files are excluded:

```sh
python3 scripts/image.py resolve --distro nixos --output nixos-image.lock.json
python3 scripts/image.py plan --lock nixos-image.lock.json
python3 scripts/image.py build --lock nixos-image.lock.json --output dist/nixos-1
```

The default retains this checkout's reviewed inputs. Resolution records source
file hashes and the complete transitive flake lock. Build refuses changed source,
missing pins, an existing output directory, or implicit lock updates. Keep the
checkout/revision together with its image lock. Locks are not portable between
arbitrarily changed source trees.

To choose a different NixOS base, explicitly resolve a new lock:

```sh
python3 scripts/image.py resolve --distro nixos --nixpkgs nixos-26.05 --output nixos-26.05.lock.json
python3 scripts/image.py resolve --distro nixos --nixpkgs latest --output nixos-latest.lock.json
```

`--nixpkgs` also accepts an exact commit. Here `latest` means `nixos-unstable`,
resolved once to a commit and NAR hash. The complete runtime/provider dependency
set remains locked. NixOS is built declaratively from nixpkgs; supplying a stock
NixOS ISO is not a supported input. An older nixpkgs revision may lack modules,
packages or compatible runtime dependencies. Evaluation must fail rather than
silently changing the requested base. A newly selected base has no inherited
qualification from the old image.

## Arch source selection

```sh
python3 scripts/image.py resolve --distro arch --output arch-image.lock.json
python3 scripts/image.py build --lock arch-image.lock.json --output dist/arch-1
```

The Arch builder also needs Docker. It uses a digest-pinned Arch builder,
public source staging, public downloaded artifacts and disposable output only.
It never mounts operator homes, host block devices, the host Nix store or the
Docker socket inside the container. SYS_ADMIN is needed for the extracted
Arch root's temporary mounts; a dedicated build VM is recommended for builders.
The OpenClaw runtime is a complete pinned Nix closure on the Arch filesystem.
This is an Arch live system with a Nix-built application runtime, not a NixOS
system. No Nix daemon or host OpenClaw state is imported.

An existing local Arch ISO can be supplied with `build --iso /path/to/image.iso`;
its SHA256 must match the selected lock exactly. A different local image is not
silently accepted or re-labeled as the selected release.

To select a different release, specify **both** the ISO and the package archive:

```sh
python3 scripts/image.py resolve --distro arch \
  --arch-iso-version 2026.10.01 --snapshot 2026/10/05 \
  --output arch-2026-10.lock.json
```

`--arch-iso-version latest` resolves the current official release once. Explicit
older dates use the Arch archive rather than expecting current mirrors to retain
them. The ISO checksum and signer, builder digest, package database hashes,
released OpenZFS policy, kernel package and matching signed ZFS packages are
recorded. The entire root is aligned to the selected package snapshot, including
downgrades: an older ISO with today's packages would not reproduce an older
system. The resolver refuses an unsupported kernel/ZFS combination or missing
signed artifacts. It does not fall back to a different filesystem or an arbitrary
older kernel. A new OpenZFS release/support range requires a reviewed policy update.

## What “deterministic” means here

A pinned ISO alone is insufficient. These builds record source, dependency and
package inputs plus a fixed `SOURCE_DATE_EPOCH`. Successful output includes:

- the ISO;
- `image.lock.json`;
- `SHA256SUMS`;
- `build-receipt.json`, with explicit qualification and reproducibility fields.

Pinned inputs are implemented. **Byte-for-byte reproducibility is not yet
qualified.** Package hooks, filesystem metadata and image tooling can still
introduce differences. Run the same lock on two independent, clean builders:

```sh
python3 scripts/image.py compare /path/to/build-one /path/to/build-two
```

Comparison rehashes both images and verifies their receipts and locks. It does
not claim that two copies or Nix cache hits prove independent rebuilding. Arch
FAT metadata and package-generated state require particular attention. Output
hashes and two-build evidence must support any future reproducibility claim.

Input archives and binary caches must remain available to repeat a build. Archive
release inputs together with their checksums/signatures for long-term retention.
A checksum is integrity evidence; the Arch build also checks the reviewed ISO
and package signers. Historical selection is supported only while the chosen
sources are available and compatible with the adapter.

## Qualification remains separate

A build receipt starts with VM boot, disk installation and physical hardware all
false. Never promote these because compilation succeeded. NixOS images use
`scripts/qualify-iso.py` and the existing desktop/lifecycle VM checks. Arch needs
its own live boot qualification followed by a separate implemented and tested
disk-install path. The previous NixOS ISO on Ventoy is unaffected by these source
changes.
