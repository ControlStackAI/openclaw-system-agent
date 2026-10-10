# Recover a custom installation blocked before first boot

The 2026-10-09 CUSTOM-DEPLOYMENT images require every requested feature to pass
before handoff. That incorrectly blocks tests which need the installed system
running, and optional work the owner explicitly wants to defer.

The tested fix is commit `ec707b1ae3e0b4d31d1aeb04b2769a0d3162cdeb`.
[Qualification receipt](../evidence/first-boot-handoff-recovery.json).

The corrected code has a separate local first-boot review. Required preboot work
still blocks, actual failures still block, and the structural boot/storage checks
always run. Approved post-boot tests and optional deferred work remain **pending**
in the resident lifecycle record and USER.md. The disk approval and existing test
evidence are not rewritten. This is not proof that the system has booted.

## For the person testing

Stay in the current live session. Ask the live agent to use this recovery guide
from the published fix revision. You do not need to reinstall, reset your password
or enroll keys again. The agent should open a separate local review screen, explain
each pending item, and return you to the same conversation afterward.

Choose **After first boot** only for tests which need the installed system running.
Choose **Optional work** only for work you want to defer. Keep unfinished setup
needed to boot or access the machine blocking. Cancelling preserves your records.

A saved handoff still needs safe filesystem cleanup before reboot. After reboot,
verify disk boot, actual sign-in and the requested desktop/key behavior separately.

## For the live agent performing recovery

1. Refresh system facts. Confirm the running environment is the live USB and the
   approved target is `/mnt/controlstack-custom`. Read the current deployment
   record and preserve the installation. Do not repeat disk review, format,
   reenroll keys, rewrite the approved plan or mark tests passed to unblock it.
2. Download this repository at the **exact published fix commit**, inspect its
   code and this guide, and place the public source in a root-owned private
   directory under `/run`. Do not use an unreviewed moving branch or execute a
   download pipeline. The directory must be on RAM-backed storage.
3. Ensure the existing target root and EFI filesystem are mounted at their
   approved locations. If the earlier attempt unmounted them, identify them from
   the existing approved disk and actual filesystem metadata before remounting.
   Do not guess partition numbers or import unrelated pools. Do not mount over a
   populated directory or create a new filesystem.
4. Stop issuing modifying deployment commands while review is open. Use a free
   virtual console, without killing another console or using `openvt -f`.
   For example, after verifying tty8 is unused:

   ```sh
   sudo -n openvt -c 8 -s -w -- python3 /run/REVIEWED-SOURCE/scripts/recover-custom-handoff.py
   ```

   This is an agent-operated command, not something to ask a novice to type.
   The helper checks live/root/TTY context, uses the already packaged Ratatui UI,
   reviews pending work locally, then runs the corrected finalizer. It does not
   patch OpenClaw, replace the running gateway, restart the conversation, install
   packages, format disks, change credentials, unmount filesystems or reboot.
   `--plain` is available only when the packaged UI cannot be used.
5. Read `/run/controlstack-agent/lifecycle/custom-deployment.json` after the helper
   returns. Require `state: prepared-for-boot`; inspect `first_boot_tasks` and
   confirm original plan/disk approval and requirement evidence remain intact.
   If the helper reports an error, preserve the target and diagnose that error.
   In particular, existing resident state must not be deleted to make it succeed.
6. Confirm the target has the matching installation handoff and pending tasks.
   Sync, release target mounts, and safely export only its ZFS pool if applicable.
   Diagnose busy mounts without forced export. Only then offer reboot. Retain the
   recovery source in live RAM until handoff and cleanup are confirmed.
7. On the installed system, verify a new boot ID, the expected machine identity
   and expected root. Complete post-boot tasks with actual evidence. Leave
   optional deferred tasks pending until the owner chooses to resume them.

The recovery helper does not change the ISO. Its qualification must be recorded
separately from the original image tests. New images require fresh qualification.
