# License and provenance

Original lifecycle code, adapters and identity are MIT licensed. No source history
from private proof-of-concept repositories was imported. The official OpenClaw
and nix-openclaw packages retain their upstream licenses, dependency lockfiles,
notices and runtime helpers; they are fetched by pinned sources, not vendored here.
Nixpkgs provides its standard package licensing metadata and hashes. ZFS is CDDL
licensed; the development ISO uses the standard pinned NixOS packages with their licensing
metadata and package notices. The MIT license here applies to this project's own
source, not to all bundled software. Downstream redistributors must retain each
component's notices and satisfy its corresponding-source requirements.

The public installer is consumed for shared readiness code and profile contracts, pinned in
`flake.lock` and `contracts/installer.lock.json`. This project does not redistribute its old ISO,
private VM receipts or hardware identifiers. Only this repository's own synthetic
VM fixtures and sanitized validation results belong in public evidence.
