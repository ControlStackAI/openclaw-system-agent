# Persistent state, adoption, backups and recovery

| State | Location / ownership | Recovery rule |
| --- | --- | --- |
| Workspace and identity | `state/workspace`, service account | Preserve owner edits; initialization never replaces files |
| Shared runtime database | OpenClaw-managed state subtree | Native consistent backup, not a raw live SQLite copy |
| Agent databases, sessions, transcripts, auth | OpenClaw-managed `agents/` and any registered external roots | Enumerate canonical roots; native verified archive; preserve database plus companion state |
| Provider/channel credentials | Runtime auth database or private SecretRef targets | Fresh installed setup; protected backup policy; never public diagnostics |
| Gateway token | `state/gateway-token`, 0600 | Private; never put token on process command line |
| Lifecycle observations | `state/lifecycle` | Refresh after reboot; old observations are not authoritative |
| Service configuration | Reviewed distro source | Rebuild separately from mutable state |
| Backups | Separate private destination | Verify, restore-test and copy off the source storage |

`system-agent backup --destination ...` uses the pinned upstream
`openclaw backup create --verify --output ... --json` with explicit state/config.
It includes workspace by default. A backup archive may contain credentials and
must be encrypted for off-device storage by the operator's chosen backup system.
The wrapper uses a private destination and does not claim encryption.
Inventory external SecretRef files and secret-manager recovery separately; do not
assume the native archive captures every external credential source.
Verification success is required; a running copy job is not a completed backup.

Adoption is **not an automatic migration feature**. First enumerate all active,
external, historical and recovery roots; stop writers where required by the
upstream migration procedure, take a full verified recovery archive, restore to
an isolated destination and check canonical SQLite integrity plus transcripts.
Only then plan service cutover. Keep the original instance intact until a real
conversation resumes on the replacement. The initializer preserves existing bytes
but is not sufficient evidence that a whole instance was adopted.

Use separate ZFS datasets for OS, resident state and independent backups where
possible. A state dataset must survive OS-generation rollback. Snapshot policy is
not enabled automatically. Proposed defaults are a snapshot before authorized
maintenance, limited hourly/daily retention agreed with the owner, and a verified
off-device replication target. Review receive-side feature compatibility and
keys before encrypted sends; never run `zpool upgrade` to fix a transfer.

Upgrades require a reviewed runtime lock, complete backup/restore test, explicit
schema compatibility decision, staged OS/kernel/module/initramfs, and a trial boot
with a retained known-good entry. Downgrading OpenClaw against a newer mutable
schema is not a valid rollback plan. Neither unattended upgrades nor boot-environment
switching are implemented. Root rollback and application-state recovery must be
coordinated and independently tested.
