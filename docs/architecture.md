# Boundaries and lifecycle

The distribution-independent core never runs pacman, nixos-rebuild, disk erasure,
or pool upgrades. The runtime integration launches the complete pinned OpenClaw
package and uses its native state/database/backup behavior. Arch and NixOS own
service and packaging differences. Provider configuration remains an OpenClaw
concern, not a second credential store invented by this project.

Lifecycle: fresh state -> private identity/config initialization -> fresh provider
setup -> gateway health -> actual model response -> operation-ready capabilities.
Installed-boot verification is an independent gate requiring a prior installation
record, a different boot ID, the target machine ID, target distro, actual root
dataset and writable mount. Without that evidence, state stays unconfirmed.
A VM reboot demonstrates service persistence, not ZFS-root installer qualification.

OpenClaw reads AGENTS.md, SOUL.md and IDENTITY.md under its configured workspace.
ExecStartPre refreshes runtime facts independently of model availability. BOOT.md
is guidance only; this project does not enable the upstream boot-md hook or
outbound messages. Session-start identity asks for refreshed observations.

Capabilities begin with reading files as a restricted system account. Optional
workspace execution enables shell, process, write and edit tools under the same
systemd boundary. It is powerful over the agent's own state; it is not read-only.
NoNewPrivileges, an empty capability set, private devices, protected homes and a
read-only system prevent granting a general root shell through the daemon.

The resident plan-only capability API uses allowlisted service/dataset/pool names and binds
the plan digest to observed boot/root facts. It has **no apply method**. A separate owner-run `system-agent-admin` broker accepts only root-owned policy
and exact target allowlists. It creates root-private five-minute plans, rechecks
the boot and target GUID/unit content, requires the exact approval digest, and
consumes each approval under a lock before execution. It implements ZFS dataset
snapshots, pool scrub starts and exact service restarts. It has no arbitrary shell,
disk erasure, pool upgrade, rollback or package-update operation. The resident
account cannot invoke it with root rights; no sudo/polkit grant is installed.
The administrator reviews the concrete plan and invokes apply outside the agent.
A friendly owner-authenticated approval UI remains future work.

The broker verifies snapshot existence and restarted service activity. Scrub start
is reported as a request, never as successful completion. A failure after approval
consumption requires a new inspection/plan, preventing crash-triggered replay.
Other root processes can still change a resource concurrently; this prototype is
not a transactional storage manager and does not perform destructive operations.

A privileged recovery tool cannot depend on the resident daemon remaining alive.
Offline recovery will run from qualified installer media using read-only import
and verified restore into a fresh destination before any root switch.
