# Installer boundary

`installer.lock.json` records a published installer revision and the exact hashes
of the shared runtime/interface and profile contracts we inspected. The checker
consumes those public profiles and validates supported image metadata (schema,
distro and runtime); it never modifies the installer checkout. Run it with
`python3 scripts/check-installer-contract.py`, or pass `--checkout` for offline
verification against a local clone at the pinned revision.

The installer owns `/etc/agent-installer/image.json` and its separate live-image
marker. Static metadata is not proof that the target root has booted.

`handoff-v1.example.json` is a PROPOSED resident handoff. The installer does not yet
emit it. The receiving validator accepts exactly these bounded fields and rejects
extra keys, free text, paths, secrets and unexpected distributions/filesystems.
No imported string is executed or treated as agent instructions. This strict
schema reduces accidental disclosure but is not a secret-detection oracle; the
producer must only supply these actual installation facts, and the owner reviews
the destination. Fresh installed authentication is separate.

The installation boot ID and target machine ID must be generated/observed at
installation time. The installed service refreshes root/distro/boot facts locally
and compares them before claiming an installed boot. No handoff is invented merely
to mark a test or a VM as an installed target.
