{ config, lib, pkgs, ... }:
let
  cfg = config.services.controlstackHypruse;
  package = pkgs.callPackage ./package.nix {};
  socket = "/run/controlstack-hypruse/mcp.sock";
  client = pkgs.writeShellScriptBin "controlstack-hypruse-mcp" ''
    exec ${pkgs.socat}/bin/socat STDIO UNIX-CONNECT:${socket}
  '';
  control = pkgs.writeShellScriptBin "controlstack-desktop-control" ''
    case "''${1:-}" in
      stop) exec ${pkgs.systemd}/bin/systemctl --user stop controlstack-hypruse.service ;;
      start) exec ${pkgs.systemd}/bin/systemctl --user start controlstack-hypruse.service ;;
      *) echo 'Use start or stop' >&2; exit 2 ;;
    esac
  '';
in {
  options.services.controlstackHypruse = {
    owner = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Desktop owner whose graphical session exposes Hypruse to the resident agent. Null disables the bridge.";
    };
    package = lib.mkOption { type = lib.types.package; default = package; };
    clientPackage = lib.mkOption { type = lib.types.package; default = client; readOnly = true; internal = true; };
  };
  config = lib.mkIf (cfg.owner != null) {
    users.groups.controlstack-desktop = {};
    users.users.${cfg.owner}.extraGroups = [ "controlstack-desktop" ];
    users.groups.controlstack-agent = {};
    users.users.controlstack-agent = {
      isSystemUser = true;
      group = "controlstack-agent";
      extraGroups = [ "controlstack-desktop" ];
    };
    systemd.tmpfiles.rules = [ "d /run/controlstack-hypruse 2750 ${cfg.owner} controlstack-desktop -" ];
    environment.systemPackages = [ cfg.package client control ];
    systemd.user.services.controlstack-hypruse = {
      description = "OpenClaw Hyprland desktop control (Hypruse MCP)";
      wantedBy = [ "graphical-session.target" ];
      partOf = [ "graphical-session.target" ];
      after = [ "graphical-session-pre.target" ];
      unitConfig.ConditionUser = cfg.owner;
      enableDefaultPath = false;
      environment = {
        HYPRUSE_READONLY = "0";
        HYPRUSE_CLIPBOARD = "1";
        HYPRUSE_SCREENSHOT_MODE = "image";
        HYPRUSE_AUTH_GUARD = "1";
        HYPRUSE_MARK = "1";
        HYPRUSE_JOURNAL = "1";
      };
      serviceConfig = {
        ExecStart = "${pkgs.python3}/bin/python3 ${../../shared/hypruse/bridge.py} ${socket} ${cfg.package}/bin/hypruse controlstack-agent";
        ExecStopPost = "${pkgs.coreutils}/bin/rm -f ${socket}";
        KillMode = "control-group";
        Restart = "on-failure";
        RestartSec = 2;
        UMask = "0077";
      };
    };
  };
}
