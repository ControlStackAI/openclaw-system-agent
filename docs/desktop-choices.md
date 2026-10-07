# Desktop choices from Nova

Inspected the active Hyprland 0.56.2 Lua configuration and loaded keybindings,
Ghostty configuration, and installed application entries on 2026-10-07.
Only portable settings were transcribed. Host files and services were not changed.

## Included now

Ghostty replaces Kitty in the Hyprland profile. Hyprland stays in Lua; Ghostty
uses its native key=value format. Nova's Ctrl+A terminal split/tab shortcuts are
included. The normal terminal, terminal launcher entries, customization editor,
and installed resident assistant use Ghostty. Existing owner configuration is
never overwritten during login.

Portable Nova bindings include Super+Return (terminal), R (apps), Space (assistant),
A (audio), C (close), F12 (lock), V (floating), P (pseudo), backslash (split),
all ten workspaces on 1–9/0, navigation/move/swap with arrows and HJKL,
monitor moves with Alt+Left/Right or H/L, scratchpad on S/Shift+S, mouse moves,
notification controls, hardware media keys and Alt+C/X (Claude/Codex Desktop).
Ctrl+O opens the portable resident monitor. M opens the logout confirmation.

## Selected additions

| Application | Purpose | Nova shortcut |
| --- | --- | --- |
| Yazi | Keyboard file manager inside Ghostty | Super+E |
| Hyprshot + Satty | Region/window screenshots and annotation | Print / Shift+Print / Super+Print / Super+Shift+Print |
| Cliphist | Searchable clipboard history | Super+Z |
| Rofimoji | Emoji picker | Super+. |
| Rofi calculator | Quick calculations | Super+= |
| imv | Lightweight image viewing | Application menu |

## Optional applications not selected

| Application | Purpose | Reserved Nova shortcut |
| --- | --- | --- |
| Obsidian | Notes | Super+O, notes workspace |
| LibreOffice | Documents and spreadsheets | Application menu |
| OBS Studio | Screen recording | Application menu |
| Helvum | Visual audio routing | Application menu |
| Discord | Chat | Super+D |
| Vivaldi / Brave / Chromium | Alternative browsers (Firefox retained on Super+B) | Shift+B / Ctrl+B reserved |

The clipboard manager stores copied content. Quick settings → System → Clear
clipboard history removes it. Optional applications are not installed merely because Nova has them.

Nova also has Warp, Buzz, specialized agent surfaces, MATLAB, hardware wallets,
and a monitor toggle tied to its physical outputs. Their keys remain reserved;
those private integrations and hardware assumptions are not copied into the image.
The window switcher (Super+Tab), power menu (Super+X), SSH picker (Super+/), and
shortcut reference/search (Super+F11 / Shift+F11) have portable helpers. Keys for
unselected applications and Nova-only services remain reserved, without dead
commands or reassignment.

References: [Ghostty configuration](https://ghostty.org/docs/config/reference),
[Yazi](https://yazi-rs.github.io/), [Satty](https://github.com/Satty-org/Satty),
[Cliphist](https://github.com/sentriz/cliphist).
