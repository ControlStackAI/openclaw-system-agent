{ owner, core, powerPolicy ? "standard", loginPolicy ? "password" }:
{ config, lib, pkgs, ... }:
let
  power = builtins.fromJSON (builtins.readFile ../shared/power-policy.json);
  alwaysOn = powerPolicy == "always-on";
  keyLogin = loginPolicy == "yubikey";
  u2f = {
    order = 100; control = "required";
    modulePath = "${pkgs.pam_u2f}/lib/security/pam_u2f.so";
    settings = { authfile = "/var/lib/controlstack-security/u2f-keys";
      origin = "pam://controlstack-system"; appid = "pam://controlstack-system";
      cue = true; userpresence = 1; };
  };
  gate = { order = 100; control = "[success=ignore default=1]";
    modulePath = "${pkgs.pam}/lib/security/pam_exec.so";
    args = [ "quiet" "${core}/bin/system-agent-key" "password-check" ]; };
  unix = { order = 200; control = "sufficient";
    modulePath = "${pkgs.pam}/lib/security/pam_unix.so"; };
in {
  environment.etc."controlstack-agent/owner-policy.json".text = builtins.toJSON {
    inherit owner; power_policy = powerPolicy; login_policy = loginPolicy;
  };
  boot.kernelParams = lib.optionals alwaysOn power.kernelParams;
  services.displayManager.sddm.settings.X11.ServerArguments = lib.mkIf alwaysOn "-nolisten tcp -s 0 -dpms";
  services.logind.settings.Login = lib.mkIf alwaysOn power.logind;
  systemd.sleep.settings.Sleep = lib.mkIf alwaysOn power.sleep;
  systemd.targets = lib.mkIf alwaysOn (lib.genAttrs
    [ "sleep" "suspend" "hibernate" "hybrid-sleep" "suspend-then-hibernate" ] (_: { enable = false; }));
  services.tlp.enable = lib.mkIf alwaysOn (lib.mkForce false);
  services.power-profiles-daemon.enable = lib.mkIf alwaysOn (lib.mkForce false);
  powerManagement.powertop.enable = lib.mkIf alwaysOn (lib.mkForce false);
  powerManagement.cpuFreqGovernor = lib.mkIf alwaysOn (lib.mkForce "performance");
  networking.networkmanager.wifi.powersave = lib.mkIf alwaysOn false;
  systemd.services.controlstack-performance = lib.mkIf alwaysOn {
    description = "Apply the owner's always-on performance policy";
    wantedBy = [ "multi-user.target" ];
    serviceConfig = { Type = "oneshot"; ExecStart = "${pkgs.python3}/bin/python3 ${../shared/always-on.py}"; };
  };
  services.udev.extraRules = lib.mkIf alwaysOn ''
    ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
    ACTION=="add", SUBSYSTEM=="pci", TEST=="power/control", ATTR{power/control}="on"
  '';
  services.displayManager.autoLogin.enable = lib.mkIf keyLogin (lib.mkForce false);
  # GNOME and Plasma own display power management outside logind.
  programs.dconf.profiles.user.databases = lib.mkIf (alwaysOn && config.services.desktopManager.gnome.enable) [{
    settings = {
      "org/gnome/desktop/session".idle-delay = lib.gvariant.mkUint32 0;
      "org/gnome/settings-daemon/plugins/power" = {
        idle-dim = false;
        sleep-inactive-ac-type = "nothing";
        sleep-inactive-battery-type = "nothing";
      };
    };
  }];
  systemd.user.services.plasma-powerdevil.enable = lib.mkIf (alwaysOn && config.services.desktopManager.plasma6.enable) false;
  # Authentication rules are intentionally explicit and version-pinned. Review
  # this module against nixpkgs PAM changes before changing the nixpkgs pin.
  security.pam.services = lib.mkIf keyLogin {
    sddm.rules.auth = lib.mkForce { key = u2f; };
    login.rules.auth = lib.mkForce { key = u2f; };
    hyprlock.rules.auth = lib.mkForce {
      key = u2f // { order = 300; };
      password-policy = gate;
      password = unix;
    };
  };
  security.sudo.extraRules = lib.mkIf keyLogin [{ users = [ owner ]; commands = [
    { command = "${core}/bin/system-agent-key password on"; options = [ "NOPASSWD" ]; }
    { command = "${core}/bin/system-agent-key password off"; options = [ "NOPASSWD" ]; }
  ]; }];
  systemd.services.controlstack-key-watch = lib.mkIf keyLogin {
    description = "Lock the owner's session on security-key removal";
    wantedBy = [ "multi-user.target" ]; after = [ "systemd-logind.service" ];
    path = [ pkgs.systemd ];
    serviceConfig = { ExecStart = "${core}/bin/system-agent-key watch";
      Restart = "on-failure"; RestartSec = 1; NoNewPrivileges = true;
      ProtectSystem = "strict"; ProtectHome = true; PrivateTmp = true; };
  };
}
