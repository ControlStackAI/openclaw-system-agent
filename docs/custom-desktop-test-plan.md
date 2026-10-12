# Test the custom desktop fixes

Use the new `CUSTOM-DESKTOP-FIX` image, once delivered with matching checksums
and qualification receipts. NixOS uses OpenClaw **2026.9.5 from the pinned official
nix-openclaw input**; Arch uses **2026.10.1** and checks stable before installation.
These versions apply to both the live session and installed resident agent.

On a spare machine with a disk you can erase:

1. Connect networking and sign into your provider. Select **Build my own system**.
2. Ask for Hyprland, your chosen shortcuts, a custom graphical login, a dark
   system theme and Ghostty following the system appearance. Supply actual artwork
   if requesting branding. The agent should record these as separate requirements.
3. Before disk approval, have the agent explain its plan in ordinary language.
   Lua configuration, the supported Hyprland launcher and the installed assistant
   window should be part of that plan, without another reminder from you.
4. Complete protected account/key setup. Keep real graphical login, shortcuts,
   theme and assistant-window tests pending for **After first boot**; the live
   environment cannot prove them. Use the local first-boot review when needed.
5. Reboot without the ISO and use the requested login. Hyprland should have no
   configuration-error or direct-launch warning. Confirm a requested shortcut
   actually works, and ask the resident agent to inspect the loaded Lua file and
   session launch chain. A process named Hyprland alone does not imply a bad launch.
6. **System Assistant** should open automatically in Ghostty with the Ratatui
   setup menu, unless you explicitly declined autostart. Its application-menu
   entry should reopen it after closing. Complete fresh resident provider sign-in;
   live credentials must not carry over.
7. Check a normal Ghostty terminal as well as the setup window. The terminal's
   background and text should match the chosen dark appearance. If you requested
   automatic system following, switch the system appearance and verify Ghostty
   follows; an explicit terminal-theme override should remain respected.
8. Retest physical YubiKey login/removal/unlock and network/audio behavior on the
   installed system. Ask the resident agent to report remaining pending tasks
   accurately and preserve the installed configuration during any repair.

The custom greeter VM checks one concrete implementation. It does not prove that
an unconstrained agent-generated login or theme works. Follow the broader
[first-boot test plan](first-boot-fix-test-plan.md) and consult the exact image's
[qualification evidence](qualification.md). Repository changes do not migrate an
already installed machine or modify an older USB image.
