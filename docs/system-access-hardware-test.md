OpenClaw USB test — system access and reusable owner preferences
2026-10-08

Choose one of the two SYSTEM-ACCESS images in Ventoy:
- Arch-Hyprland: OpenClaw 2026.9.9; Hyprland or no desktop.
- NixOS: OpenClaw 2026.9.5; Hyprland, Plasma, GNOME or no desktop.

These are development images. Use the spare laptop and an internal disk whose
contents you have already backed up and are happy to replace. Installation uses
one whole internal disk in UEFI mode, with ZFS. It does not preserve partitions.
Physical YubiKey authentication still needs your test; VM tests use synthetic
credentials and cannot prove a real key works.

1. Boot and connect
The OpenClaw setup should open automatically. Change Text size if needed.
Connect to Wi-Fi or Ethernet. Connect your ChatGPT account using the short URL
and QR code displayed on the screen. Use that exact URL, keep setup open, and
enter the short code on your phone or another computer. Sign-in should return to
the assistant without asking you to install OpenClaw or copy a long URL.

2. Check live system access before installation
Ask: "Inspect this laptop and tell me whether your root command access works."
It should report live Arch/NixOS and verified administrator commands. It should
not say that all host devices are hidden or that it can only use its workspace.
If you have another USB, plug it in and ask: "Identify this USB and mount its
existing filesystem read-only so you can inspect it. Do not format it."
For a writable diagnostics export, explicitly ask it to mount the chosen USB
writable and export a summary without passwords, tokens or provider credentials.
The booted Ventoy USB must not be mistaken for the installation disk.

3. Install from the conversation
Tell it your intended system and ask it to proceed. Choose Hyprland for the
YubiKey island controls. The local review should open automatically, carrying
saved choices, without telling you to find an inaccessible payload or navigate
back through menus. Review defaults: always-on performance and YubiKey sign-in.
The current built-in installer supports its listed choices. Custom requests must
be identified before approval, never claimed as silently implemented.

If using your YubiKey, connect only that key, with FIDO enabled. Registration and
a second touch verification must finish before disk approval. A failed key test
must not erase anything. Password-only sign-in remains an explicit alternative.
Check the disk's model, size and serial. Only type the exact ERASE phrase when it
identifies the spare internal disk. Enter account/encryption passwords only in
the protected local prompts, not in the chat.

4. Check conversation resumption
After installation, choose Stay in this USB session once. The same assistant
conversation should return and report files installed, awaiting a separate boot.
It must not claim an installed boot has already succeeded. Then shut down, remove
Ventoy, and boot from the internal disk.

5. Check installed Hyprland and persistence
The enrolled YubiKey should be required for desktop sign-in. Disk encryption,
if chosen, has its separate passphrase. Provider sign-in is intentionally fresh:
live credentials are not copied. Ask the resident assistant to check its actual
installed root, boot identity, chosen preferences, and OpenClaw version.
Confirm Ghostty, Firefox, Neovim, coding apps and the three small desktop islands.

6. Check key removal and screen-unlock policy
Remove the enrolled key: the desktop should lock promptly. Reinsert and touch it
to unlock (press Enter to begin), or use the account password while allowed.
With the desktop unlocked and key attached, use Password unlock in the right
island's System tab. Disabling or re-enabling password unlock requires a fresh
key touch. With it disabled, a password must not unlock the screen. Reboot sign-in
must still require the key regardless of this screen-unlock toggle.
Keep the key and disk passphrase available. A second-key enrollment UI is not yet
implemented; a lost key requires administrator recovery from trusted live media.

7. Check always-on behavior
Wait idle and close/reopen the lid. The machine should not suspend, hibernate,
automatically dim, or power off its displays. Idle locking can still happen.
Thermal safeguards remain enabled. A firmware-controlled lid switch may still
physically switch off an internal panel; software cannot override all hardware.

If something fails, record the exact step and a clear photo of the visible error.
Prefer a readable plain-text summary or USB export over compressed text in a
photo: a single misread character can make the entire compressed block unusable.
