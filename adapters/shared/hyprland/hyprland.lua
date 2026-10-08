-- Owner-editable defaults for the pinned Hyprland 0.56 Lua configuration.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
hl.config({
    input = { kb_layout = "@keyboard@", follow_mouse = 0, touchpad = { natural_scroll = true } },
    general = { gaps_in = 6, gaps_out = 12, border_size = 2, layout = "dwindle",
        col = { active_border = "rgba(88bdffff)", inactive_border = "rgba(29435fff)" } },
    decoration = { rounding = 12, blur = { enabled = false } },
    animations = { enabled = false },
    misc = { disable_hyprland_logo = true, force_default_wallpaper = 0, disable_splash_rendering = true },
    ecosystem = { no_donation_nag = true, no_update_news = true },
    dwindle = { preserve_split = true },
})
hl.on("hyprland.start", function () hl.exec_cmd("uwsm finalize") end)
-- Portable bindings follow the owner's Nova layout. Optional application keys
-- are reserved until those applications are selected; do not repurpose them.
hl.bind("SUPER + Return", hl.dsp.exec_cmd("ghostty"))
hl.bind("SUPER + Space", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell assistant"))
hl.bind("SUPER + R", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell launcher"))
hl.bind("SUPER + A", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell audio"))
hl.bind("SUPER + CTRL + O", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell monitor"))
hl.bind("SUPER + M", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell logout"))
hl.bind("SUPER + E", hl.dsp.exec_cmd("ghostty -e yazi"))
hl.bind("SUPER + ALT + C", hl.dsp.exec_cmd("claude-desktop"))
hl.bind("SUPER + ALT + X", hl.dsp.exec_cmd("chatgpt codex://"))
hl.bind("SUPER + F12", hl.dsp.exec_cmd("hyprlock"))
hl.bind("SUPER + C", hl.dsp.window.close())
hl.bind("SUPER + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + P", hl.dsp.window.pseudo())
hl.bind("SUPER + backslash", hl.dsp.layout("togglesplit"))
hl.bind("SUPER + N", hl.dsp.exec_cmd("makoctl dismiss"))
hl.bind("SUPER + SHIFT + N", hl.dsp.exec_cmd("makoctl dismiss --all"))
hl.bind("SUPER + CTRL + N", hl.dsp.exec_cmd("makoctl restore"))
for i = 1, 10 do
    local key = i % 10
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end
for key, direction in pairs({ left = "left", right = "right", up = "up", down = "down",
                              H = "left", L = "right", K = "up", J = "down" }) do
    hl.bind("SUPER + " .. key, hl.dsp.focus({ direction = direction }))
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ direction = direction }))
    hl.bind("SUPER + CTRL + " .. key, hl.dsp.window.swap({ direction = direction }))
end
for key, monitor in pairs({ H = "l", L = "r", left = "l", right = "r" }) do
    hl.bind("SUPER + ALT + " .. key, hl.dsp.window.move({ monitor = monitor, follow = true }))
end
hl.bind("SUPER + S", hl.dsp.workspace.toggle_special("magic"))
hl.bind("SUPER + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }))
hl.bind("SUPER + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind("SUPER + mouse_up", hl.dsp.focus({ workspace = "e-1" }))
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true, repeating = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"), { locked = true, repeating = true })
for key, action in pairs({ XF86AudioNext = "next", XF86AudioPause = "play-pause", XF86AudioPlay = "play-pause", XF86AudioPrev = "previous" }) do
    hl.bind(key, hl.dsp.exec_cmd("playerctl " .. action), { locked = true })
end

-- Selected everyday tools, with the same keys as Nova.
hl.bind("SUPER + B", hl.dsp.exec_cmd("firefox"))
hl.bind("SUPER + Z", hl.dsp.exec_cmd('cliphist list | rofi -dmenu -i -p "Clipboard" | cliphist decode | wl-copy'))
hl.bind("SUPER + period", hl.dsp.exec_cmd("rofimoji --selector rofi"))
hl.bind("SUPER + equal", hl.dsp.exec_cmd("rofi -show calc -no-sort"))
hl.bind("SUPER + Tab", hl.dsp.exec_cmd("rofi -show window -show-icons"))
hl.bind("SUPER + slash", hl.dsp.exec_cmd("rofi -show ssh"))
hl.bind("code:107", hl.dsp.exec_cmd("hyprshot -m region --freeze -o ~/Pictures/Screenshots"))
hl.bind("SHIFT + code:107", hl.dsp.exec_cmd("hyprshot -m window --freeze -o ~/Pictures/Screenshots"))
hl.bind("SUPER + code:107", hl.dsp.exec_cmd("hyprshot -m output -o ~/Pictures/Screenshots"))
hl.bind("SUPER + SHIFT + code:107", hl.dsp.exec_cmd('grim -g "$(slurp)" -t ppm - | satty --filename -'))

-- Stop all desktop MCP sessions immediately; resume from the monitor panel.
hl.bind("SUPER + SHIFT + BackSpace", hl.dsp.exec_cmd("controlstack-desktop-control stop"))
hl.bind("SUPER + X", hl.dsp.exec_cmd("controlstack-desktop-menu power"))
hl.bind("SUPER + F11", hl.dsp.exec_cmd("controlstack-desktop-menu shortcuts"))
hl.bind("SUPER + SHIFT + F11", hl.dsp.exec_cmd("controlstack-desktop-menu search"))
