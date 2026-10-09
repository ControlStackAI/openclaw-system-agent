# Reusable owner preferences

`identity/install-preferences.json` supplies non-secret defaults for each new
installation. Saved conversation choices override those defaults, and the local
review screen can change them before disk approval. The installed agent receives
the reviewed choices in its lifecycle state and USER.md. No provider credential,
key registration or disk-erasure approval is stored in the public profile.

The current profile selects always-on power and YubiKey sign-in. People without a
key can choose account-password sign-in in the review screen. The YubiKey island
integration currently supports Hyprland. Console-only systems use key sign-in but
have no graphical session to lock. GNOME/Plasma require explicitly selecting the
password policy until their lock-screen adapters are implemented.

## YubiKey

On the live setup screen, connect only the YubiKey being enrolled. FIDO must be
enabled. Touch it to register and again to test the actual pinned PAM module.
Both checks finish before disk approval. Only the public registration and device
identity go into the installed system; the private key stays on the YubiKey.

After reboot, the Hyprland preset’s greetd login and local console sign-in require
the enrolled key; the account
password cannot replace it. Disk encryption remains a separate passphrase. The
owner still sets an account password for administration and optional screen unlock.
The default profile disables display-manager autologin.

Hyprland locks on removal of the enrolled USB device (checked every 250 ms).
Reinserting a key does not unlock anything. Press Enter on the lock screen and
touch the key, or enter the password while password screen-unlock is enabled.
The right island's System controls show the password-unlock toggle. Changing it
requires an active, unlocked local desktop, the enrolled key attached, and a fresh
cryptographic touch assertion. The root helper rechecks the session after touch.
The selected screen-unlock policy persists through reboot; initial sign-in always
requires the key. Missing or corrupt password policy disables password unlock.

The service matches the device serial when the USB interface supplies one. For
keys without a USB serial, removing any attached Yubico device locks the session;
changing policy and authenticating still require the enrolled cryptographic key.
A lost key requires administrator recovery from trusted live media; encrypted
storage still requires its disk passphrase. A second recovery-key enrollment UI
is not yet implemented. This policy does not protect against an administrator
intentionally changing PAM or against a physically modified unencrypted disk.

## Always-on power

Both adapters ignore the lid, suspend/hibernate keys and idle power actions, mask
all sleep modes, disable TLP/power-profile switching, disable NetworkManager Wi-Fi
power saving, and apply performance settings where hardware supports them.
Kernel settings disable console blanking, USB autosuspend, PCIe ASPM, NVMe APST
and HDA audio power saving. CPU governor/EPP, SATA link power and device runtime
power controls are set for performance. Thermal protections remain enabled.

Hyprland does not use automatic DPMS or dimming; idle screen *locking* remains
active. Its keep-awake control is hidden under this policy. GNOME's idle display
power settings are disabled, and Plasma's PowerDevil service is masked. Those two
desktop power paths have not yet been qualified in graphical VMs. The policy
cannot override firmware emergency shutdown or a panel's hardware lid switch.

## OpenClaw release selection

The default Arch target policy checks the official npm stable tag during plan
preparation, before disk approval. It rejects prereleases and records the selected
version in the installed-image receipt. NixOS uses its reviewed flake/image pin
without consulting a moving tag. Explicit image-pinned selection is available in
the review screen, including for offline Arch installs.

The ISO itself always uses a locked, preinstalled runtime. Currently Arch can
install that bundled runtime only. If a newer stable version is available, setup
stops before erasing anything and asks for an updated image or an explicit pinned
selection. Automatic staging/qualification of an arbitrary newer runtime from an
older USB is not implemented; the agent must explain this rather than claim that
it installed the latest release. A custom NixOS version requires an explicit,
reviewed pin change and rebuild, not `openclaw update` against the Nix store.

References: [Yubico PAM](https://developers.yubico.com/pam-u2f/),
[registration tool](https://developers.yubico.com/pam-u2f/Manuals/pamu2fcfg.1.html),
[Hyprlock](https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/),
[OpenClaw updates](https://docs.openclaw.ai/install/updating).
