# Test a deployment-supplied login implementation instead of the preset greeter.
{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-custom-greeter";
  enableOCR = true;
  nodes.machine = { lib, ... }: {
    imports = [ module ../adapters/nixos/hyprland
      (import ../adapters/nixos/owner-setup.nix { owner = "owner"; }) ];
    services.controlstackAgent = { enable = true; mutableProviderSetup = true; };
    services.greetd.settings.default_session.command = lib.mkForce
      "${pkgs.cage}/bin/cage -s -- ${pkgs.quickshell}/bin/quickshell -p ${./fixtures/custom-greeter.qml}";
    programs.dconf.profiles.user.databases = [{
      settings."org/gnome/desktop/interface".color-scheme = "prefer-dark";
    }];
    users.users.owner = { isNormalUser = true; password = "vm-only"; };
    virtualisation = { memorySize = 3072; cores = 2; qemu.options = [ "-vga virtio" ]; };
  };
  testScript = ''
    import json, subprocess, time
    machine.start()
    machine.succeed("install -d -o owner -g users /home/owner/.config /home/owner/.config/hypr")
    machine.succeed("cat /etc/controlstack-agent/desktop-defaults/hyprland.lua ${./fixtures/custom-shortcut.lua} > /home/owner/.config/hypr/hyprland.lua")
    machine.succeed("chown owner:users /home/owner/.config/hypr/hyprland.lua")
    machine.succeed("install -d -o owner -g users /home/owner/.config/ghostty")
    machine.succeed("cp ${./fixtures/custom-ghostty.conf} /home/owner/.config/ghostty/config; chown owner:users /home/owner/.config/ghostty/config")
    machine.wait_for_unit("greetd.service")
    machine.wait_for_text("CUSTOM DEPLOYMENT")
    machine.screenshot("custom-login")
    machine.send_chars("owner"); machine.send_key("ret")
    machine.wait_for_text("Password")
    machine.send_chars("wrong-password"); machine.send_key("ret")
    machine.wait_for_text("Sign-in failed")
    machine.send_chars("owner"); machine.send_key("ret")
    machine.wait_for_text("Password")
    machine.send_chars("vm-only"); machine.send_key("ret")
    owner = "runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
    machine.wait_until_succeeds(owner + "systemctl --user is-active controlstack-shell", timeout=120)
    machine.wait_until_succeeds(owner + "systemd-run --user --quiet --wait --pipe hyprctl -j layers | grep controlstack-islands", timeout=120)
    machine.wait_until_succeeds("pgrep -u owner -f '/bin/[.]?start-hyprland(-wrapped)?( |$)'", timeout=30)
    machine.succeed("test ! -e /home/owner/.config/hypr/hyprland.conf")
    errors = json.loads(machine.succeed(owner + "systemd-run --user --quiet --wait --pipe hyprctl -j configerrors"))
    assert not any(str(error).strip() for error in errors), errors
    machine.succeed(owner + "${pkgs.glib}/bin/gsettings --schemadir ${pkgs.gsettings-desktop-schemas}/share/gsettings-schemas/${pkgs.gsettings-desktop-schemas.name}/glib-2.0/schemas get org.gnome.desktop.interface color-scheme | grep prefer-dark")
    machine.succeed(owner + "ghostty +show-config | grep 'dark:Catppuccin Frappe'")
    machine.wait_for_text("Connect your AI account", timeout=120)
    machine.succeed("pgrep -u root -f 'system_agent.setup'")
    machine.succeed("runuser -u owner -- sudo -n -l | grep system-agent-setup")
    machine.fail("runuser -u owner -- sudo -n /bin/true")
    machine.screenshot("custom-login-assistant-setup")
    machine.send_key("meta_l-f9")
    machine.wait_until_succeeds("test -f /home/owner/lua-shortcut-worked", timeout=30)
    machine.screenshot("custom-login-hyprland")
    # Check a normal terminal, since Ratatui paints its own background.
    gui = owner + "systemd-run --user --quiet --wait --pipe "
    machine.succeed(owner + "systemd-run --user --collect --quiet ghostty --title=ThemeProbe -e sleep 300")
    machine.wait_until_succeeds(gui + "hyprctl -j clients | grep ThemeProbe", timeout=30)
    clients = json.loads(machine.succeed(gui + "hyprctl -j clients"))
    probe = next(c for c in clients if c["title"] == "ThemeProbe")
    x = probe["at"][0] + int(probe["size"][0] * .7)
    y = probe["at"][1] + int(probe["size"][1] * .7)
    def brightness(name):
        machine.screenshot(name)
        return float(subprocess.check_output([
            "${pkgs.imagemagick}/bin/magick", str(machine.out_dir / (name + ".png")),
            "-format", "%[fx:(p{" + str(x) + "," + str(y) + "}.r+p{" + str(x) + "," + str(y) + "}.g+p{" + str(x) + "," + str(y) + "}.b)/3]", "info:"
        ], text=True))
    time.sleep(3)
    assert brightness("normal-terminal-dark") < .4
    settings = owner + "${pkgs.glib}/bin/gsettings --schemadir ${pkgs.gsettings-desktop-schemas}/share/gsettings-schemas/${pkgs.gsettings-desktop-schemas.name}/glib-2.0/schemas "
    machine.succeed(settings + "set org.gnome.desktop.interface color-scheme prefer-light")
    time.sleep(3)
    assert brightness("normal-terminal-light") > .7
    machine.succeed(settings + "reset org.gnome.desktop.interface color-scheme")
    time.sleep(3)
    assert brightness("normal-terminal-dark-restored") < .4
    machine.succeed("! systemctl is-enabled sddm.service")
  '';
}
