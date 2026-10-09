# Test the custom-deployment images

Use the new `CUSTOM-DEPLOYMENT` Arch or NixOS entry on Ventoy. Keep the USB
attached until installation finishes. Installing the tested preset erases the
selected whole disk; use a disposable machine/disk and preserve needed data first.

## Tested setup

1. Connect to Wi-Fi, then sign into your provider. Confirm a real agent reply.
2. Keep **Use the tested setup** and ask for Hyprland. Give your account, keyboard,
   storage, power and YubiKey preferences in the conversation.
3. Check the displayed disk identity. A mistyped erase confirmation should offer
   another attempt; cancelling should return to the agent without erasing.
4. Let the agent finish. If anything fails, ask it to inspect the exact error and
   resume the unfinished step. Do not ask it to reinstall over completed work.
5. Reboot onto the installed disk. The Hyprland preset should show the simple
   graphical greetd/gtkgreet login, then your existing three-island desktop,
   Ghostty and resident assistant setup.
6. If enrolled, verify YubiKey sign-in, removal locking, key unlock and the
   password-unlock toggle. These physical actions must be retested with the new
   greeter even if they worked on an older image.
7. Confirm networking, sound, microphone selection, shortcuts and always-on/lid
   behavior. Connect the resident assistant to a provider with fresh sign-in.

## Build my own system

1. Before describing the deployment, open **Deployment mode → Build my own
   system**, then **Talk to the assistant**.
2. Describe a concrete change, for example: “Start with a minimal system, install
   Hyprland, and create a simple Quickshell login with my supplied company artwork.”
   Supply artwork through an accessible file/URL; do not expect an invented logo.
3. Confirm the agent records the requested login, desktop, storage, access and
   recovery requirements. It should explain any missing dependency or unsupported
   verification before promising the result. It must not silently substitute the
   preset greeter for your requested one.
4. Review the disk/plan locally. Passwords, key PINs and disk passphrases belong in
   protected local prompts, never in chat. After each prompt the same custom
   conversation should resume.
5. Before reboot, ask for the minimum boot-check results and separate evidence
   for each requested feature. Files prepared on disk do not prove a successful
   boot. If a check fails, remain in the agent and repair the installed target.
6. Reboot without the ISO and check the actual login/desktop and resident agent.
   Ask it to confirm the independent boot and retained owner intentions.

Report which ISO you used, the step, the visible message and whether the disk had
already changed. Screenshots are useful, but do not include passwords, API keys,
provider tokens, disk passphrases or recovery secrets.

Custom configurations are not all prequalified. Current automatic structural
verification covers one reviewed disk with x86_64 UEFI/systemd-boot and supported
filesystems. See [the workflow limits](custom-deployment.md) and
[qualification evidence](qualification.md) for the exact configurations tested.
