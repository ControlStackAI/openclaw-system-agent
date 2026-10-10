# Build your own system

The live setup menu offers **Deployment mode → Build my own system** alongside
**Use the tested setup**. Both use the same image and provider sign-in. A custom
conversation uses separate instructions and a separate session, so preset desktop
choices do not overwrite requests made for a custom system.

Describe the system you want in ordinary language, including any custom login
screen or branding. The agent can start with a minimal installation or adapt a
preset using native Arch or NixOS tools. It reviews a concrete plan, opens local
disk approval, and returns to the conversation to perform and verify the work.
Passwords and key enrollment use protected local input. Progress is recorded so a
failed command can be diagnosed without starting the installation over.

The boot check is a minimum requirement, not a restriction on installed software.
Requested desktop, login, key behavior, network and resident-agent checks are
tracked separately. Prepared files are not a verified boot; the installed system
must start independently after reboot. Before first boot, a separate local review
can schedule pending tests for the installed system and record optional work the
owner chooses to defer. Failed tests, unreviewed pending items and failed minimum
boot checks still block handoff. This preserves the original disk approval and
never marks untested features as passed. Custom configurations do not inherit the
qualification of a tested preset.

The first custom review interface covers one unused internal disk. The supplied
boot verifier covers x86_64 UEFI/systemd-boot and ZFS, ext4, Btrfs or XFS. Native
customization is unrestricted by desktop/package lists, but unsupported boot
verification or storage review needs an explicit extension before claiming it is
covered. Credentials and conversations from the USB are never copied to the target.

See the [packaged native deployment contract](../adapters/custom-deployment.md)
for the exact plan schema, commands, native recipes and evidence boundaries.

For agents building a custom login, the [Quickshell/greetd example](../tests/fixtures/custom-greeter.qml)
and its [isolated authentication test](../tests/custom-greeter-vm.nix) show a working
UI/backend connection. Adapt the appearance and selected session to the owner's
plan; use protected owner enrollment instead of the test's public fixture account.
Authentication, key policy and the requested desktop must each be verified.

For an installation blocked on an older image, see [first-boot handoff recovery](first-boot-handoff-recovery.md).
