{ lib, pkgs, ... }:
{
  # Only the live image imports this profile. The resident service retains its
  # separately configured capabilities; this sudo grant is never handed off.
  environment.etc."controlstack-agent/live-system-access.json".text = builtins.toJSON {
    schema = 1; access = "sudo-full";
  };
  security.sudo.enable = true;
  security.sudo.extraRules = [{
    users = [ "controlstack-agent" ];
    commands = [{ command = "ALL"; options = [ "NOPASSWD" ]; }];
  }];
  systemd.services.controlstack-agent = {
    environment.PATH = lib.mkForce "/run/wrappers/bin:/run/current-system/sw/bin:/run/current-system/sw/sbin";
    serviceConfig = {
      NoNewPrivileges = lib.mkForce false;
      CapabilityBoundingSet = lib.mkForce "~";
      ProtectSystem = lib.mkForce false;
      ProtectHome = lib.mkForce false;
      PrivateTmp = lib.mkForce false;
      PrivateDevices = lib.mkForce false;
      ProtectKernelTunables = lib.mkForce false;
      ProtectKernelModules = lib.mkForce false;
      ProtectControlGroups = lib.mkForce false;
      RestrictAddressFamilies = lib.mkForce [];
      ReadWritePaths = lib.mkForce [];
      LockPersonality = lib.mkForce false;
    };
  };
  services.controlstackAgent.settings = {
    agents.defaults.sandbox.mode = "off";
    tools.exec = { host = "gateway"; mode = "full"; };
  };
}
