# Test the preset graphical login without test-only autologin.
{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-preset-greeter";
  enableOCR = true;
  nodes.machine = { lib, ... }: {
    imports = [ module ../adapters/nixos/hyprland ];
    services.controlstackAgent.enable = true;
    users.users.owner = { isNormalUser = true; password = "vm-only"; };
    virtualisation = { memorySize = 3072; cores = 2; qemu.options = [ "-vga virtio" ]; };
  };
  testScript = ''
    import os, subprocess, time
    def screen_has(text):
        for attempt in range(60):
            machine.screenshot("current")
            value = subprocess.check_output(["${pkgs.tesseract}/bin/tesseract", os.path.join(os.environ["out"], "current.png"), "stdout", "--psm", "11"], text=True)
            print(repr(value), flush=True)
            if text.lower() in value.lower().replace("usemame", "username"): return
            time.sleep(1)
        raise Exception("Screen did not show " + text)
    machine.start()
    machine.wait_for_unit("greetd.service")
    screen_has("Username")
    machine.screenshot("preset-login")
    machine.send_chars("owner"); machine.send_key("ret")
    screen_has("Password")
    machine.send_chars("wrong-password"); machine.send_key("ret")
    screen_has("Username")
    machine.send_chars("owner"); machine.send_key("ret")
    screen_has("Password")
    machine.send_chars("vm-only"); machine.send_key("ret")
    owner = "runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "
    machine.wait_until_succeeds(owner + "systemctl --user is-active controlstack-shell", timeout=120)
    machine.wait_until_succeeds(owner + "systemd-run --user --quiet --wait --pipe hyprctl -j monitors | grep width", timeout=120)
    machine.sleep(5)
    machine.screenshot("preset-login-hyprland")
    machine.succeed("! systemctl is-enabled sddm.service")
  '';
}
