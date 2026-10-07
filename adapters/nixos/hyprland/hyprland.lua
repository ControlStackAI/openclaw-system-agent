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
hl.bind("SUPER + Return", hl.dsp.exec_cmd("kitty"))
hl.bind("SUPER + A", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell assistant"))
hl.bind("SUPER + Space", hl.dsp.exec_cmd("quickshell -c controlstack ipc call shell launcher"))
hl.bind("SUPER + E", hl.dsp.exec_cmd("thunar"))
hl.bind("SUPER + L", hl.dsp.exec_cmd("hyprlock"))
hl.bind("SUPER + Q", hl.dsp.window.close())
hl.bind("SUPER + V", hl.dsp.window.float({ action = "toggle" }))
for i = 1, 5 do
    hl.bind("SUPER + " .. i, hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER + SHIFT + " .. i, hl.dsp.window.move({ workspace = i }))
end
for _, direction in ipairs({ "left", "right", "up", "down" }) do
    hl.bind("SUPER + " .. direction, hl.dsp.focus({ direction = direction }))
end
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"))
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"))
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"))
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set +5%"))
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"))

hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"))
