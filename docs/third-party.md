# License and provenance

Original lifecycle code, adapters and identity are MIT licensed. No source history
from private proof-of-concept repositories was imported. The official OpenClaw
and nix-openclaw packages retain their upstream licenses, dependency lockfiles,
notices and runtime helpers; they are fetched by pinned sources, not vendored here.
Nixpkgs provides its standard package licensing metadata and hashes. ZFS is CDDL
licensed; any future ISO distribution must include the appropriate notices and
source obligations for all bundled components.

The public installer is used as a data/interface contract reference pinned in
`contracts/installer.lock.json`. This project does not redistribute its old ISO,
private VM receipts or hardware identifiers. Only this repository's own synthetic
VM fixtures and sanitized validation results belong in public evidence.
