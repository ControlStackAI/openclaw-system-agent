# Desktop-only iteration, with synthetic audio devices and no account credentials.
{ pkgs, aiTools }:
pkgs.testers.runNixOSTest {
  name = "controlstack-desktop";
  nodes.machine = { pkgs, lib, ... }: {
    imports = [ (import ../adapters/nixos/desktop.nix { desktop = "hyprland"; inherit aiTools; }) ];
    networking.networkmanager.enable = true;
    users.users.owner = { isNormalUser = true; extraGroups = [ "wheel" "networkmanager" ]; password = "vm-only"; };
    services.displayManager.autoLogin = { enable = true; user = "owner"; };
    virtualisation = { memorySize = 3072; cores = 2; qemu.options = [ "-vga virtio" ]; };
    environment.systemPackages = [ pkgs.python3 pkgs.pulseaudio ];
    services.pipewire.extraConfig.pipewire."99-test-devices"."context.objects" = map (device: {
      factory = "adapter";
      args = { "factory.name" = "support.null-audio-sink"; "node.name" = device.name; "node.description" = device.description;
        "media.class" = device.class; "audio.position" = "FL,FR"; };
    }) [
      { name = "test-speakers"; description = "Studio speakers"; class = "Audio/Sink"; }
      { name = "test-headphones"; description = "USB headphones"; class = "Audio/Sink"; }
      { name = "test-microphone"; description = "Desk microphone"; class = "Audio/Source"; }
      { name = "test-headset"; description = "Headset microphone"; class = "Audio/Source"; }
    ];
  };
  testScript = ''
    import time, json
    machine.start()
    machine.wait_for_unit("display-manager.service")
    owner = "runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
    gui = owner + "systemd-run --user --quiet --wait --pipe "
    machine.wait_until_succeeds(owner + "systemctl --user is-active controlstack-shell")
    time.sleep(8)
    errors = json.loads(machine.succeed(gui + "hyprctl -j configerrors"))
    assert not any(str(error).strip() for error in errors), errors
    print(machine.succeed("journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager"))
    machine.succeed("! journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager | grep -E 'Failed to load configuration|ReferenceError|TypeError'")
    machine.screenshot("desktop")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell launcher")
    time.sleep(2)
    machine.screenshot("launcher")
    machine.send_chars("mousepad")
    machine.send_key("ret")
    machine.wait_until_succeeds("pgrep -u owner -f '[m]ousepad'")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell controls")
    time.sleep(2)
    machine.screenshot("controls")
    machine.succeed(gui + "wpctl status")
    machine.succeed(gui + "quickshell -c controlstack ipc call shell network")
    time.sleep(2)
    machine.screenshot("network")
    machine.send_key("esc")
    machine.succeed(owner + "codex --version")
    machine.succeed(owner + "claude --version")
    machine.succeed("test -x $(dirname $(readlink -f $(command -v codex)))/codex-code-mode-host")
    machine.succeed("test -x $(dirname $(readlink -f $(command -v codex)))/logs_client")
    machine.succeed(owner + "nvim --headless '+lua assert(vim.o.number)' +qall")
    for app, match in [("chatgpt", "chatgpt"), ("claude-desktop", "claude")]:
        machine.succeed(owner + "systemd-run --user --quiet --unit=app-test " + app)
        machine.wait_until_succeeds(gui + "hyprctl -j clients | grep -i " + match, timeout=120)
        time.sleep(6)
        machine.screenshot(app)
        machine.succeed(owner + "systemctl --user stop app-test")
    machine.succeed("! journalctl -b _SYSTEMD_USER_UNIT=controlstack-shell.service --no-pager | grep -E 'Failed to load configuration|ReferenceError|TypeError'")
  '';
}
