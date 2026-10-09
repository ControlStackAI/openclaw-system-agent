# Test a deployment-supplied login implementation instead of the preset greeter.
{ pkgs, module }:
pkgs.testers.runNixOSTest {
  name = "controlstack-custom-greeter";
  enableOCR = true;
  nodes.machine = { lib, ... }: {
    imports = [ module ../adapters/nixos/hyprland ];
    services.controlstackAgent.enable = true;
    services.greetd.settings.default_session.command = lib.mkForce
      "${pkgs.cage}/bin/cage -s -- ${pkgs.quickshell}/bin/quickshell -p ${./fixtures/custom-greeter.qml}";
    users.users.owner = { isNormalUser = true; password = "vm-only"; };
    virtualisation = { memorySize = 3072; cores = 2; qemu.options = [ "-vga virtio" ]; };
  };
  testScript = ''
    machine.start()
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
    machine.screenshot("custom-login-hyprland")
    machine.succeed("! systemctl is-enabled sddm.service")
  '';
}
